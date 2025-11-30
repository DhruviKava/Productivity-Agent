"""
Custom tool for estimating task durations.
Uses historical data to improve estimates.

FEATURE COVERED: Custom Tools
"""

from typing import Dict, Any, Optional, List
from src.observability.logger import setup_logger

logger = setup_logger("time_estimator")


class TimeEstimatorTool:
    """
    Custom tool for intelligent time estimation.
    
    This implements the Custom Tools requirement.
    Uses historical data and heuristics to estimate task durations.
    """
    
    def __init__(self):
        # Default estimates by task type (in minutes)
        self.default_estimates = {
            "meeting": 30,
            "coding": 90,
            "email": 15,
            "research": 60,
            "review": 30,
            "planning": 45,
            "learning": 120,
            "writing": 60,
            "testing": 45,
            "deployment": 30,
            "default": 60
        }
        logger.info("time_estimator_tool_initialized")
    
    def estimate_duration(
        self,
        task: Dict[str, Any],
        historical_data: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Estimate how long a task will take.
        
        Custom Tool Specification:
        - Tool Name: estimate_duration
        - Inputs: task details, historical data
        - Output: estimated duration with confidence
        
        Usage by agent:
            estimate = time_estimator.estimate_duration(task, history)
        """
        logger.info("estimating_duration", task_name=task.get("name"))
        
        category = task.get("category", "").lower()
        complexity = task.get("complexity", "medium")  # low, medium, high
        
        # Start with base estimate
        base_estimate = self.default_estimates.get(
            category,
            self.default_estimates["default"]
        )
        
        # Adjust for complexity
        complexity_multipliers = {
            "low": 0.7,
            "medium": 1.0,
            "high": 1.5
        }
        multiplier = complexity_multipliers.get(complexity, 1.0)
        
        estimated_duration = base_estimate * multiplier
        
        # If we have historical data for similar tasks, use it
        if historical_data:
            similar_tasks = [
                t for t in historical_data
                if t.get("category") == category
            ]
            
            if similar_tasks:
                historical_avg = sum(
                    t.get("actual_duration", 0) for t in similar_tasks
                ) / len(similar_tasks)
                
                # Blend historical average with base estimate
                estimated_duration = (estimated_duration * 0.4 + historical_avg * 0.6)
                confidence = "high"
            else:
                confidence = "medium"
        else:
            confidence = "low"
        
        # Add buffer for uncertainty
        if confidence == "low":
            estimated_duration *= 1.2  # Add 20% buffer
        
        result = {
            "estimated_duration_minutes": round(estimated_duration),
            "confidence": confidence,
            "base_category": category,
            "complexity": complexity,
            "reasoning": self._generate_reasoning(
                category,
                complexity,
                estimated_duration,
                confidence
            )
        }
        
        logger.info(
            "duration_estimated",
            task_name=task.get("name"),
            estimate=result["estimated_duration_minutes"],
            confidence=confidence
        )
        
        return result
    
    def estimate_total_workload(
        self,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Estimate total time needed for a list of tasks.
        
        Custom Tool Specification:
        - Tool Name: estimate_total_workload
        - Input: list of tasks
        - Output: total estimated time and breakdown
        
        Useful for planning daily schedules.
        """
        logger.info("estimating_total_workload", task_count=len(tasks))
        
        total_minutes = 0
        task_estimates = []
        
        for task in tasks:
            estimate = self.estimate_duration(task)
            total_minutes += estimate["estimated_duration_minutes"]
            
            task_estimates.append({
                "task_name": task.get("name"),
                "estimated_minutes": estimate["estimated_duration_minutes"],
                "category": task.get("category")
            })
        
        # Convert to hours and minutes
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        result = {
            "total_minutes": total_minutes,
            "total_hours": hours,
            "remaining_minutes": minutes,
            "formatted_duration": f"{hours}h {minutes}m",
            "task_count": len(tasks),
            "task_estimates": task_estimates,
            "feasibility": self._assess_feasibility(total_minutes)
        }
        
        logger.info(
            "total_workload_estimated",
            total_minutes=total_minutes,
            task_count=len(tasks)
        )
        
        return result
    
    def suggest_break_schedule(
        self,
        total_work_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Suggest when to take breaks based on total work time.
        
        Uses the Pomodoro technique and ergonomic guidelines.
        """
        breaks = []
        work_blocks = total_work_minutes // 90  # 90-minute work blocks
        
        for i in range(work_blocks):
            break_time = (i + 1) * 90
            break_duration = 15 if i % 2 == 0 else 5  # Alternate break lengths
            
            breaks.append({
                "after_minutes": break_time,
                "break_duration_minutes": break_duration,
                "break_type": "long" if break_duration == 15 else "short"
            })
        
        return breaks
    
    def _generate_reasoning(
        self,
        category: str,
        complexity: str,
        estimate: float,
        confidence: str
    ) -> str:
        """Generate human-readable reasoning for the estimate"""
        base = f"Based on '{category}' category with '{complexity}' complexity"
        
        if confidence == "high":
            historical = ", and similar historical tasks"
            return f"{base}{historical}, estimated {round(estimate)} minutes."
        elif confidence == "medium":
            return f"{base}, estimated {round(estimate)} minutes."
        else:
            buffer = " (with 20% buffer for uncertainty)"
            return f"{base}{buffer}, estimated {round(estimate)} minutes."
    
    def _assess_feasibility(self, total_minutes: int) -> str:
        """Assess if workload is feasible for one day"""
        hours = total_minutes / 60
        
        if hours <= 4:
            return "Light workload - easily achievable"
        elif hours <= 6:
            return "Moderate workload - achievable with focus"
        elif hours <= 8:
            return "Full workload - requires good time management"
        else:
            return "Heavy workload - consider prioritizing or splitting across days"


# Global time estimator instance
_time_estimator = TimeEstimatorTool()

def get_time_estimator() -> TimeEstimatorTool:
    """Get the global time estimator tool instance"""
    return _time_estimator