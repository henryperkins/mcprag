"""
Usage Analyzer for Behavior Tracking
Analyzes user behavior patterns to improve search and recommendations
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

from .feedback_collector import FeedbackCollector

logger = logging.getLogger(__name__)


class UsageAnalyzer:
    """
    Analyzes usage patterns from feedback data
    """
    
    def __init__(self, feedback_collector: FeedbackCollector):
        """
        Initialize usage analyzer
        
        Args:
            feedback_collector: FeedbackCollector instance
        """
        self.feedback_collector = feedback_collector
        self._pattern_cache = {}
        self._cache_timestamp = None
        self._cache_duration = timedelta(minutes=15)
    
    async def analyze_user_preferences(
        self,
        user_id: str,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze preferences for a specific user
        
        Args:
            user_id: User identifier
            time_window_days: Days of history to analyze
            
        Returns:
            User preference analysis
        """
        # Get success patterns for user
        success_patterns = await self.feedback_collector.get_success_patterns(user_id)
        
        if not success_patterns:
            return {
                'user_id': user_id,
                'preferred_languages': [],
                'preferred_file_patterns': [],
                'common_query_terms': [],
                'typical_intents': [],
                'success_rate': 0
            }
        
        # Filter by time window
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        recent_patterns = [
            p for p in success_patterns 
            if datetime.fromisoformat(p['timestamp']) > cutoff_date
        ]
        
        # Analyze patterns
        languages = Counter(p['context_language'] for p in recent_patterns if p.get('context_language'))
        intents = Counter(p['intent'] for p in recent_patterns if p.get('intent'))
        
        # Extract common query terms
        query_words = []
        for pattern in recent_patterns:
            words = pattern['query'].lower().split()
            query_words.extend(words)
        common_terms = Counter(query_words).most_common(10)
        
        # Analyze file patterns
        file_patterns = self._analyze_file_patterns(recent_patterns)
        
        return {
            'user_id': user_id,
            'preferred_languages': languages.most_common(3),
            'preferred_file_patterns': file_patterns,
            'common_query_terms': [term for term, count in common_terms],
            'typical_intents': intents.most_common(3),
            'success_rate': len(recent_patterns) / len(success_patterns) if success_patterns else 0,
            'analysis_period_days': time_window_days,
            'total_successful_searches': len(recent_patterns)
        }
    
    def _analyze_file_patterns(self, patterns: List[Dict]) -> List[str]:
        """Extract common file path patterns"""
        file_paths = []
        for pattern in patterns:
            file_paths.extend(pattern.get('selected_files', []))
        
        if not file_paths:
            return []
        
        # Extract common directory patterns
        dir_counts = Counter()
        for path in file_paths:
            parts = path.split('/')
            # Count directory patterns at different levels
            for i in range(1, min(4, len(parts))):
                dir_pattern = '/'.join(parts[:i])
                dir_counts[dir_pattern] += 1
        
        # Return most common patterns
        return [pattern for pattern, count in dir_counts.most_common(5)]
    
    async def analyze_query_evolution(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze how queries evolve within a session
        
        Args:
            session_id: Specific session to analyze
            user_id: User to analyze
            
        Returns:
            Query evolution patterns
        """
        # Get all feedback records
        all_records = list(self.feedback_collector.feedback_queue)
        
        # Filter by user if specified
        if user_id:
            all_records = [r for r in all_records if r.get('query', {}).get('user_id') == user_id]
        
        # Group by session (using timestamp proximity)
        sessions = self._group_into_sessions(all_records)
        
        evolution_patterns = []
        for session in sessions:
            if len(session) < 2:
                continue
            
            # Analyze query refinements
            refinements = []
            for i in range(1, len(session)):
                prev_query = session[i-1]['query']['query']
                curr_query = session[i]['query']['query']
                
                refinement = self._analyze_query_refinement(prev_query, curr_query)
                if refinement:
                    refinements.append(refinement)
            
            if refinements:
                evolution_patterns.append({
                    'session_start': session[0]['timestamp'],
                    'session_queries': len(session),
                    'refinements': refinements,
                    'final_success': session[-1].get('outcome') == 'success'
                })
        
        return evolution_patterns
    
    def _group_into_sessions(
        self,
        records: List[Dict],
        max_gap_minutes: int = 30
    ) -> List[List[Dict]]:
        """Group records into sessions based on time proximity"""
        if not records:
            return []
        
        # Sort by timestamp
        sorted_records = sorted(records, key=lambda x: x['timestamp'])
        
        sessions = []
        current_session = [sorted_records[0]]
        
        for i in range(1, len(sorted_records)):
            prev_time = datetime.fromisoformat(sorted_records[i-1]['timestamp'])
            curr_time = datetime.fromisoformat(sorted_records[i]['timestamp'])
            
            if (curr_time - prev_time).total_seconds() / 60 <= max_gap_minutes:
                current_session.append(sorted_records[i])
            else:
                sessions.append(current_session)
                current_session = [sorted_records[i]]
        
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    def _analyze_query_refinement(
        self,
        prev_query: str,
        curr_query: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze how a query was refined"""
        prev_words = set(prev_query.lower().split())
        curr_words = set(curr_query.lower().split())
        
        added_words = curr_words - prev_words
        removed_words = prev_words - curr_words
        
        if not added_words and not removed_words:
            return None
        
        refinement_type = 'unknown'
        if added_words and not removed_words:
            refinement_type = 'expansion'
        elif removed_words and not added_words:
            refinement_type = 'reduction'
        elif added_words and removed_words:
            refinement_type = 'modification'
        
        return {
            'type': refinement_type,
            'added_terms': list(added_words),
            'removed_terms': list(removed_words),
            'prev_query': prev_query,
            'curr_query': curr_query
        }
    
    async def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze common failure patterns"""
        failure_patterns = await self.feedback_collector.get_failure_patterns()
        
        if not failure_patterns:
            return {
                'total_failures': 0,
                'common_failure_queries': [],
                'common_failure_intents': [],
                'improvement_suggestions': []
            }
        
        # Analyze common characteristics of failed queries
        failure_queries = [p['query'] for p in failure_patterns]
        failure_intents = Counter(p['intent'] for p in failure_patterns if p.get('intent'))
        
        # Look for common words in failed queries
        failure_words = []
        for query in failure_queries:
            failure_words.extend(query.lower().split())
        common_failure_words = Counter(failure_words).most_common(10)
        
        # Generate improvement suggestions
        suggestions = self._generate_improvement_suggestions(failure_patterns)
        
        return {
            'total_failures': len(failure_patterns),
            'common_failure_queries': failure_queries[:10],
            'common_failure_intents': failure_intents.most_common(3),
            'common_failure_terms': [word for word, count in common_failure_words],
            'improvement_suggestions': suggestions
        }
    
    def _generate_improvement_suggestions(
        self,
        failure_patterns: List[Dict]
    ) -> List[str]:
        """Generate suggestions for improving search based on failures"""
        suggestions = []
        
        # Check for specific failure patterns
        intent_failures = defaultdict(int)
        for pattern in failure_patterns:
            if pattern.get('intent'):
                intent_failures[pattern['intent']] += 1
        
        # Suggest improvements based on intent failures
        for intent, count in intent_failures.items():
            if count > len(failure_patterns) * 0.3:  # More than 30% failures
                suggestions.append(f"Improve {intent} intent handling - {count} failures")
        
        # Check for language-specific failures
        lang_failures = defaultdict(int)
        for pattern in failure_patterns:
            if pattern.get('context_language'):
                lang_failures[pattern['context_language']] += 1
        
        for lang, count in lang_failures.items():
            if count > len(failure_patterns) * 0.2:  # More than 20% failures
                suggestions.append(f"Improve {lang} language support - {count} failures")
        
        # Check for empty results
        empty_results = sum(1 for p in failure_patterns if not p.get('shown_files'))
        if empty_results > len(failure_patterns) * 0.5:
            suggestions.append("Expand search coverage - many queries returning no results")
        
        return suggestions
    
    async def get_trending_topics(
        self,
        time_window_hours: int = 24
    ) -> List[Tuple[str, int]]:
        """
        Get trending search topics in recent time window
        
        Args:
            time_window_hours: Hours to look back
            
        Returns:
            List of (topic, count) tuples
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_queries = []
        
        for record in self.feedback_collector.feedback_queue:
            try:
                timestamp = datetime.fromisoformat(record['timestamp'])
                if timestamp > cutoff_time:
                    query = record['query']['query'].lower()
                    # Extract meaningful words (simple tokenization)
                    words = [w for w in query.split() if len(w) > 3]
                    recent_queries.extend(words)
            except (KeyError, ValueError):
                continue
        
        # Count occurrences
        topic_counts = Counter(recent_queries)
        
        # Filter out common stop words
        stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'what', 'when', 'where'}
        trending = [(topic, count) for topic, count in topic_counts.items() if topic not in stop_words]
        
        # Sort by count
        trending.sort(key=lambda x: x[1], reverse=True)
        
        return trending[:20]
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall performance metrics"""
        stats = await self.feedback_collector.get_statistics()
        
        # Calculate additional metrics
        all_records = list(self.feedback_collector.feedback_queue)
        
        # Response time analysis
        response_times = []
        for record in all_records:
            if 'time_to_selection_ms' in record and record['time_to_selection_ms']:
                response_times.append(record['time_to_selection_ms'])
        
        avg_response_time = statistics.mean(response_times) if response_times else 0
        median_response_time = statistics.median(response_times) if response_times else 0
        
        # Click-through rate by position
        position_clicks = defaultdict(int)
        position_shows = defaultdict(int)
        
        for record in all_records:
            if 'results' in record and 'selected_results' in record:
                for i, result in enumerate(record['results'][:10]):
                    position_shows[i] += 1
                    if result['id'] in record.get('selected_results', []):
                        position_clicks[i] += 1
        
        ctr_by_position = {}
        for pos in range(10):
            if position_shows[pos] > 0:
                ctr_by_position[pos] = position_clicks[pos] / position_shows[pos]
        
        return {
            **stats,
            'avg_response_time_ms': avg_response_time,
            'median_response_time_ms': median_response_time,
            'ctr_by_position': ctr_by_position,
            'total_records_analyzed': len(all_records)
        }