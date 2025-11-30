"""
Planner Agent - Generates human readable daily schedule (pretty format)
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
import time
from tzlocal import get_localzone

from src.observability.logger import AgentLogger
from src.observability.tracer import AgentTracer
from src.observability.metrics import get_metrics_collector

logger = AgentLogger("planner_agent")
tracer = AgentTracer("planner_agent")
metrics = get_metrics_collector()


class PlannerAgent:

    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.agent_name = "planner_agent"
        self.model_name = model_name
        logger.logger.info("planner_agent_initialized", model=model_name)

    # ---------------------------------------------------------

    def _priority_icon(self, priority: str):
        return {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }.get(priority, "🟡")

    # ---------------------------------------------------------

    def _format_task_block(self, task):
        start = datetime.fromisoformat(task["start_time"])
        end = datetime.fromisoformat(task["end_time"])
        minutes = int((end - start).total_seconds() // 60)

        icon = self._priority_icon(task["priority"])

        return (
            f"{icon} {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} ({minutes}min)\n"
            f"   {task['name']}\n"
            f"   Category: {task['category']}\n"
        )

    # ---------------------------------------------------------

    def _format_break(self, block):
        start = datetime.fromisoformat(block["start_time"])
        end = datetime.fromisoformat(block["end_time"])
        minutes = int((end - start).total_seconds() // 60)

        return f"☕ {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} | {minutes}-minute break\n"

    # ---------------------------------------------------------

    def _schedule_tasks(self, tasks):
        # Sort: priority → deadline
        tasks = sorted(tasks, key=lambda x: (
            {"high": 1, "medium": 2, "low": 3}.get(x["priority"], 2),
            x.get("deadline", "")
        ))

        schedule = []
        local_tz = get_localzone()
        now_local = datetime.now(local_tz)

        current = now_local.replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0
        )

        for t in tasks:
            duration = t.get("estimated_duration", 60)

            start_time = current
            end_time = start_time + timedelta(minutes=duration)

            schedule.append({
                "type": "task",
                "name": t["name"],
                "category": t["category"],
                "priority": t["priority"],
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration
            })

            # break
            break_len = 15 if duration >= 60 else 5

            break_start = end_time
            break_end = break_start + timedelta(minutes=break_len)

            schedule.append({
                "type": "break",
                "start_time": break_start.isoformat(),
                "end_time": break_end.isoformat(),
                "duration": break_len,
                "name": f"{break_len}-minute break"
            })

            current = break_end

        return schedule

    # ---------------------------------------------------------

    async def create_plan(self, prioritized_data, session_id, work_hours=(9, 17)):

        tasks = prioritized_data.get("prioritized_tasks", [])

        schedule = self._schedule_tasks(tasks)

        # Build pretty text
        lines = []
        lines.append("="*60)
        lines.append("YOUR DAILY SCHEDULE")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        lines.append("="*60)
        lines.append("")

        task_items = [t for t in schedule if t["type"] == "task"]
        break_items = [t for t in schedule if t["type"] == "break"]

        total_work = sum(t["duration"] for t in task_items)
        total_break = sum(t["duration"] for t in break_items)

        lines.append("📊 Overview:")
        lines.append(f"   • Total Tasks: {len(task_items)}")
        lines.append(f"   • Work Time: {total_work//60}h {total_work%60}m")
        lines.append(f"   • Break Time: {total_break//60}h {total_break%60}m")
        lines.append(f"   • Reminders Set: {len(task_items)}")
        lines.append("")
        lines.append("📅 Detailed Schedule:")
        lines.append("-"*60)

        for block in schedule:
            if block["type"] == "task":
                lines.append(self._format_task_block(block))
            else:
                lines.append(self._format_break(block))

        lines.append("="*60)
        lines.append("💡 Tips:")
        lines.append("   • Take breaks regularly to maintain focus")
        lines.append("   • Check reminders to stay on track")
        lines.append("   • Adjust priorities if needed during the day")
        lines.append("="*60)

        formatted = "\n".join(lines)

        return {
            "scheduled_tasks": schedule,
            "formatted_schedule": formatted,
            "task_count": len(task_items),
            "total_work_minutes": total_work
        }


def create_planner_agent():
    return PlannerAgent()
