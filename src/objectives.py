# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

from dataclasses import dataclass


@dataclass
class Goal:
    title: str
    description: str = ""
    completed: bool = False
    reward_type: str = "health"
    reward_amount: int = 5
    goal_type: str = ""

@dataclass
class Task:
    title: str
    description: str = ""
    completed: bool = False
    reward_type: str = "xp"
    reward_amount: int = 10
    task_type: str = ""

