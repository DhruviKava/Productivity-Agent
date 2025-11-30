"""
Long-term memory storage for the agent system.
Persists information across sessions for learning and personalization.

FEATURE COVERED: Long-term Memory (Memory Bank)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from src.utils.config import Config
from src.observability.logger import setup_logger

logger = setup_logger("memory_bank")


class MemoryBank:
    """
    Persistent memory storage for long-term learning.
    Stores user preferences, task history, and learned patterns.
    
    This implements the Memory Bank requirement from the course.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or Config.MEMORY_BANK_PATH
        self.memory: Dict[str, Any] = {
            "user_preferences": {},
            "task_history": [],
            "learned_patterns": {},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        
        # Load existing memory if available
        self.load()
        logger.info("memory_bank_initialized", path=self.storage_path)
    
    def store_preference(self, key: str, value: Any):
        """
        Store a user preference in long-term memory.
        
        Usage:
            memory.store_preference("work_hours_start", "09:00")
            memory.store_preference("preferred_task_duration", 60)
        """
        self.memory["user_preferences"][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }
        
        self._update_metadata()
        self.save()
        
        logger.info("preference_stored", key=key)
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a stored preference"""
        pref = self.memory["user_preferences"].get(key)
        if pref:
            return pref["value"]
        return default
    
    def store_task_completion(
        self,
        task: Dict[str, Any],
        completion_time: datetime,
        actual_duration_minutes: Optional[int] = None
    ):
        """
        Store completed task for learning patterns.
        
        This helps the agent learn:
        - How long tasks actually take
        - Which times of day work best
        - Task completion patterns
        """
        task_record = {
            "task_id": task.get("id"),
            "task_name": task.get("name"),
            "category": task.get("category"),
            "estimated_duration": task.get("estimated_duration"),
            "actual_duration": actual_duration_minutes,
            "completed_at": completion_time.isoformat(),
            "priority": task.get("priority"),
            "success": True
        }
        
        self.memory["task_history"].append(task_record)
        
        # Keep only last 1000 tasks to prevent memory bloat
        if len(self.memory["task_history"]) > 1000:
            self.memory["task_history"] = self.memory["task_history"][-1000:]
        
        self._update_metadata()
        self.save()
        
        logger.info("task_completion_stored", task_id=task.get("id"))
    
    def learn_pattern(self, pattern_name: str, pattern_data: Dict):
        """
        Store a learned pattern.
        
        Examples:
        - "best_work_hours": {"start": "09:00", "end": "11:00"}
        - "average_task_duration": {"coding": 90, "meetings": 30}
        """
        self.memory["learned_patterns"][pattern_name] = {
            "data": pattern_data,
            "learned_at": datetime.now().isoformat(),
            "confidence": pattern_data.get("confidence", 1.0)
        }
        
        self._update_metadata()
        self.save()
        
        logger.info("pattern_learned", pattern=pattern_name)
    
    def get_pattern(self, pattern_name: str) -> Optional[Dict]:
        """Retrieve a learned pattern"""
        pattern = self.memory["learned_patterns"].get(pattern_name)
        if pattern:
            return pattern["data"]
        return None
    
    def analyze_task_history(self) -> Dict[str, Any]:
        """
        Analyze task history to extract insights.
        
        Returns statistics like:
        - Average completion time by category
        - Most productive hours
        - Task success rate
        """
        history = self.memory["task_history"]
        
        if not history:
            return {"message": "No task history available"}
        
        # Calculate statistics
        total_tasks = len(history)
        
        # Average duration by category
        category_durations = {}
        for task in history:
            if task.get("actual_duration"):
                category = task.get("category", "uncategorized")
                if category not in category_durations:
                    category_durations[category] = []
                category_durations[category].append(task["actual_duration"])
        
        avg_by_category = {
            cat: sum(durations) / len(durations)
            for cat, durations in category_durations.items()
        }
        
        # Find most productive hours
        hour_counts = {}
        for task in history:
            if task.get("completed_at"):
                hour = datetime.fromisoformat(task["completed_at"]).hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        most_productive_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
        
        analysis = {
            "total_tasks_completed": total_tasks,
            "average_duration_by_category": avg_by_category,
            "most_productive_hour": most_productive_hour,
            "categories_tracked": list(category_durations.keys())
        }
        
        logger.info("task_history_analyzed", total_tasks=total_tasks)
        
        return analysis
    
    def get_personalized_recommendations(self) -> List[str]:
        """
        Generate personalized recommendations based on memory.
        
        Returns tips for improving productivity.
        """
        recommendations = []
        
        # Analyze patterns
        analysis = self.analyze_task_history()
        
        if analysis.get("most_productive_hour"):
            hour = analysis["most_productive_hour"]
            recommendations.append(
                f"You're most productive around {hour}:00. "
                "Schedule important tasks during this time."
            )
        
        # Check preferences
        if self.get_preference("break_frequency"):
            recommendations.append(
                "Don't forget to take regular breaks as per your preferences."
            )
        
        # Pattern-based recommendations
        if self.get_pattern("task_overestimation"):
            recommendations.append(
                "You tend to overestimate task duration. "
                "Try reducing estimates by 20%."
            )
        
        return recommendations
    
    def save(self):
        """Persist memory to disk"""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.storage_path, 'w') as f:
            json.dump(self.memory, f, indent=2)
        
        logger.debug("memory_saved", path=self.storage_path)
    
    def load(self):
        """Load memory from disk"""
        if Path(self.storage_path).exists():
            with open(self.storage_path, 'r') as f:
                loaded_memory = json.load(f)
                self.memory.update(loaded_memory)
            
            logger.info("memory_loaded", path=self.storage_path)
        else:
            logger.info("no_existing_memory", path=self.storage_path)
    
    def clear(self):
        """Clear all memory (use with caution!)"""
        self.memory = {
            "user_preferences": {},
            "task_history": [],
            "learned_patterns": {},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        self.save()
        logger.warning("memory_cleared")
    
    def _update_metadata(self):
        """Update metadata timestamp"""
        self.memory["metadata"]["last_updated"] = datetime.now().isoformat()


# Global memory bank instance
_memory_bank = MemoryBank()

def get_memory_bank() -> MemoryBank:
    """Get the global memory bank instance"""
    return _memory_bank