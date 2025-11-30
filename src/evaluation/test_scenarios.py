"""
Test scenarios for agent evaluation.
Provides standardized test cases for validating agent behavior.
"""

from typing import List, Dict, Any

# Test scenario 1: Simple daily tasks
TEST_SCENARIO_SIMPLE = {
    "name": "Simple Daily Tasks",
    "tasks": [
        {
            "id": "task_1",
            "name": "Morning standup meeting",
            "category": "meeting",
            "priority": "high",
            "estimated_duration": 30,
            "deadline": "today"
        },
        {
            "id": "task_2",
            "name": "Review pull requests",
            "category": "review",
            "priority": "high",
            "estimated_duration": 60,
            "deadline": "today"
        },
        {
            "id": "task_3",
            "name": "Write documentation",
            "category": "writing",
            "priority": "medium",
            "estimated_duration": 90,
            "deadline": "in 2 days"
        }
    ],
    "expected_order": ["task_1", "task_2", "task_3"]
}

# Test scenario 2: Overloaded day
TEST_SCENARIO_OVERLOAD = {
    "name": "Overloaded Schedule",
    "tasks": [
        {"id": f"task_{i}", "name": f"Task {i}", "priority": "high", "estimated_duration": 120}
        for i in range(1, 8)
    ],
    "expected_outcome": "Should recommend splitting across days"
}

# Test scenario 3: Mixed priorities
TEST_SCENARIO_MIXED = {
    "name": "Mixed Priority Tasks",
    "tasks": [
        {"id": "task_1", "name": "Urgent bug fix", "priority": "high", "estimated_duration": 45},
        {"id": "task_2", "name": "Team lunch", "priority": "low", "estimated_duration": 60},
        {"id": "task_3", "name": "Client presentation prep", "priority": "high", "estimated_duration": 120},
        {"id": "task_4", "name": "Read industry news", "priority": "low", "estimated_duration": 30},
    ],
    "expected_order": ["task_1", "task_3", "task_2", "task_4"]
}

def get_test_scenarios() -> List[Dict[str, Any]]:
    """Get all test scenarios"""
    return [
        TEST_SCENARIO_SIMPLE,
        TEST_SCENARIO_OVERLOAD,
        TEST_SCENARIO_MIXED
    ]