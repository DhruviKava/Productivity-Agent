"""
Reflection Agent - Reviews and learns from completed tasks.
Implements loop logic for continuous improvement.

FEATURE COVERED: Loop Agents
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from src.observability.logger import AgentLogger
from src.observability.tracer import AgentTracer
from src.observability.metrics import get_metrics_collector
from src.memory.memory_bank import get_memory_bank
from src.tools.habit_analyzer import get_habit_analyzer

logger = AgentLogger("reflection_agent")
tracer = AgentTracer("reflection_agent")
metrics = get_metrics_collector()


class ReflectionAgent:
    """
    Reflection Agent - Implements loop pattern.
    
    Responsibilities:
    - Review completed tasks
    - Learn patterns from history
    - Identify improvements
    - Re-plan if needed (loop)
    - Update memory bank with insights
    
    This implements: Loop Agents
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.agent_name = "reflection_agent"
        self.model_name = model_name
        self.memory_bank = get_memory_bank()
        self.habit_analyzer = get_habit_analyzer()
        
        logger.logger.info(
            "reflection_agent_initialized",
            model=model_name
        )
    
    async def reflect_and_learn(
        self,
        session_id: str,
        completed_tasks: Optional[List[Dict[str, Any]]] = None,
        planned_tasks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for reflection agent.
        
        This agent runs in a loop:
        1. Analyze completed tasks
        2. Learn patterns
        3. Decide if re-planning needed
        4. If yes, trigger re-plan (loop back)
        
        Args:
            session_id: Session identifier
            completed_tasks: Tasks marked as complete
            planned_tasks: Originally planned tasks
        
        Returns:
            Reflection insights and re-plan recommendation
        """
        start_time_ms = time.time()
        
        logger.log_agent_start({
            "session_id": session_id,
            "completed": len(completed_tasks) if completed_tasks else 0,
            "planned": len(planned_tasks) if planned_tasks else 0
        })
        
        with tracer.trace_operation("reflect_and_learn", {"session_id": session_id}):
            try:
                # Get task history from memory
                task_history = self.memory_bank.memory.get("task_history", [])
                
                # Analyze completion rate
                completion_analysis = self._analyze_completion(
                    completed_tasks or [],
                    planned_tasks or []
                )
                
                # Analyze patterns
                pattern_insights = self._analyze_patterns(task_history)
                
                # Learn from this session
                learning_insights = self._learn_from_session(
                    completed_tasks or [],
                    task_history
                )
                
                # Decide if re-planning needed (LOOP LOGIC)
                replan_decision = self._should_replan(
                    completed_tasks or [],
                    planned_tasks or []
                )
                
                # Update memory bank
                self._update_memory(learning_insights)
                
                # Generate recommendations
                recommendations = self._generate_recommendations(
                    completion_analysis,
                    pattern_insights,
                    learning_insights
                )
                
                result = {
                    "completion_analysis": completion_analysis,
                    "pattern_insights": pattern_insights,
                    "learning_insights": learning_insights,
                    "replan_needed": replan_decision["needed"],
                    "replan_reason": replan_decision["reason"],
                    "recommendations": recommendations,
                    "reflected_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": self.agent_name
                }
                
                duration_ms = (time.time() - start_time_ms) * 1000
                
                logger.log_agent_complete(
                    result={"replan_needed": replan_decision["needed"]},
                    duration_ms=duration_ms
                )
                
                # Log loop decision
                if replan_decision["needed"]:
                    logger.log_decision(
                        decision="LOOP: Re-planning required",
                        reasoning=replan_decision
                    )
                
                metrics.record_agent_execution(
                    agent_name=self.agent_name,
                    duration_ms=duration_ms,
                    success=True,
                    task_count=len(completed_tasks) if completed_tasks else 0
                )
                
                return result
            
            except Exception as e:
                logger.log_error(e, {"session_id": session_id})
                metrics.record_counter(f"{self.agent_name}_errors")
                raise
    
    def _analyze_completion(
        self,
        completed: List[Dict],
        planned: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze task completion rate.
        
        Compare completed vs planned to identify issues.
        """
        planned_count = len(planned)
        completed_count = len(completed)
        
        if planned_count == 0:
            completion_rate = 0.0
        else:
            completion_rate = (completed_count / planned_count) * 100
        
        # Analyze incomplete tasks
        incomplete = planned_count - completed_count
        
        analysis = {
            "planned_tasks": planned_count,
            "completed_tasks": completed_count,
            "incomplete_tasks": incomplete,
            "completion_rate": round(completion_rate, 1),
            "status": self._get_completion_status(completion_rate)
        }
        
        logger.logger.info(
            "completion_analyzed",
            rate=completion_rate,
            status=analysis["status"]
        )
        
        return analysis
    
    def _get_completion_status(self, rate: float) -> str:
        """Get status based on completion rate"""
        if rate >= 90:
            return "excellent"
        elif rate >= 70:
            return "good"
        elif rate >= 50:
            return "fair"
        else:
            return "needs_improvement"
    
    def _analyze_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """
        Analyze patterns using habit analyzer tool.
        
        Identifies productivity trends.
        """
        if not history:
            return {"message": "Insufficient history for pattern analysis"}
        
        # Use habit analyzer tool
        productivity = self.habit_analyzer.analyze_productivity_hours(history)
        duration_accuracy = self.habit_analyzer.analyze_task_duration_accuracy(history)
        patterns = self.habit_analyzer.identify_task_patterns(history)
        
        insights = {
            "productivity_hours": productivity.get("peak_productivity_hours", []),
            "estimation_tendency": duration_accuracy.get("tendency", "unknown"),
            "top_categories": patterns.get("top_categories", []),
            "pattern_count": len(history)
        }
        
        logger.logger.info("patterns_analyzed", insights=insights)
        
        return insights
    
    def _learn_from_session(self, completed, history):
        """
        Learn from completed tasks. Handles cases where completed may contain
        invalid data types (e.g., strings).
        """

        # Filter out invalid entries
        valid_completed = [
            t for t in completed
            if isinstance(t, dict)
        ]

        if not valid_completed:
            return {
                "average_duration": None,
                "task_count": 0,
                "insight": "No completed tasks to learn from yet."
            }

        total_duration = sum(
            t.get("actual_duration", t.get("duration", 0))
            for t in valid_completed
        )
        avg_duration = total_duration / len(valid_completed)

        return {
            "average_duration": avg_duration,
            "task_count": len(valid_completed),
            "insight": "Learned from completed tasks successfully."
        }
  
    def _should_replan(
        self,
        completed: List[Dict],
        planned: List[Dict]
    ) -> Dict[str, Any]:
        """
        Decide if re-planning is needed (LOOP LOGIC).
        
        Re-plan if:
        - Completion rate < 50%
        - Multiple high-priority tasks incomplete
        - Major timing issues detected
        
        This is the LOOP implementation!
        """
        planned_count = len(planned)
        completed_count = len(completed)
        
        if planned_count == 0:
            return {
                "needed": False,
                "reason": "No planned tasks to review"
            }
        
        completion_rate = (completed_count / planned_count) * 100
        
        # Check if re-planning needed
        replan_needed = False
        reasons = []
        
        # Reason 1: Low completion rate
        if completion_rate < 50:
            replan_needed = True
            reasons.append(
                f"Low completion rate ({completion_rate:.1f}%). "
                "Tasks may need re-prioritization."
            )
        
        # Reason 2: High-priority tasks incomplete
        incomplete_high_priority = [
            t for t in planned
            if t.get("priority") == "high" and t.get("id") not in [
                c.get("id") for c in completed
            ]
        ]
        
        if len(incomplete_high_priority) >= 2:
            replan_needed = True
            reasons.append(
                f"{len(incomplete_high_priority)} high-priority tasks incomplete. "
                "Recommend re-planning remaining tasks."
            )
        
        # Reason 3: Major overruns
        # (In real implementation, check actual vs estimated time)
        
        decision = {
            "needed": replan_needed,
            "reason": " ".join(reasons) if reasons else "On track, no re-planning needed",
            "incomplete_tasks": planned_count - completed_count,
            "completion_rate": round(completion_rate, 1)
        }
        
        return decision
    
    def _update_memory(self, insights: Dict[str, Any]):
        """
        Update memory bank with new insights.
        
        Stores learned patterns for future use.
        """
        # Store patterns learned
        for pattern in insights.get("patterns_learned", []):
            pattern_name = pattern.get("pattern")
            self.memory_bank.learn_pattern(pattern_name, pattern)
        
        logger.logger.info("memory_updated", insights_count=len(insights))
    
    def _generate_recommendations(
        self,
        completion: Dict,
        patterns: Dict,
        learnings: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on completion rate
        status = completion.get("status")
        if status == "needs_improvement":
            recommendations.append(
                "Consider reducing daily workload or extending deadlines"
            )
        elif status == "excellent":
            recommendations.append(
                "Great job! You can handle slightly more tasks"
            )
        
        # Based on patterns
        if patterns.get("productivity_hours"):
            peak = patterns["productivity_hours"][0]
            recommendations.append(
                f"Schedule critical tasks around {peak}:00 for best results"
            )
        
        # Based on estimation
        tendency = patterns.get("estimation_tendency")
        if tendency == "underestimates":
            recommendations.append(
                "Add 20-30% buffer to your time estimates"
            )
        elif tendency == "overestimates":
            recommendations.append(
                "You can reduce time estimates by 15-20%"
            )
        
        return recommendations


# Factory function
def create_reflection_agent() -> ReflectionAgent:
    """Create and return a ReflectionAgent instance"""
    return ReflectionAgent()