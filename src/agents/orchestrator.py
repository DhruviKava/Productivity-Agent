"""
Main Orchestrator - Coordinates all agents using A2A Protocol.
Implements Agent-to-Agent communication.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import time
import json

from src.observability.logger import AgentLogger
from src.observability.tracer import AgentTracer, trace_agent_communication
from src.observability.metrics import get_metrics_collector
from src.memory.session_manager import get_session_service
from src.memory.memory_bank import get_memory_bank
from src.evaluation.plan_evaluator import get_plan_evaluator

# Import all agents
from src.agents.collector_agent import create_collector_agent
from src.agents.priority_agent import create_priority_agent
from src.agents.planner_agent import create_planner_agent
from src.agents.reminder_agent import create_reminder_agent
from src.agents.reflection_agent import create_reflection_agent

logger = AgentLogger("orchestrator")
tracer = AgentTracer("orchestrator")
metrics = get_metrics_collector()


class A2AMessage:
    """Agent-to-Agent Protocol Message format."""
    
    def __init__(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        data: Any,
        session_id: str
    ):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.message_type = message_type
        self.data = data
        self.session_id = session_id
        self.timestamp = datetime.now().isoformat()
        self.message_id = f"msg_{int(time.time() * 1000)}"
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.message_type,
            "data": self.data,
            "session_id": self.session_id,
            "timestamp": self.timestamp
        }


class AgentOrchestrator:
    """
    Main Orchestrator using A2A Protocol.
    """

    def __init__(self):
        self.orchestrator_name = "orchestrator"
        
        self.collector = create_collector_agent()
        self.priority = create_priority_agent()
        self.planner = create_planner_agent()
        self.reminder = create_reminder_agent()
        self.reflection = create_reflection_agent()
        
        self.session_service = get_session_service()
        self.memory_bank = get_memory_bank()
        self.evaluator = get_plan_evaluator()
        
        self.message_queue: List[A2AMessage] = []
        
        logger.logger.info("orchestrator_initialized", agents=5)

    # -----------------------------------------------------------------------------------

    async def process_tasks(
        self,
        raw_tasks: Any,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:

        start_time = time.time()

        if not session_id:
            session_id = f"session_{int(time.time())}"

        session = self.session_service.get_session(session_id)
        if not session:
            session = self.session_service.create_session(session_id)

        logger.log_agent_start({
            "session_id": session_id,
            "workflow": "full_pipeline"
        })

        with tracer.trace_operation("full_workflow", {"session_id": session_id}):
            try:
                # --------------------
                # 1. Collector
                # --------------------
                collected = await self._send_to_agent(
                    "orchestrator", "collector",
                    "collect_tasks",
                    {"raw_input": raw_tasks},
                    session_id,
                    self.collector.collect_tasks
                )

                self.session_service.update_context(session_id, "collected_tasks", collected)

                # --------------------
                # 2. Priority Agent
                # --------------------
                prioritized = await self._send_to_agent(
                    "collector", "priority",
                    "prioritize_tasks",
                    collected,
                    session_id,
                    self.priority.prioritize_tasks
                )

                self.session_service.update_context(session_id, "prioritized_tasks", prioritized)

                # --------------------
                # 3. Planner Agent
                # --------------------
                planned = await self._send_to_agent(
                    "priority", "planner",
                    "create_plan",
                    prioritized,
                    session_id,
                    self.planner.create_plan
                )

                # 🔥 SAVE formatted schedule so UI can read it directly
                formatted_schedule = planned.get("formatted_schedule", "")
                self.session_service.update_context(session_id, "formatted_schedule", formatted_schedule)

                self.session_service.update_context(session_id, "planned_schedule", planned)

                # --------------------
                # 4. Evaluate Plan
                # --------------------
                evaluation = self.evaluator.evaluate_plan(
                    plan=planned,
                    original_tasks=collected.get("tasks", [])
                )

                # --------------------
                # 5. Reminder Agent
                # --------------------
                reminders = await self._send_to_agent(
                    "planner", "reminder",
                    "create_reminders",
                    planned,
                    session_id,
                    self.reminder.create_reminders
                )

                # --------------------
                # 6. Reflection Agent
                # --------------------
                reflection = await self._send_to_agent(
                    "reminder", "reflection",
                    "reflect",
                    {
                        "planned_tasks": planned.get("scheduled_tasks", []),
                        "completed_tasks": []
                    },
                    session_id,
                    self.reflection.reflect_and_learn
                )

                duration_ms = (time.time() - start_time) * 1000

                # FINAL RESULT (UI reads this)
                result = {
                    "session_id": session_id,
                    "workflow_status": "completed",
                    "formatted_schedule": formatted_schedule,   # 🔥 KEY FIX
                    "outputs": {
                        "collected": collected,
                        "prioritized": prioritized,
                        "planned": planned,
                        "evaluation": evaluation,
                        "reminders": reminders,
                        "reflection": reflection
                    },
                    "completed_at": datetime.now().isoformat()
                }

                logger.log_agent_complete({"workflow": "success"}, duration_ms)
                metrics.record_counter("workflows_completed")

                return result

            except Exception as e:
                logger.log_error(e, {"session_id": session_id})
                metrics.record_counter("workflows_failed")
                raise

    # -----------------------------------------------------------------------------------

    async def _send_to_agent(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        data: Any,
        session_id: str,
        handler: callable
    ) -> Any:

        message = A2AMessage(from_agent, to_agent, message_type, data, session_id)
        self.message_queue.append(message)

        with trace_agent_communication(from_agent, to_agent, message_type):
            logger.logger.info(
                "a2a_message_sent",
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=message_type,
                message_id=message.message_id
            )

            result = await handler(data, session_id)

            logger.logger.info(
                "a2a_message_received",
                from_agent=from_agent,
                to_agent=to_agent,
                message_id=message.message_id
            )

            return result

# -----------------------------------------------------------------------------------

def create_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator()
