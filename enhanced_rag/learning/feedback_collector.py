"""
Feedback Collector for Learning Loop
Collects and stores user interaction feedback for improving search relevance
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import asyncio
from collections import deque

from ..core.models import FeedbackRecord, SearchQuery, SearchResult, CodeContext

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collects user feedback and interaction data for learning
    """
    
    def __init__(self, storage_path: Optional[str] = None, max_records: int = 10000):
        """
        Initialize feedback collector
        
        Args:
            storage_path: Path to store feedback data
            max_records: Maximum number of records to keep in memory
        """
        self.storage_path = Path(storage_path) if storage_path else Path("./feedback_data")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_records = max_records
        self.feedback_queue = deque(maxlen=max_records)
        self.session_data = {}
        
        # Load existing feedback data
        self._load_feedback_data()
        
        # Start background persistence task
        self.persist_task = asyncio.create_task(self._periodic_persist())
    
    def _load_feedback_data(self):
        """Load existing feedback data from storage"""
        feedback_file = self.storage_path / "feedback_records.jsonl"
        if feedback_file.exists():
            try:
                with open(feedback_file, 'r') as f:
                    for line in f:
                        try:
                            record_data = json.loads(line)
                            # Only load recent records to avoid memory issues
                            if len(self.feedback_queue) < self.max_records:
                                self.feedback_queue.append(record_data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid feedback record: {line}")
            except Exception as e:
                logger.error(f"Error loading feedback data: {e}")
    
    async def record_search_interaction(
        self,
        query: SearchQuery,
        results: List[SearchResult],
        context: CodeContext
    ) -> str:
        """
        Record a search interaction
        
        Args:
            query: The search query
            results: Results shown to user
            context: Code context at time of search
            
        Returns:
            Interaction ID for tracking
        """
        interaction_id = f"{query.user_id or 'anon'}_{datetime.utcnow().timestamp()}"
        
        # Store interaction data
        self.session_data[interaction_id] = {
            'query': query.model_dump(),
            'results': [r.model_dump() for r in results],
            'context': context.model_dump() if context else None,
            'timestamp': datetime.utcnow().isoformat(),
            'interaction_id': interaction_id
        }
        
        logger.debug(f"Recorded search interaction: {interaction_id}")
        return interaction_id
    
    async def record_result_selection(
        self,
        interaction_id: str,
        selected_result_ids: List[str],
        time_to_selection_ms: Optional[float] = None
    ):
        """
        Record which results were selected by the user
        
        Args:
            interaction_id: ID from record_search_interaction
            selected_result_ids: IDs of results user clicked/selected
            time_to_selection_ms: Time taken to make selection
        """
        if interaction_id not in self.session_data:
            logger.warning(f"Unknown interaction ID: {interaction_id}")
            return
        
        interaction = self.session_data[interaction_id]
        interaction['selected_results'] = selected_result_ids
        interaction['time_to_selection_ms'] = time_to_selection_ms
        interaction['selection_timestamp'] = datetime.utcnow().isoformat()
        
        # Determine outcome based on selection
        if selected_result_ids:
            interaction['outcome'] = 'success'
        else:
            interaction['outcome'] = 'no_selection'
        
        # Add to feedback queue
        self.feedback_queue.append(interaction)
        
        # Clean up session data
        del self.session_data[interaction_id]
        
        logger.info(f"Recorded result selection for {interaction_id}: {len(selected_result_ids)} results selected")
    
    async def record_explicit_feedback(
        self,
        interaction_id: str,
        satisfaction: int,
        comment: Optional[str] = None
    ):
        """
        Record explicit user feedback (e.g., thumbs up/down)
        
        Args:
            interaction_id: ID from record_search_interaction
            satisfaction: User satisfaction rating (1-5)
            comment: Optional feedback comment
        """
        # Find the interaction in recent feedback
        for record in reversed(self.feedback_queue):
            if record.get('interaction_id') == interaction_id:
                record['user_satisfaction'] = satisfaction
                record['user_comment'] = comment
                record['feedback_timestamp'] = datetime.utcnow().isoformat()
                logger.info(f"Recorded explicit feedback for {interaction_id}: {satisfaction}/5")
                break
    
    async def get_success_patterns(
        self,
        user_id: Optional[str] = None,
        min_satisfaction: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Get patterns from successful interactions
        
        Args:
            user_id: Filter by specific user
            min_satisfaction: Minimum satisfaction score
            
        Returns:
            List of successful interaction patterns
        """
        success_patterns = []
        
        for record in self.feedback_queue:
            # Filter by user if specified
            if user_id and record.get('query', {}).get('user_id') != user_id:
                continue
            
            # Check success criteria
            is_successful = (
                record.get('outcome') == 'success' or
                record.get('user_satisfaction', 0) >= min_satisfaction
            )
            
            if is_successful and record.get('selected_results'):
                # Extract pattern information
                pattern = {
                    'query': record['query']['query'],
                    'intent': record['query'].get('intent'),
                    'selected_files': [
                        r['file_path'] 
                        for r in record['results'] 
                        if r['id'] in record['selected_results']
                    ],
                    'context_language': record['context'].get('language') if record.get('context') else None,
                    'satisfaction': record.get('user_satisfaction'),
                    'timestamp': record['timestamp']
                }
                success_patterns.append(pattern)
        
        return success_patterns
    
    async def get_failure_patterns(
        self,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get patterns from failed interactions
        
        Args:
            user_id: Filter by specific user
            
        Returns:
            List of failed interaction patterns
        """
        failure_patterns = []
        
        for record in self.feedback_queue:
            # Filter by user if specified
            if user_id and record.get('query', {}).get('user_id') != user_id:
                continue
            
            # Check failure criteria
            is_failed = (
                record.get('outcome') == 'no_selection' or
                record.get('user_satisfaction', 5) <= 2
            )
            
            if is_failed:
                # Extract pattern information
                pattern = {
                    'query': record['query']['query'],
                    'intent': record['query'].get('intent'),
                    'shown_files': [r['file_path'] for r in record['results'][:5]],
                    'context_language': record['context'].get('language') if record.get('context') else None,
                    'satisfaction': record.get('user_satisfaction'),
                    'timestamp': record['timestamp']
                }
                failure_patterns.append(pattern)
        
        return failure_patterns
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        total_interactions = len(self.feedback_queue)
        
        if total_interactions == 0:
            return {
                'total_interactions': 0,
                'success_rate': 0,
                'average_satisfaction': 0,
                'common_intents': {},
                'common_languages': {}
            }
        
        successful = sum(1 for r in self.feedback_queue if r.get('outcome') == 'success')
        satisfaction_scores = [r['user_satisfaction'] for r in self.feedback_queue if 'user_satisfaction' in r]
        
        # Count intents and languages
        intent_counts = {}
        language_counts = {}
        
        for record in self.feedback_queue:
            intent = record['query'].get('intent', 'unknown')
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            if record.get('context') and record['context'].get('language'):
                lang = record['context']['language']
                language_counts[lang] = language_counts.get(lang, 0) + 1
        
        return {
            'total_interactions': total_interactions,
            'success_rate': successful / total_interactions,
            'average_satisfaction': sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0,
            'common_intents': dict(sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            'common_languages': dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
            'feedback_with_ratings': len(satisfaction_scores)
        }
    
    async def _periodic_persist(self):
        """Periodically persist feedback data to disk"""
        while True:
            try:
                await asyncio.sleep(300)  # Persist every 5 minutes
                await self.persist_feedback()
            except Exception as e:
                logger.error(f"Error in periodic persist: {e}")
    
    async def persist_feedback(self):
        """Persist feedback data to storage"""
        feedback_file = self.storage_path / "feedback_records.jsonl"
        temp_file = feedback_file.with_suffix('.tmp')
        
        try:
            with open(temp_file, 'w') as f:
                for record in self.feedback_queue:
                    f.write(json.dumps(record) + '\n')
            
            # Atomic rename
            temp_file.replace(feedback_file)
            logger.info(f"Persisted {len(self.feedback_queue)} feedback records")
            
        except Exception as e:
            logger.error(f"Error persisting feedback: {e}")
            if temp_file.exists():
                temp_file.unlink()
    
    async def cleanup(self):
        """Clean up resources"""
        # Cancel background task
        if hasattr(self, 'persist_task'):
            self.persist_task.cancel()
        
        # Final persist
        await self.persist_feedback()