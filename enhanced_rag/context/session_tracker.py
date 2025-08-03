"""
Session tracking for maintaining context across interactions
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionTracker:
    """
    Tracks user session context and file interactions
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.file_access_history: Dict[str, List[Tuple[str, datetime]]] = defaultdict(list)
        self.interaction_count: Dict[str, int] = defaultdict(int)

        # Configuration
        self.max_history_size = self.config.get('max_history_size', 100)
        self.session_timeout_minutes = self.config.get('session_timeout_minutes', 30)

        # Persistence path (optional)
        self.storage_path = self.config.get('storage_path')
        if self.storage_path:
            self.storage_path = Path(self.storage_path)
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_sessions()

    async def track_file_change(
        self,
        session_id: str,
        file_path: str,
        change_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a file change event

        Args:
            session_id: Session identifier
            file_path: Path to the changed file
            change_type: Type of change (open, edit, save, close)
            metadata: Additional metadata about the change
        """
        try:
            # Initialize session if needed
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    'id': session_id,
                    'started_at': datetime.now(timezone.utc),
                    'last_activity': datetime.now(timezone.utc),
                    'file_history': [],
                    'current_files': set(),
                    'interaction_count': 0
                }

            session = self.sessions[session_id]
            session['last_activity'] = datetime.now(timezone.utc)

            # Track file access
            self.file_access_history[file_path].append((session_id, datetime.now(timezone.utc)))

            # Update current files
            if change_type == 'open':
                session['current_files'].add(file_path)
            elif change_type == 'close':
                session['current_files'].discard(file_path)

            # Add to history
            session['file_history'].append({
                'file_path': file_path,
                'change_type': change_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {}
            })

            # Trim history if too large
            if len(session['file_history']) > self.max_history_size:
                session['file_history'] = session['file_history'][-self.max_history_size:]

            # Increment interaction count
            session['interaction_count'] += 1
            self.interaction_count[session_id] += 1

            # Persist if configured
            if self.storage_path:
                await self._save_session(session_id)

        except Exception as e:
            logger.error(f"Error tracking file change: {e}")

    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current context for a session

        Args:
            session_id: Session identifier

        Returns:
            Session context including current files and history
        """
        if session_id not in self.sessions:
            return {
                'exists': False,
                'session_id': session_id
            }

        session = self.sessions[session_id]

        # Clean up expired sessions
        await self._cleanup_expired_sessions()

        return {
            'exists': True,
            'session_id': session_id,
            'started_at': session['started_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
            'duration_minutes': (datetime.now(timezone.utc) - session['started_at']).total_seconds() / 60,
            'current_files': list(session['current_files']),
            'recent_files': self._get_recent_files(session),
            'interaction_count': session['interaction_count'],
            'file_patterns': self._analyze_file_patterns(session)
        }

    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get overall session statistics

        Returns:
            Statistics about all sessions
        """
        await self._cleanup_expired_sessions()

        active_sessions = [
            s for s in self.sessions.values()
            if (datetime.now(timezone.utc) - s['last_activity']).total_seconds() < self.session_timeout_minutes * 60
        ]

        return {
            'total_sessions': len(self.sessions),
            'active_sessions': len(active_sessions),
            'total_interactions': sum(self.interaction_count.values()),
            'most_accessed_files': self._get_most_accessed_files(),
            'average_session_duration': self._calculate_average_duration()
        }

    def _get_recent_files(self, session: Dict[str, Any], limit: int = 10) -> List[str]:
        """Get recently accessed files for a session"""
        recent = []
        seen = set()

        # Iterate in reverse to get most recent first
        for entry in reversed(session['file_history']):
            file_path = entry['file_path']
            if file_path not in seen:
                recent.append(file_path)
                seen.add(file_path)
                if len(recent) >= limit:
                    break

        return recent

    def _analyze_file_patterns(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze file access patterns for a session"""
        patterns = {
            'file_types': defaultdict(int),
            'directories': defaultdict(int),
            'change_types': defaultdict(int)
        }

        for entry in session['file_history']:
            file_path = Path(entry['file_path'])

            # Count file types
            if file_path.suffix:
                patterns['file_types'][file_path.suffix] += 1

            # Count directories
            if file_path.parent:
                patterns['directories'][str(file_path.parent)] += 1

            # Count change types
            patterns['change_types'][entry['change_type']] += 1

        # Convert defaultdicts to regular dicts for JSON serialization
        return {
            'file_types': dict(patterns['file_types']),
            'directories': dict(patterns['directories']),
            'change_types': dict(patterns['change_types'])
        }

    def _get_most_accessed_files(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the most frequently accessed files across all sessions"""
        file_counts = defaultdict(int)

        for file_path, accesses in self.file_access_history.items():
            file_counts[file_path] = len(accesses)

        # Sort by count and return top files
        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:limit]

    def _calculate_average_duration(self) -> float:
        """Calculate average session duration in minutes"""
        if not self.sessions:
            return 0.0

        total_duration = 0
        for session in self.sessions.values():
            duration = (session['last_activity'] - session['started_at']).total_seconds() / 60
            total_duration += duration

        return total_duration / len(self.sessions)

    async def _cleanup_expired_sessions(self) -> None:
        """Remove sessions that have been inactive for too long"""
        current_time = datetime.now(timezone.utc)
        expired_sessions = []

        for session_id, session in self.sessions.items():
            inactive_minutes = (current_time - session['last_activity']).total_seconds() / 60
            if inactive_minutes > self.session_timeout_minutes * 2:  # Double timeout for cleanup
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]
            if session_id in self.interaction_count:
                del self.interaction_count[session_id]

    async def _save_session(self, session_id: str) -> None:
        """Save session to disk"""
        if not self.storage_path:
            return

        try:
            session = self.sessions.get(session_id)
            if not session:
                return

            # Convert sets to lists for JSON serialization
            session_data = session.copy()
            session_data['current_files'] = list(session_data['current_files'])

            # Convert datetime objects to ISO format
            session_data['started_at'] = session_data['started_at'].isoformat()
            session_data['last_activity'] = session_data['last_activity'].isoformat()

            # Save to file
            session_file = self.storage_path / f"session_{session_id}.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")

    def _load_sessions(self) -> None:
        """Load sessions from disk"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            for session_file in self.storage_path.glob("session_*.json"):
                with open(session_file, 'r') as f:
                    session_data = json.load(f)

                # Convert ISO format back to datetime
                session_data['started_at'] = datetime.fromisoformat(session_data['started_at'])
                session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])

                # Convert lists back to sets
                session_data['current_files'] = set(session_data['current_files'])

                session_id = session_data['id']
                self.sessions[session_id] = session_data
                self.interaction_count[session_id] = session_data.get('interaction_count', 0)

        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

    async def clear_session(self, session_id: str) -> None:
        """Clear a specific session"""
        if session_id in self.sessions:
            del self.sessions[session_id]

        if session_id in self.interaction_count:
            del self.interaction_count[session_id]

        # Remove from storage if exists
        if self.storage_path:
            session_file = self.storage_path / f"session_{session_id}.json"
            if session_file.exists():
                session_file.unlink()
