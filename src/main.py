"""
Main entry point for the Personal Productivity Agent System.
Run this file to start the complete agent workflow.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

from src.agents.orchestrator import create_orchestrator
from src.utils.config import Config
from src.observability.logger import setup_logger
from src.observability.metrics import get_metrics_collector

logger = setup_logger("main")


async def run_productivity_system():
    """
    Main function to run the productivity agent system.
    
    This demonstrates the complete workflow:
    1. Load tasks from file or user input
    2. Process through agent pipeline
    3. Generate schedule and reminders
    4. Display results
    """
    
    print("\n" + "=" * 70)
    print(" " * 15 + "PERSONAL PRODUCTIVITY AGENT SYSTEM")
    print("=" * 70 + "\n")
    
    logger.info("system_started")
    
    try:
        # Load tasks
        tasks_file = Config.DATA_DIR / "removed_tasksjson"
        
        if tasks_file.exists():
            print(f"📥 Loading tasks from: {tasks_file}")
            with open(tasks_file, 'r') as f:
                tasks = json.load(f)
            print(f"   ✅ Loaded {len(tasks.get('tasks', []))} tasks\n")
        else:
            print("❌ No removed_tasksjson found. Creating sample tasks...\n")
            tasks = create_sample_tasks()
        
        # Create orchestrator
        print("🤖 Initializing AI Agent System...")
        print("   • Collector Agent")
        print("   • Priority Agent")
        print("   • Planner Agent")
        print("   • Reminder Agent")
        print("   • Reflection Agent")
        print("   ✅ All agents ready\n")
        
        orchestrator = create_orchestrator()
        
        # Generate session ID
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"🔄 Processing tasks (Session: {session_id})...")
        print("   This will take a few seconds...\n")
        
        # Process through agent pipeline
        result = await orchestrator.process_tasks(
            raw_tasks=tasks,
            session_id=session_id
        )
        
        # Display results
        display_results(result)
        
        # Save metrics
        metrics = get_metrics_collector()
        metrics.save_metrics()
        
        logger.info("system_completed", session_id=session_id)
        
        print("\n" + "=" * 70)
        print(" " * 20 + "✅ WORKFLOW COMPLETED!")
        print("=" * 70 + "\n")
        
        return result
    
    except Exception as e:
        logger.error("system_error", error=str(e), exc_info=True)
        print(f"\n❌ Error: {str(e)}\n")
        raise


def create_sample_tasks() -> dict:
    """Create sample tasks if none exist"""
    return {
        "tasks": [
            {
                "name": "Team standup meeting",
                "category": "meeting",
                "priority": "high",
                "estimated_duration": 30,
                "deadline": "today"
            },
            {
                "name": "Code review",
                "category": "review",
                "priority": "high",
                "estimated_duration": 60,
                "deadline": "today"
            },
            {
                "name": "Write documentation",
                "category": "writing",
                "priority": "medium",
                "estimated_duration": 90,
                "deadline": "in 2 days"
            }
        ]
    }


def display_results(result: dict):
    """Display formatted results"""
    
    print("\n" + "=" * 70)
    print(" " * 25 + "WORKFLOW RESULTS")
    print("=" * 70 + "\n")
    
    # Workflow summary
    print("📊 WORKFLOW SUMMARY")
    print("-" * 70)
    print(f"Status:           {result['workflow_status']}")
    print(f"Duration:         {result['total_duration_ms']:.0f}ms")
    print(f"A2A Messages:     {result['a2a_messages_sent']}")
    print(f"Steps Completed:  {', '.join(result['steps_completed'])}")
    print()
    
    # Task processing
    outputs = result['outputs']
    
    print("📝 TASK PROCESSING")
    print("-" * 70)
    collected = outputs['collected']
    print(f"Tasks Collected:  {collected['task_count']}")
    
    prioritized = outputs['prioritized']
    print(f"Tasks Prioritized: {prioritized['task_count']}")
    
    print("\nTop 3 Priorities:")
    for task in prioritized['priority_summary']['top_3_tasks'][:3]:
        print(f"   {task['rank']}. {task['name']} (score: {task['score']})")
    print()
    
    # Schedule
    print("📅 SCHEDULE")
    print("-" * 70)
    planned = outputs['planned']
    print(f"Tasks Scheduled:  {planned['task_count']}")
    print(f"Total Work Time:  {planned['total_work_hours']}h")
    print(f"Breaks Included:  {planned['includes_breaks']}")
    print()
    
    # Quality evaluation
    print("⭐ PLAN QUALITY EVALUATION")
    print("-" * 70)
    evaluation = outputs['evaluation']
    print(f"Overall Score:    {evaluation['total_score']}/100 (Grade: {evaluation['grade']})")
    print("\nScore Breakdown:")
    for key, value in evaluation['scores_breakdown'].items():
        bar = "█" * int(value) + "░" * (25 - int(value))
        print(f"   {key:20s} [{bar}] {value:.1f}/25")
    
    if evaluation['feedback']:
        print("\nFeedback:")
        for feedback in evaluation['feedback']:
            print(f"   💬 {feedback}")
    print()
    
    # Reminders
    print("⏰ REMINDERS")
    print("-" * 70)
    reminders = outputs['reminders']
    print(f"Reminders Created: {reminders['reminder_count']}")
    print()
    
    # Files
    print("📁 OUTPUT FILES")
    print("-" * 70)
    for file_type, filepath in reminders['files_created'].items():
        print(f"   {file_type:12s}: {filepath}")
    print()
    
    # Reflection
    print("🔄 REFLECTION & LEARNING")
    print("-" * 70)
    reflection = outputs['reflection']
    print(f"Re-plan Needed:   {reflection['replan_needed']}")
    
    if reflection['replan_needed']:
        print(f"Reason:           {reflection['replan_reason']}")
    
    if reflection['recommendations']:
        print("\nRecommendations:")
        for rec in reflection['recommendations']:
            print(f"   • {rec}")
    print()


def main():
    """Entry point"""
    try:
        asyncio.run(run_productivity_system())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()