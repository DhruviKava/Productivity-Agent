"""
Priority Agent - Ranks tasks by importance and urgency.
Second agent in the sequential pipeline.

FEATURE COVERED: Sequential Agents
"""

from typing import Dict, List, Any
from datetime import datetime
import time

from src.observability.logger import AgentLogger
from src.observability.tracer import AgentTracer
from src.observability.metrics import get_metrics_collector
from src.utils.helpers import calculate_priority_score
from src.memory.memory_bank import get_memory_bank

logger = AgentLogger("priority_agent")
tracer = AgentTracer("priority_agent")
metrics = get_metrics_collector()


class PriorityAgent:
    """
    Priority Agent - Second in the sequential pipeline.
    """

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.agent_name = "priority_agent"
        self.model_name = model_name
        self.memory_bank = get_memory_bank()

        logger.logger.info(
            "priority_agent_initialized",
            model=model_name
        )

    async def prioritize_tasks(
        self,
        collected_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        start_time = time.time()

        logger.log_agent_start({
            "session_id": session_id,
            "task_count": collected_data.get("task_count", 0)
        })

        with tracer.trace_operation("prioritize_tasks", {"session_id": session_id}):
            try:
                tasks = collected_data.get("tasks", [])

                scored_tasks = [self._score_task(t) for t in tasks]

                sorted_tasks = sorted(
                    scored_tasks,
                    key=lambda x: x["priority_score"],
                    reverse=True
                )

                for idx, task in enumerate(sorted_tasks):
                    task["rank"] = idx + 1

                adjusted_tasks = self._apply_user_preferences(sorted_tasks)

                result = {
                    "prioritized_tasks": adjusted_tasks,
                    "task_count": len(adjusted_tasks),
                    "prioritized_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": self.agent_name,
                    "priority_summary": self._generate_summary(adjusted_tasks)
                }

                duration_ms = (time.time() - start_time) * 1000
                logger.log_agent_complete(
                    result={"task_count": len(adjusted_tasks)},
                    duration_ms=duration_ms
                )

                metrics.record_agent_execution(
                    agent_name=self.agent_name,
                    duration_ms=duration_ms,
                    success=True,
                    task_count=len(adjusted_tasks)
                )

                return result

            except Exception as e:
                logger.log_error(e, {"session_id": session_id})
                metrics.record_counter(f"{self.agent_name}_errors")
                raise

    def _score_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes urgency, importance, effort, and deadline-based score.
        """

        name = task.get("name", "Unnamed Task")

        priority_map = {"high": 5, "medium": 3, "low": 1}
        urgency = priority_map.get(task.get("priority", "medium"), 3)

        importance_map = {
            "meeting": 4,
            "coding": 3,
            "review": 3,
            "planning": 3,
            "learning": 2,
            "email": 2,
            "general": 2
        }
        importance = importance_map.get(task.get("category", "general"), 2)

        duration = task.get("estimated_duration", 60)
        if duration <= 30:
            effort = 1
        elif duration <= 60:
            effort = 2
        elif duration <= 120:
            effort = 3
        elif duration <= 180:
            effort = 4
        else:
            effort = 5

        deadline_days = None
        if task.get("deadline"):
            try:
                deadline = datetime.fromisoformat(task["deadline"])
                days_remaining = (deadline - datetime.now()).days
                deadline_days = max(days_remaining, 0)
            except:
                deadline_days = None

        score = calculate_priority_score(
            urgency=urgency,
            importance=importance,
            effort=effort,
            deadline_days=deadline_days
        )

        task["priority_score"] = score
        task["scoring_details"] = {
            "urgency": urgency,
            "importance": importance,
            "effort": effort,
            "deadline_days": deadline_days
        }

        logger.log_decision(
            decision=f"Scored task: {name}",
            reasoning={
                "score": score,
                "urgency": urgency,
                "importance": importance,
                "effort": effort,
                "deadline_days": deadline_days
            }
        )

        return task

    def _apply_user_preferences(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        preferred_categories = self.memory_bank.get_preference(
            "morning_categories",
            ["meeting", "review"]
        )

        for task in tasks:
            if task.get("category") in preferred_categories:
                task["priority_score"] += 0.2
                task["adjusted_for_preferences"] = True

        tasks = sorted(tasks, key=lambda x: x["priority_score"], reverse=True)

        for idx, task in enumerate(tasks):
            task["rank"] = idx + 1

        return tasks

    def _generate_summary(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Produce a clean summary without crashing when deadline is None"""

        urgent_tasks = []
        for t in tasks:
            details = t.get("scoring_details", {})
            deadline_days = details.get("deadline_days")

            if deadline_days is None:
                continue
            if deadline_days <= 1:
                urgent_tasks.append(t)

        return {
            "total_tasks": len(tasks),
            "by_priority": {
                "high": sum(1 for t in tasks if t.get("priority") == "high"),
                "medium": sum(1 for t in tasks if t.get("priority") == "medium"),
                "low": sum(1 for t in tasks if t.get("priority") == "low"),
            },
            "urgent_tasks_count": len(urgent_tasks),
            "top_3_tasks": [
                {
                    "rank": t.get("rank"),
                    "name": t.get("name", "Unnamed Task"),
                    "score": t.get("priority_score", 0)
                }
                for t in tasks[:3]
            ]
        }


def create_priority_agent() -> PriorityAgent:
    return PriorityAgent()
