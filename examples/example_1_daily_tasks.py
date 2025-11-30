"""
Example 1: Process daily tasks through the agent system.
Demonstrates the complete workflow from input to output.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.orchestrator import create_orchestrator
from src.utils.config import Config


async def main():
    """Run example 1: Daily task processing"""
    
    print("=" * 60)
    print("EXAMPLE 1: Daily Task Processing")
    print("=" * 60)
    print()
    
    # Load sample tasks
    tasks_file = Config.DATA_DIR / "removed_tasksjson"
    with open(tasks_file, 'r') as f:
        tasks_data = json.load(f)
    
    print(f"📥 Loaded {len(tasks_data['tasks'])} tasks")
    print()
    
    # Create orchestrator
    print("🤖 Initializing agent system...")
    orchestrator = create_orchestrator()
    print("✅ All 5 agents initialized")
    print()
    
    # Process tasks
    print("⚙️  Processing tasks through agent pipeline...")
    print("   Step 1: Collector Agent - Normalizing tasks")
    print("   Step 2: Priority Agent - Ranking by importance")
    print("   Step 3: Planner Agent - Creating schedule")
    print("   Step 4: Reminder Agent - Generating reminders")
    print("   Step 5: Reflection Agent - Learning patterns")
    print()
    
    result = await orchestrator.process_tasks(
        raw_tasks=tasks_data,
        session_id="example_1_session"
    )
    
    # Display results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print()
    
    # Summary
    print("📊 Workflow Summary:")
    print(f"   Status: {result['workflow_status']}")
    print(f"   Duration: {result['total_duration_ms']:.0f}ms")
    print(f"   A2A Messages: {result['a2a_messages_sent']}")
    print()
    
    # Collected tasks
    collected = result['outputs']['collected']
    print(f"✅ Collected: {collected['task_count']} tasks")
    print()
    
    # Prioritized tasks
    prioritized = result['outputs']['prioritized']
    print(f"🎯 Prioritized: {prioritized['task_count']} tasks")
    print("   Top 3 priorities:")
    for task in prioritized['priority_summary']['top_3_tasks']:
        print(f"      {task['rank']}. {task['name']} (score: {task['score']})")
    print()
    
    # Planned schedule
    planned = result['outputs']['planned']
    print(f"📅 Planned: {planned['task_count']} tasks")
    print(f"   Total work time: {planned['total_work_hours']}h")
    print(f"   Includes breaks: {planned['includes_breaks']}")
    print()
    
    # Evaluation
    evaluation = result['outputs']['evaluation']
    print(f"⭐ Plan Quality Score: {evaluation['total_score']}/100 (Grade: {evaluation['grade']})")
    print("   Breakdown:")
    for key, value in evaluation['scores_breakdown'].items():
        print(f"      {key}: {value:.1f}/25")
    print()
    
    # Reminders
    reminders = result['outputs']['reminders']
    print(f"⏰ Reminders: {reminders['reminder_count']} created")
    print()
    
    # Reflection
    reflection = result['outputs']['reflection']
    print(f"🔄 Reflection:")
    print(f"   Re-plan needed: {reflection['replan_needed']}")
    if reflection['recommendations']:
        print(f"   Recommendations:")
        for rec in reflection['recommendations']:
            print(f"      • {rec}")
    print()
    
    # Files created
    print("📁 Files created:")
    for file_type, filepath in reminders['files_created'].items():
        print(f"   {file_type}: {filepath}")
    print()
    
    # A2A message log
    print("📨 A2A Communication Log:")
    a2a_messages = orchestrator.get_a2a_message_log()
    for msg in a2a_messages:
        print(f"   {msg['from']} → {msg['to']}: {msg['type']}")
    print()
    
    print("=" * 60)
    print("✅ Example 1 completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())