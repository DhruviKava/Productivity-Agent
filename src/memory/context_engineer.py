"""
Context engineering for managing and optimizing context windows.
Implements context compaction and smart context management.

FEATURE COVERED: Context Engineering
"""

from typing import List, Dict, Any
from src.observability.logger import setup_logger

logger = setup_logger("context_engineer")


class ContextEngineer:
    """
    Manages context window optimization for LLM agents.
    Implements context compaction and smart summarization.
    
    This implements the Context Engineering requirement from the course.
    """
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        logger.info("context_engineer_initialized", max_tokens=max_tokens)
    
    def compact_context(
        self,
        tasks: List[Dict[str, Any]],
        conversation_history: List[Dict],
        keep_recent: int = 5
    ) -> Dict[str, Any]:
        """
        Compact context to fit within token limits.
        
        Strategy:
        1. Keep recent tasks in full detail
        2. Summarize older tasks
        3. Keep only relevant conversation history
        
        Args:
            tasks: List of tasks
            conversation_history: Full conversation history
            keep_recent: Number of recent items to keep in full
        
        Returns:
            Compacted context dictionary
        """
        logger.info(
            "compacting_context",
            total_tasks=len(tasks),
            total_history=len(conversation_history)
        )
        
        # Separate recent and old tasks
        recent_tasks = tasks[-keep_recent:] if len(tasks) > keep_recent else tasks
        old_tasks = tasks[:-keep_recent] if len(tasks) > keep_recent else []
        
        # Summarize old tasks
        old_tasks_summary = self._summarize_tasks(old_tasks)
        
        # Compact conversation history
        recent_history = conversation_history[-keep_recent:]
        
        compacted = {
            "recent_tasks": recent_tasks,
            "old_tasks_summary": old_tasks_summary,
            "conversation_history": recent_history,
            "compaction_stats": {
                "original_task_count": len(tasks),
                "kept_full_tasks": len(recent_tasks),
                "summarized_tasks": len(old_tasks),
                "original_history_length": len(conversation_history),
                "kept_history_length": len(recent_history)
            }
        }
        
        logger.info("context_compacted", stats=compacted["compaction_stats"])
        
        return compacted
    
    def _summarize_tasks(self, tasks: List[Dict]) -> Dict[str, Any]:
        """
        Create a summary of multiple tasks.
        
        Reduces memory while preserving key information.
        """
        if not tasks:
            return {"count": 0, "summary": "No tasks to summarize"}
        
        # Group by status
        by_status = {}
        for task in tasks:
            status = task.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
        
        # Group by priority
        by_priority = {}
        for task in tasks:
            priority = task.get("priority", "unknown")
            by_priority[priority] = by_priority.get(priority, 0) + 1
        
        summary = {
            "count": len(tasks),
            "by_status": by_status,
            "by_priority": by_priority,
            "categories": list(set(t.get("category", "none") for t in tasks))
        }
        
        return summary
    
    def extract_relevant_context(
        self,
        full_context: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        Extract only context relevant to a specific query.
        
        This reduces noise and improves agent focus.
        """
        # Simple keyword matching for demo
        # In production, use embeddings or semantic search
        
        relevant_tasks = []
        query_lower = query.lower()
        
        for task in full_context.get("tasks", []):
            task_text = f"{task.get('name', '')} {task.get('description', '')}".lower()
            
            # Check if any query words appear in task
            if any(word in task_text for word in query_lower.split()):
                relevant_tasks.append(task)
        
        return {
            "relevant_tasks": relevant_tasks,
            "original_count": len(full_context.get("tasks", [])),
            "filtered_count": len(relevant_tasks)
        }
    
    def prioritize_context_items(
        self,
        items: List[Dict],
        criteria: str = "recency"
    ) -> List[Dict]:
        """
        Prioritize context items based on criteria.
        
        Criteria options:
        - 'recency': Most recent first
        - 'priority': Highest priority first
        - 'relevance': Most relevant first (requires relevance scores)
        """
        if criteria == "recency":
            # Assume items have 'created_at' or similar timestamp
            return sorted(
                items,
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
        
        elif criteria == "priority":
            priority_order = {"high": 3, "medium": 2, "low": 1}
            return sorted(
                items,
                key=lambda x: priority_order.get(x.get("priority", "low"), 0),
                reverse=True
            )
        
        return items
    
    def estimate_token_count(self, text: str) -> int:
        """
        Rough estimate of token count.
        Actual tokenization varies by model.
        
        Rule of thumb: ~4 characters per token for English
        """
        return len(text) // 4
    
    def truncate_to_token_limit(
        self,
        text: str,
        max_tokens: int = None
    ) -> str:
        """
        Truncate text to fit within token limit.
        
        Attempts to break at sentence boundaries.
        """
        max_tokens = max_tokens or self.max_tokens
        max_chars = max_tokens * 4  # Rough conversion
        
        if len(text) <= max_chars:
            return text
        
        # Try to break at sentence boundary
        truncated = text[:max_chars]
        
        # Find last period
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.8:  # If period is in last 20%
            return truncated[:last_period + 1]
        
        return truncated + "..."


# Global context engineer instance
_context_engineer = ContextEngineer()

def get_context_engineer() -> ContextEngineer:
    """Get the global context engineer instance"""
    return _context_engineer