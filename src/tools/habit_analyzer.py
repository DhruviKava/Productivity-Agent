"""
Custom tool for analyzing user habits and patterns.
Provides insights to optimize task scheduling.

FEATURE COVERED: Custom Tools
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, time
from collections import defaultdict

from src.observability.logger import setup_logger

logger = setup_logger("habit_analyzer")


class HabitAnalyzerTool:
    """
    Custom tool for analyzing user productivity patterns.
    
    This implements the Custom Tools requirement from the course.
    Analyzes task completion history to identify optimal work patterns.
    """
    
    def __init__(self):
        logger.info("habit_analyzer_tool_initialized")
    
    def analyze_productivity_hours(
        self,
        task_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze which hours of the day are most productive.
        
        Custom Tool Specification:
        - Tool Name: analyze_productivity_hours
        - Input: task_history (list of completed tasks)
        - Output: productivity analysis by hour
        
        Usage by agent:
            analysis = habit_analyzer.analyze_productivity_hours(history)
        """
        logger.info("analyzing_productivity_hours", tasks=len(task_history))
        
        hour_stats = defaultdict(lambda: {"tasks": 0, "total_duration": 0})
        
        for task in task_history:
            completed_at = task.get("completed_at")
            if not completed_at:
                continue
            
            # Parse completion time
            try:
                dt = datetime.fromisoformat(completed_at)
                hour = dt.hour
                
                hour_stats[hour]["tasks"] += 1
                duration = task.get("actual_duration", 0)
                hour_stats[hour]["total_duration"] += duration
            except Exception:
                continue
        
        # Calculate productivity score for each hour
        productivity_by_hour = {}
        for hour, stats in hour_stats.items():
            if stats["tasks"] > 0:
                avg_duration = stats["total_duration"] / stats["tasks"]
                productivity_score = stats["tasks"] * 10 + avg_duration
                
                productivity_by_hour[hour] = {
                    "tasks_completed": stats["tasks"],
                    "avg_duration_minutes": round(avg_duration, 1),
                    "productivity_score": round(productivity_score, 2)
                }
        
        # Find peak hours
        if productivity_by_hour:
            sorted_hours = sorted(
                productivity_by_hour.items(),
                key=lambda x: x[1]["productivity_score"],
                reverse=True
            )
            
            peak_hours = [hour for hour, _ in sorted_hours[:3]]
        else:
            peak_hours = []
        
        result = {
            "productivity_by_hour": productivity_by_hour,
            "peak_productivity_hours": peak_hours,
            "recommendation": self._generate_hour_recommendation(peak_hours)
        }
        
        logger.info("productivity_hours_analyzed", peak_hours=peak_hours)
        
        return result
    
    def analyze_task_duration_accuracy(
        self,
        task_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze how accurate the user's time estimates are.
        
        Custom Tool Specification:
        - Tool Name: analyze_duration_accuracy
        - Input: task_history
        - Output: estimation accuracy analysis
        
        Returns insights on whether user over/underestimates.
        """
        logger.info("analyzing_duration_accuracy", tasks=len(task_history))
        
        comparisons = []
        
        for task in task_history:
            estimated = task.get("estimated_duration")
            actual = task.get("actual_duration")
            
            if estimated and actual:
                difference = actual - estimated
                ratio = actual / estimated if estimated > 0 else 1.0
                
                comparisons.append({
                    "estimated": estimated,
                    "actual": actual,
                    "difference": difference,
                    "ratio": ratio
                })
        
        if not comparisons:
            return {
                "message": "Insufficient data for analysis",
                "comparisons_count": 0
            }
        
        # Calculate statistics
        avg_ratio = sum(c["ratio"] for c in comparisons) / len(comparisons)
        avg_difference = sum(c["difference"] for c in comparisons) / len(comparisons)
        
        # Determine tendency
        if avg_ratio > 1.2:
            tendency = "underestimates"
            recommendation = "Try increasing your time estimates by 20-30%"
        elif avg_ratio < 0.8:
            tendency = "overestimates"
            recommendation = "You can reduce your time estimates by 15-20%"
        else:
            tendency = "accurate"
            recommendation = "Your time estimates are quite accurate!"
        
        result = {
            "comparisons_count": len(comparisons),
            "average_ratio": round(avg_ratio, 2),
            "average_difference_minutes": round(avg_difference, 1),
            "tendency": tendency,
            "recommendation": recommendation
        }
        
        logger.info("duration_accuracy_analyzed", tendency=tendency)
        
        return result
    
    def identify_task_patterns(
        self,
        task_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Identify recurring patterns in task completion.
        
        Custom Tool Specification:
        - Tool Name: identify_patterns
        - Input: task_history
        - Output: identified patterns
        
        Finds patterns like:
        - Tasks often done on specific days
        - Sequential task relationships
        - Category preferences
        """
        logger.info("identifying_task_patterns", tasks=len(task_history))
        
        # Analyze by category
        category_stats = defaultdict(lambda: {"count": 0, "total_time": 0})
        
        for task in task_history:
            category = task.get("category", "uncategorized")
            category_stats[category]["count"] += 1
            category_stats[category]["total_time"] += task.get("actual_duration", 0)
        
        # Find most common categories
        sorted_categories = sorted(
            category_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        top_categories = [
            {
                "category": cat,
                "count": stats["count"],
                "avg_duration": round(stats["total_time"] / stats["count"], 1) if stats["count"] > 0 else 0
            }
            for cat, stats in sorted_categories[:5]
        ]
        
        patterns = {
            "top_categories": top_categories,
            "total_categories": len(category_stats),
            "pattern_insights": []
        }
        
        # Generate insights
        if top_categories:
            top_cat = top_categories[0]
            patterns["pattern_insights"].append(
                f"You complete most tasks in '{top_cat['category']}' category "
                f"({top_cat['count']} tasks completed)"
            )
        
        logger.info("task_patterns_identified", categories=len(category_stats))
        
        return patterns
    
    def _generate_hour_recommendation(self, peak_hours: List[int]) -> str:
        """Generate recommendation based on peak hours"""
        if not peak_hours:
            return "No clear productivity pattern found yet. Keep tracking!"
        
        hour_ranges = []
        for hour in peak_hours:
            time_str = time(hour, 0).strftime("%I:%M %p")
            hour_ranges.append(time_str)
        
        return (
            f"Your peak productivity hours are: {', '.join(hour_ranges)}. "
            f"Schedule your most important tasks during these times."
        )


# Global habit analyzer instance
_habit_analyzer = HabitAnalyzerTool()

def get_habit_analyzer() -> HabitAnalyzerTool:
    """Get the global habit analyzer tool instance"""
    return _habit_analyzer