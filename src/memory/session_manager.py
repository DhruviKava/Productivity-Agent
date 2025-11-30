"""
Session management for maintaining conversation state.
Implements InMemorySessionService for state management.

FEATURE COVERED: Sessions & State Management
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import json

from src.utils.config import Config
from src.observability.logger import setup_logger

logger = setup_logger("session_manager")


@dataclass
class SessionContext:
    """Represents the context for a single session"""
    session_id: str
    created_at: datetime
    last_accessed: datetime
    user_id: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_accessed'] = self.last_accessed.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)


class InMemorySessionService:
    """
    In-memory session service for managing agent sessions.
    Maintains state across multiple agent interactions.
    
    This implements the session management requirement from the course.
    """
    
    def __init__(self, timeout_seconds: int = Config.SESSION_TIMEOUT):
        self.sessions: Dict[str, SessionContext] = {}
        self.timeout_seconds = timeout_seconds
        logger.info("session_service_initialized", timeout=timeout_seconds)
    
    def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> SessionContext:
        """
        Create a new session.
        
        Args:
            session_id: Unique identifier for the session
            user_id: Optional user identifier
        
        Returns:
            Created SessionContext
        """
        now = datetime.now()
        session = SessionContext(
            session_id=session_id,
            created_at=now,
            last_accessed=now,
            user_id=user_id
        )
        
        self.sessions[session_id] = session
        logger.info("session_created", session_id=session_id, user_id=user_id)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        """
        Retrieve a session by ID.
        Updates last_accessed timestamp and checks for timeout.
        """
        session = self.sessions.get(session_id)
        
        if not session:
            logger.warning("session_not_found", session_id=session_id)
            return None
        
        # Check if session has timed out
        if self._is_expired(session):
            logger.info("session_expired", session_id=session_id)
            self.delete_session(session_id)
            return None
        
        # Update last accessed
        session.last_accessed = datetime.now()
        logger.debug("session_accessed", session_id=session_id)
        
        return session
    
    def update_context(
        self,
        session_id: str,
        key: str,
        value: Any
    ) -> bool:
        """
        Update session context with a key-value pair.
        
        Usage:
            service.update_context("session_123", "tasks", task_list)
            service.update_context("session_123", "user_preferences", prefs)
        """
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        session.context_data[key] = value
        logger.info(
            "session_context_updated",
            session_id=session_id,
            key=key
        )
        
        return True
    
    def get_context(self, session_id: str, key: str) -> Optional[Any]:
        """Retrieve a specific context value"""
        session = self.get_session(session_id)
        
        if not session:
            return None
        
        return session.context_data.get(key)
    
    def add_to_history(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a message to conversation history.
        
        Args:
            session_id: Session identifier
            role: 'user' or 'agent' or agent name
            content: Message content
            metadata: Optional additional metadata
        """
        session = self.get_session(session_id)
        
        if not session:
            return
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        session.conversation_history.append(message)
        logger.debug(
            "history_updated",
            session_id=session_id,
            role=role
        )
    
    def get_history(self, session_id: str) -> List[Dict]:
        """Get full conversation history for a session"""
        session = self.get_session(session_id)
        return session.conversation_history if session else []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info("session_deleted", session_id=session_id)
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        expired_ids = [
            sid for sid, session in self.sessions.items()
            if self._is_expired(session)
        ]
        
        for sid in expired_ids:
            self.delete_session(sid)
        
        logger.info("expired_sessions_cleaned", count=len(expired_ids))
    
    def _is_expired(self, session: SessionContext) -> bool:
        """Check if session has expired"""
        timeout = timedelta(seconds=self.timeout_seconds)
        return (datetime.now() - session.last_accessed) > timeout
    
    def get_all_sessions(self) -> Dict[str, SessionContext]:
        """Get all active sessions (for debugging/admin)"""
        return self.sessions.copy()
    
    def save_to_file(self, filepath: str):
        """Persist sessions to file"""
        data = {
            sid: session.to_dict()
            for sid, session in self.sessions.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("sessions_saved", filepath=filepath, count=len(data))
    
    def load_from_file(self, filepath: str):
        """Load sessions from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.sessions = {
                sid: SessionContext.from_dict(session_data)
                for sid, session_data in data.items()
            }
            
            logger.info("sessions_loaded", filepath=filepath, count=len(self.sessions))
        except FileNotFoundError:
            logger.warning("session_file_not_found", filepath=filepath)


# Global session service instance
_session_service = InMemorySessionService()

def get_session_service() -> InMemorySessionService:
    """Get the global session service instance"""
    return _session_service