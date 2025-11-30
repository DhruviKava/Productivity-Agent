"""
Reminder Agent - Creates reminders and saves schedule.
Fourth agent in the sequential pipeline.

FEATURE COVERED: Sequential Agents, MCP Tools
"""

from typing import Dict, List, Any
from datetime import datetime
from datetime import timedelta
import time

from src.observability.logger import AgentLogger
from src.observability.tracer import AgentTracer
from src.observability.metrics import get_metrics_collector
from src.tools.mcp_tools import get_mcp_tool

logger = AgentLogger("reminder_agent")
tracer = AgentTracer("reminder_agent")
metrics = get_metrics_collector()


class ReminderAgent:
    """
    Reminder Agent - Fourth in the sequential pipeline.
    
    Responsibilities:
    - Create reminders for scheduled tasks
    - Save schedule using MCP tools
    - Generate notification list
    - Export in multiple formats
    
    This implements:
    - Sequential Agents
    - MCP Tools usage
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.agent_name = "reminder_agent"
        self.model_name = model_name
        self.mcp_tool = get_mcp_tool()
        
        logger.logger.info(
            "reminder_agent_initialized",
            model=model_name
        )
    
    async def create_reminders(
        self,
        plan_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Main entry point for reminder agent.
        
        Args:
            plan_data: Output from PlannerAgent
            session_id: Session identifier
        
        Returns:
            Reminders and saved file locations
        """
        start_time_ms = time.time()
        
        logger.log_agent_start({
            "session_id": session_id,
            "tasks": plan_data.get("task_count", 0)
        })
        
        with tracer.trace_operation("create_reminders", {"session_id": session_id}):
            try:
                scheduled_tasks = plan_data.get("scheduled_tasks", [])
                
                # Generate reminders
                reminders = self._generate_reminders(scheduled_tasks)
                
                # Save schedule using MCP tool
                logger.log_tool_use("mcp_write_file", {
                    "filename": "schedule.json",
                    "content_type": "schedule"
                })
                
                schedule_result = self.mcp_tool.write_file(
                    filename=f"schedule_{session_id}.json",
                    content=plan_data,
                    format="json"
                )
                
                # Save reminders using MCP tool
                logger.log_tool_use("mcp_write_file", {
                    "filename": "reminders.json",
                    "content_type": "reminders"
                })
                
                reminders_result = self.mcp_tool.write_file(
                    filename=f"reminders_{session_id}.json",
                    content={"reminders": reminders},
                    format="json"
                )
                
                # Generate human-readable summary
                summary = self._generate_summary(scheduled_tasks, reminders)
                
                # Save summary as text
                summary_result = self.mcp_tool.write_file(
                    filename=f"summary_{session_id}.txt",
                    content=summary,
                    format="text"
                )
                
                result = {
                    "reminders": reminders,
                    "reminder_count": len(reminders),
                    "files_created": {
                        "schedule": schedule_result.get("filepath"),
                        "reminders": reminders_result.get("filepath"),
                        "summary": summary_result.get("filepath")
                    },
                    "summary": summary,
                    "created_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": self.agent_name
                }
                
                duration_ms = (time.time() - start_time_ms) * 1000
                
                logger.log_agent_complete(
                    result={"reminders": len(reminders)},
                    duration_ms=duration_ms
                )
                
                metrics.record_agent_execution(
                    agent_name=self.agent_name,
                    duration_ms=duration_ms,
                    success=True,
                    task_count=len(reminders)
                )
                
                return result
            
            except Exception as e:
                logger.log_error(e, {"session_id": session_id})
                metrics.record_counter(f"{self.agent_name}_errors")
                raise
    
    def _generate_reminders(
        self,
        scheduled_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate reminders for scheduled tasks.
        
        Reminder strategy:
        - 5 min before high priority tasks
        - 15 min before meetings
        - At start time for other tasks
        """
        reminders = []
        
        for task in scheduled_tasks:
            if task.get("type") != "task":
                continue  # Skip breaks
            
            task_name = task.get("name")
            start_time = datetime.fromisoformat(task.get("start_time"))
            priority = task.get("priority", "medium")
            category = task.get("category", "general")
            
            # Determine reminder timing
            if category == "meeting":
                reminder_minutes_before = 15
            elif priority == "high":
                reminder_minutes_before = 5
            else:
                reminder_minutes_before = 0  # At start time
            
            reminder_time = start_time
            if reminder_minutes_before > 0:
                reminder_time = start_time - timedelta(minutes=reminder_minutes_before)
            
            reminder = {
                "reminder_id": f"reminder_{task.get('task_id')}",
                "task_id": task.get("task_id"),
                "task_name": task_name,
                "reminder_time": reminder_time.isoformat(),
                "task_start_time": start_time.isoformat(),
                "minutes_before": reminder_minutes_before,
                "priority": priority,
                "message": self._create_reminder_message(
                    task_name,
                    start_time,
                    reminder_minutes_before
                )
            }
            
            reminders.append(reminder)
        
        logger.logger.info("reminders_generated", count=len(reminders))
        
        return reminders
    
    def _create_reminder_message(
        self,
        task_name: str,
        start_time: datetime,
        minutes_before: int
    ) -> str:
        """Create a user-friendly reminder message"""
        time_str = start_time.strftime("%I:%M %p")
        
        if minutes_before == 0:
            return f"⏰ Time to start: {task_name} (scheduled for {time_str})"
        else:
            return f"⏰ Reminder: {task_name} starts in {minutes_before} minutes at {time_str}"
    
    def _generate_summary(
        self,
        scheduled_tasks: List[Dict[str, Any]],
        reminders: List[Dict[str, Any]]
    ) -> str:
        """
        Generate human-readable schedule summary.
        
        Creates a nicely formatted text summary of the day.
        """
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("YOUR DAILY SCHEDULE")
        summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        summary_lines.append("=" * 60)
        summary_lines.append("")
        
        # Task breakdown
        tasks = [t for t in scheduled_tasks if t.get("type") == "task"]
        breaks = [t for t in scheduled_tasks if t.get("type") == "break"]
        
        total_work = sum(t.get("duration", 0) for t in tasks)
        total_break = sum(t.get("duration", 0) for t in breaks)
        
        summary_lines.append(f"📊 Overview:")
        summary_lines.append(f"   • Total Tasks: {len(tasks)}")
        summary_lines.append(f"   • Work Time: {total_work // 60}h {total_work % 60}m")
        summary_lines.append(f"   • Break Time: {total_break // 60}h {total_break % 60}m")
        summary_lines.append(f"   • Reminders Set: {len(reminders)}")
        summary_lines.append("")
        
        # Detailed schedule
        summary_lines.append("📅 Detailed Schedule:")
        summary_lines.append("-" * 60)
        
        for item in scheduled_tasks:
            start = datetime.fromisoformat(item.get("start_time"))
            end = datetime.fromisoformat(item.get("end_time"))
            duration = item.get("duration")
            
            if item.get("type") == "task":
                priority = item.get("priority", "medium")
                priority_icon = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(priority, "⚪")
                
                summary_lines.append(
                    f"{priority_icon} {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} "
                    f"({duration}min)"
                )
                summary_lines.append(f"   {item.get('name')}")
                summary_lines.append(f"   Category: {item.get('category', 'general')}")
            else:
                summary_lines.append(
                    f"☕ {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} "
                    f"| {item.get('name')}"
                )
            
            summary_lines.append("")
        
        summary_lines.append("=" * 60)
        summary_lines.append("💡 Tips:")
        summary_lines.append("   • Take breaks regularly to maintain focus")
        summary_lines.append("   • Check reminders to stay on track")
        summary_lines.append("   • Adjust priorities if needed during the day")
        summary_lines.append("=" * 60)
        
        return "\n".join(summary_lines)


# Factory function
def create_reminder_agent() -> ReminderAgent:
    """Create and return a ReminderAgent instance"""
    return ReminderAgent()