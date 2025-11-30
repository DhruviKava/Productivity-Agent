"""
Example 2: Project planning with multiple tasks over several days.
Demonstrates context engineering with large task lists.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.orchestrator import create_orchestrator


async def main():
    """Run example 2: Project planning"""
    
    print("=" * 60)
    print("EXAMPLE 2: Project Planning")
    print("=" * 60)
    print()
    
    # Create a large project with many tasks
    project_tasks = {
        "tasks": [
            {
                "name": f"Project Task {i}",
                "category": "coding" if i % 3 == 0 else "planning",
                "priority": "high" if i <= 5 else "medium",
                "estimated_duration": 60 + (i * 10),
                "deadline": "in 7 days"
            }
            for i in range(1, 21)  # 20 tasks
        ]
    }
    
    print(f"📦 Project with {len(project_tasks['tasks'])} tasks")
    print()
    
    # Process with orchestrator
    orchestrator = create_orchestrator()
    
    print("⚙️  Processing large project...")
    print("   (Context engineering will be applied automatically)")
    print()
    
    result = await orchestrator.process_tasks(
        raw_tasks=project_tasks,
        session_id="example_2_project"
    )
    
    # Check if context engineering was applied
    planned = result['outputs']['planned']
    
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print()
    
    print(f"📊 Context Engineering Applied: {planned['context_engineering_applied']}")
    
    if planned['context_engineering_applied']:
        print(f"   Tasks scheduled: {planned['task_count']}")
        print(f"   Old tasks summarized: {planned['old_tasks_summary']['count']}")
    
    print()
    print(f"⏱️  Total work time: {planned['total_work_hours']}h")
    print(f"⭐ Quality score: {result['outputs']['evaluation']['total_score']}/100")
    print()
    
    print("✅ Example 2 completed!")


if __name__ == "__main__":
    asyncio.run(main())