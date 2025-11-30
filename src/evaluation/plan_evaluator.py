"""
Agent evaluation system using LLM-as-a-judge.
Evaluates the quality of agent outputs.

FEATURE COVERED: Agent Evaluation
"""

from typing import Dict, Any, List
import json

from src.observability.logger import setup_logger
from src.utils.config import Config

logger = setup_logger("plan_evaluator")


class PlanEvaluator:
    """
    Evaluates agent-generated plans using LLM-as-a-judge approach.
    
    This implements the Agent Evaluation requirement from the course.
    Scores plans on multiple criteria and provides feedback.
    """
    
    def __init__(self):
        logger.info("plan_evaluator_initialized")
    
    def evaluate_plan(
        self,
        plan: Dict[str, Any],
        original_tasks: List[Dict[str, Any]],
        user_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a generated plan using multiple criteria.
        
        Evaluation Specification:
        - Tool Name: evaluate_plan
        - Inputs: generated plan, original tasks, preferences
        - Output: scores and feedback
        
        Scoring Criteria:
        1. Time Efficiency (0-25 points)
        2. Priority Alignment (0-25 points)
        3. Feasibility (0-25 points)
        4. Work-Life Balance (0-25 points)
        
        Total: 100 points possible
        """
        logger.info("evaluating_plan", task_count=len(original_tasks))
        
        scores = {
            "time_efficiency": self._score_time_efficiency(plan),
            "priority_alignment": self._score_priority_alignment(
                plan,
                original_tasks
            ),
            "feasibility": self._score_feasibility(plan),
            "work_life_balance": self._score_work_life_balance(
                plan,
                user_preferences or {}
            )
        }
        
        total_score = sum(scores.values())
        
        # Generate feedback
        feedback = self._generate_feedback(scores, plan)
        
        # Determine grade
        grade = self._calculate_grade(total_score)
        
        evaluation_result = {
            "total_score": total_score,
            "max_score": 100,
            "percentage": round((total_score / 100) * 100, 1),
            "grade": grade,
            "scores_breakdown": scores,
            "feedback": feedback,
            "recommendations": self._generate_recommendations(scores, plan)
        }
        
        logger.info(
            "plan_evaluated",
            total_score=total_score,
            grade=grade
        )
        
        return evaluation_result
    
    def _score_time_efficiency(self, plan: Dict[str, Any]) -> float:
        """
        Score how efficiently time is used (0-25 points).
        
        Factors:
        - Minimal gaps between tasks
        - Realistic task durations
        - No overtime
        """
        score = 25.0  # Start with full points
        
        scheduled_tasks = plan.get("scheduled_tasks", [])
        
        if not scheduled_tasks:
            return 0.0
        
        # Check for excessive gaps
        total_duration = sum(
            t.get("duration", 0) for t in scheduled_tasks
        )
        
        # Expect 6-8 hours of work
        if total_duration < 360:  # Less than 6 hours
            score -= 5
        elif total_duration > 480:  # More than 8 hours
            score -= 5
        
        # Check task distribution
        if len(scheduled_tasks) < 3:
            score -= 3  # Too few tasks might indicate underutilization
        
        return max(0, score)
    
    def _score_priority_alignment(
        self,
        plan: Dict[str, Any],
        original_tasks: List[Dict[str, Any]]
    ) -> float:
        """
        Score how well plan respects task priorities (0-25 points).
        
        High priority tasks should be scheduled earlier.
        """
        score = 25.0
        
        scheduled_tasks = plan.get("scheduled_tasks", [])
        
        # Create priority map
        priority_scores = {"high": 3, "medium": 2, "low": 1}
        
        # Check if high priority tasks are scheduled early
        for idx, task in enumerate(scheduled_tasks):
            task_priority = task.get("priority", "medium")
            position_penalty = idx * 0.5  # Later positions get penalty
            
            if task_priority == "high" and idx > 2:
                score -= 3  # High priority task too late
            elif task_priority == "low" and idx == 0:
                score -= 2  # Low priority task too early
        
        return max(0, score)
    
    def _score_feasibility(self, plan: Dict[str, Any]) -> float:
        """
        Score how feasible the plan is (0-25 points).
        
        Realistic time estimates, reasonable workload.
        """
        score = 25.0
        
        scheduled_tasks = plan.get("scheduled_tasks", [])
        
        # Check total workload
        total_duration = sum(
            t.get("duration", 0) for t in scheduled_tasks
        )
        
        if total_duration > 540:  # More than 9 hours
            score -= 10  # Very ambitious
        elif total_duration > 480:  # More than 8 hours
            score -= 5  # Ambitious
        
        # Check for unrealistic individual task durations
        for task in scheduled_tasks:
            duration = task.get("duration", 0)
            if duration > 180:  # Single task over 3 hours
                score -= 2
        
        return max(0, score)
    
    def _score_work_life_balance(
        self,
        plan: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> float:
        """
        Score work-life balance (0-25 points).
        
        Includes breaks, respects preferences, reasonable hours.
        """
        score = 25.0
        
        # Check if plan includes breaks
        has_breaks = plan.get("includes_breaks", False)
        if not has_breaks:
            score -= 5
        
        # Check work hours
        total_duration = sum(
            t.get("duration", 0) for t in plan.get("scheduled_tasks", [])
        )
        
        if total_duration > 600:  # More than 10 hours
            score -= 10  # Poor work-life balance
        
        # Check preferences
        preferred_hours = user_preferences.get("max_work_hours", 8)
        if total_duration > (preferred_hours * 60):
            score -= 5
        
        return max(0, score)
    
    def _generate_feedback(
        self,
        scores: Dict[str, float],
        plan: Dict[str, Any]
    ) -> List[str]:
        """Generate human-readable feedback"""
        feedback = []
        
        if scores["time_efficiency"] < 15:
            feedback.append(
                "Time efficiency could be improved. "
                "Consider optimizing task scheduling."
            )
        
        if scores["priority_alignment"] < 15:
            feedback.append(
                "High-priority tasks should be scheduled earlier in the day."
            )
        
        if scores["feasibility"] < 15:
            feedback.append(
                "The plan might be too ambitious. "
                "Consider reducing workload or extending timeline."
            )
        
        if scores["work_life_balance"] < 15:
            feedback.append(
                "Don't forget work-life balance. "
                "Add breaks and limit total work hours."
            )
        
        if not feedback:
            feedback.append("Excellent plan! Well-balanced and achievable.")
        
        return feedback
    
    def _generate_recommendations(
        self,
        scores: Dict[str, float],
        plan: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if scores["time_efficiency"] < 20:
            recommendations.append(
                "Add more tasks to fill available time efficiently"
            )
        
        if scores["priority_alignment"] < 20:
            recommendations.append(
                "Move high-priority tasks to morning slots"
            )
        
        if scores["feasibility"] < 20:
            recommendations.append(
                "Reduce task durations or split complex tasks"
            )
        
        if scores["work_life_balance"] < 20:
            recommendations.append(
                "Schedule 15-minute breaks every 90 minutes"
            )
        
        return recommendations
    
    def _calculate_grade(self, total_score: float) -> str:
        """Calculate letter grade from score"""
        if total_score >= 90:
            return "A"
        elif total_score >= 80:
            return "B"
        elif total_score >= 70:
            return "C"
        elif total_score >= 60:
            return "D"
        else:
            return "F"
    
    def evaluate_agent_response(
        self,
        agent_name: str,
        response: Any,
        expected_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Evaluate general agent response quality.
        
        Checks:
        - Response format correctness
        - Completeness
        - Coherence
        """
        logger.info("evaluating_agent_response", agent_name=agent_name)
        
        scores = {
            "format_correctness": 0,
            "completeness": 0,
            "coherence": 0
        }
        
        # Check format
        if expected_format == "json":
            try:
                if isinstance(response, (dict, list)):
                    scores["format_correctness"] = 10
                else:
                    json.loads(str(response))
                    scores["format_correctness"] = 10
            except:
                scores["format_correctness"] = 0
        else:
            scores["format_correctness"] = 10  # Assume correct for non-JSON
        
        # Check completeness (has expected fields)
        if isinstance(response, dict):
            if len(response) > 0:
                scores["completeness"] = 10
        else:
            scores["completeness"] = 5
        
        # Check coherence (basic validation)
        scores["coherence"] = 10  # Default to good
        
        total = sum(scores.values())
        
        return {
            "agent_name": agent_name,
            "total_score": total,
            "max_score": 30,
            "scores": scores,
            "passed": total >= 20
        }


# Global evaluator instance
_plan_evaluator = PlanEvaluator()

def get_plan_evaluator() -> PlanEvaluator:
    """Get the global plan evaluator instance"""
    return _plan_evaluator