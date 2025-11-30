from typing import Dict, Any, List
import json
import os
import re

from src.observability.logger import AgentLogger
from src.observability.tracer import AgentTracer
from src.observability.metrics import get_metrics_collector

logger = AgentLogger("collector_agent")
tracer = AgentTracer("collector_agent")
metrics = get_metrics_collector()


class CollectorAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.agent_name = "collector_agent"
        self.model_name = model_name

        logger.logger.info("collector_agent_initialized", model=model_name)

    # ------------------------------------------------------
    # NEW INPUT PARSER (replaces tasks.json dependency)
    # ------------------------------------------------------
    def _parse_user_input(self, raw: Any):
        if raw is None:
            return []

        # Convert bytes to string
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")

        raw = str(raw).strip()

        # Try JSON → list or dict
        try:
            parsed = json.loads(raw)

            if isinstance(parsed, dict) and "tasks" in parsed:
                return [self._normalize(t) for t in parsed["tasks"]]

            if isinstance(parsed, list):
                return [self._normalize(t) for t in parsed]

            if isinstance(parsed, dict):
                return [self._normalize(parsed)]
        except Exception:
            pass

        # Fallback: text
        return [{"name": l, "category": "general"} for l in raw.splitlines() if l.strip()]

    # ------------------------------------------------------
    # Normalization (identical to your original)
    # ------------------------------------------------------
    def _normalize(self, task):
        duration = (
            task.get("estimated_duration")
            or task.get("estimated_time")
            or task.get("duration")
            or 60
        )

        deadline = (
            task.get("deadline")
            or task.get("due_date")
        )

        return {
            "id": task.get("id"),
            "name": task.get("name", "Unnamed Task"),
            "priority": task.get("priority", "medium"),
            "category": task.get("category", "general"),
            "estimated_duration": duration,
            "deadline": deadline,
            "description": task.get("description", ""),
            "tags": task.get("tags", []),
            "dependencies": task.get("dependencies", []),
            "status": task.get("status", "pending"),
            "actual_duration": task.get("actual_time", 0),
            "assignee": task.get("assignee", "Unknown"),
        }

    # ------------------------------------------------------
    # MAIN ENTRY POINT (must match orchestrator signature)
    # ------------------------------------------------------
    async def collect_tasks(self, input_data, session_id):
        try:
            if isinstance(input_data, dict) and "raw_input" in input_data:
                raw = input_data["raw_input"]
            else:
                raw = input_data

            # Convert bytes to string
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")

            raw = str(raw).strip()

            # Try JSON
            try:
                parsed = json.loads(raw)

                # JSON with "tasks"
                if isinstance(parsed, dict) and "tasks" in parsed:
                    tasks = [self._normalize(t) for t in parsed["tasks"]]
                    return {"tasks": tasks, "task_count": len(tasks)}

                # JSON list
                if isinstance(parsed, list):
                    tasks = [self._normalize(t) for t in parsed]
                    return {"tasks": tasks, "task_count": len(tasks)}

            except:
                pass

            # Fallback plain text
                        # Fallback plain text
            # Support lines like: "Task name (high, 60 min)" OR just "Task name"
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            tasks: List[Dict[str, Any]] = []

            # pattern: Task name (high, 60 min)
            pattern = re.compile(
                r"""
                ^(?P<name>.+?)              # task name (greedy but minimal due to following ' (')
                \s*\(                       # opening parenthesis
                    \s*(?P<priority>high|medium|low)\s*,\s*
                    (?P<duration>\d+)\s*min
                \)\s*$
                """,
                re.IGNORECASE | re.VERBOSE,
            )

            for line in lines:
                m = pattern.match(line)
                if m:
                    name = m.group("name").strip()
                    priority = m.group("priority").lower()
                    duration = int(m.group("duration"))
                else:
                    # If user didn't follow "(priority, N min)" format,
                    # fall back to old behaviour.
                    name = line
                    priority = "medium"
                    duration = 60

                tasks.append(
                    {
                        "name": name,
                        "priority": priority,
                        "category": "general",
                        "estimated_duration": duration,
                    }
                )

            return {"tasks": tasks, "task_count": len(tasks)}


        except Exception as e:
            logger.log_error(e, {"session_id": session_id})
            raise

def create_collector_agent():
    return CollectorAgent()
