"""
Utility functions used across the application.
Provides common operations like date parsing, ID generation, etc.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import re

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{unique_id}" if prefix else unique_id

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse various date formats into datetime object.
    Handles formats like: "tomorrow", "in 3 days", "2025-11-20"
    """
    date_str = date_str.lower().strip()
    
    # Handle relative dates
    if date_str == "today":
        return datetime.now()
    elif date_str == "tomorrow":
        return datetime.now() + timedelta(days=1)
    elif "in" in date_str and "day" in date_str:
        # Extract number from "in 3 days"
        match = re.search(r'(\d+)', date_str)
        if match:
            days = int(match.group(1))
            return datetime.now() + timedelta(days=days)
    
    # Try parsing absolute date formats
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def calculate_priority_score(
    urgency: int,  # 1-5 scale
    importance: int,  # 1-5 scale
    effort: int,  # 1-5 scale (lower is better)
    deadline_days: Optional[int] = None
) -> float:
    """
    Calculate priority score based on multiple factors.
    Higher score = higher priority
    """
    # Base score from urgency and importance
    base_score = (urgency * 0.4) + (importance * 0.4)
    
    # Effort penalty (easier tasks get slight boost)
    effort_factor = (6 - effort) * 0.1  # Inverted so low effort = bonus
    
    # Deadline urgency boost
    deadline_factor = 0
    if deadline_days is not None:
        if deadline_days <= 1:
            deadline_factor = 0.5  # Critical
        elif deadline_days <= 3:
            deadline_factor = 0.3  # Urgent
        elif deadline_days <= 7:
            deadline_factor = 0.1  # Soon
    
    total_score = base_score + effort_factor + deadline_factor
    return round(total_score, 2)

def format_duration(minutes: int) -> str:
    """Convert minutes to human-readable duration"""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining_mins = minutes % 60
    if remaining_mins == 0:
        return f"{hours}h"
    return f"{hours}h {remaining_mins}m"

def load_json(filepath: str) -> Dict[str, Any]:
    """Safely load JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_json(data: Dict[str, Any], filepath: str) -> bool:
    """Safely save JSON file"""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving JSON: {e}")
        return False

def extract_action_items(text: str) -> List[str]:
    """Extract action items from text (lines starting with -, *, or •)"""
    lines = text.split('\n')
    actions = []
    for line in lines:
        line = line.strip()
        if line.startswith(('-', '*', '•', '□', '☐')):
            # Remove the bullet point
            action = re.sub(r'^[-*•□☐]\s*', '', line)
            if action:
                actions.append(action)
    return actions