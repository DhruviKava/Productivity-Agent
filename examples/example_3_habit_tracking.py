"""
Example 3: Demonstrates memory and learning capabilities.
Shows how the system learns from task history.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.memory_bank import get_memory_bank
from src.tools.habit_analyzer import get_habit_analyzer


async def main():
    """Run example 3: Memory and learning"""
    
    print("=" * 60)
    print("EXAMPLE 3: Memory & Learning")
    print("=" * 60)
    print()
    
    memory_bank = get_memory_bank()
    habit_analyzer = get_habit_analyzer()
    
    # Store some preferences
    print("💾 Storing user preferences...")
    memory_bank.store_preference("work_hours_start", "09:00")
    memory_bank.store_preference("work_hours_end", "17:00")
    memory_bank.store_preference("preferred_break_duration", 15)
    print("   ✅ Preferences saved")
    print()
    
    # Simulate task history
    print("📚 Adding simulated task history...")
    
    for i in range(10):
        completed_time = datetime.now() - timedelta(days=i)
        task = {
            "id": f"task_{i}",
            "name": f"Historical Task {i}",
            "category": "coding" if i % 2 == 0 else "meeting",
            "estimated_duration": 60,
            "priority": "high" if i < 5 else "medium"
        }
        
        memory_bank.store_task_completion(
            task=task,
            completion_time=completed_time,
            actual_duration_minutes=70  # Took 10 min longer than estimated
        )
    
    print(f"   ✅ Added {len(memory_bank.memory['task_history'])} historical tasks")
    print()
    
    # Analyze patterns
    print("🔍 Analyzing productivity patterns...")
    analysis = memory_bank.analyze_task_history()
    
    print(f"   Total tasks analyzed: {analysis['total_tasks_completed']}")
    print(f"   Categories tracked: {', '.join(analysis['categories_tracked'])}")
    
    if analysis.get('most_productive_hour'):
        print(f"   Most productive hour: {analysis['most_productive_hour']}:00")
    
    print()
    
    # Get personalized recommendations
    print("💡 Personalized Recommendations:")
    recommendations = memory_bank.get_personalized_recommendations()
    
    for rec in recommendations:
        print(f"   • {rec}")
    
    print()
    
    # Analyze duration accuracy
    print("📊 Time Estimation Analysis:")
    task_history = memory_bank.memory.get("task_history", [])
    duration_analysis = habit_analyzer.analyze_task_duration_accuracy(task_history)
    
    print(f"   Tendency: {duration_analysis['tendency']}")
    print(f"   Average ratio: {duration_analysis['average_ratio']}")
    print(f"   Recommendation: {duration_analysis['recommendation']}")
    print()
    
    print("✅ Example 3 completed!")
    print()
    print("Note: Memory persists across sessions in:")
    print(f"   {memory_bank.storage_path}")


if __name__ == "__main__":
    asyncio.run(main())