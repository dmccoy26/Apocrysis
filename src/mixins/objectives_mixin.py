# Auto-extracted from the original monolithic apocrysis.py during
# the src/ restructuring - see README.md for the project layout.

from src.objectives import Goal, Task


class ObjectivesMixin:

    def _auto_check_goals(self):
        """Automatically mark goals as completed when they are achieved based on the last action."""
        self._check_and_complete_goals(self.last_action)

    def add_goal(self, title, description="", goal_type=""):
        self.goals.append(Goal(title=title, description=description, goal_type=goal_type))
        self.io.say(f"New goal added: {title}")

    def list_goals(self):
        if not self.goals:
            self.io.say("No active goals.")
            return
        self.io.say("\n--- Active Goals ---")
        for i, g in enumerate(self.goals):
            status = "[DONE]" if g.completed else "[ACTIVE]"
            reward_desc = f"Reward: +{g.reward_amount} {g.reward_type}"
            type_desc = f"Type: {g.goal_type or 'General'}"
            self.io.say(f"{i+1}. {status} {g.title} - {g.description or 'No description'} ({reward_desc}, {type_desc})")

    def _prompt_complete_goal(self):
        try:
            index = int(self.io.ask("Goal index (1-based): ")) - 1
        except ValueError:
            self.io.say("Please enter a valid number.")
            return
        self.complete_goal(index)

    def _prompt_complete_task(self):
        try:
            index = int(self.io.ask("Task index (1-based): ")) - 1
        except ValueError:
            self.io.say("Please enter a valid number.")
            return
        self.complete_task(index)

    def complete_goal(self, index):
        if 0 <= index < len(self.goals) and not self.goals[index].completed:
            goal = self.goals[index]
            goal.completed = True
            self.io.say(f"Goal completed: {goal.title}!")
            
            # Apply reward
            if goal.reward_type == "xp":
                self.award_xp(goal.reward_amount)
            elif goal.reward_type == "health":
                self.health = min(100, self.health + goal.reward_amount)
            elif goal.reward_type == "fatigue":
                self.fatigue = max(0, self.fatigue - goal.reward_amount)
            elif goal.reward_type == "food":
                self.backpack.food += goal.reward_amount
            elif goal.reward_type == "water":
                self.backpack.water += goal.reward_amount
            elif goal.reward_type == "medicine":
                self.backpack.medicine += goal.reward_amount
                
            self.io.say(f"Reward applied: +{goal.reward_amount} {goal.reward_type}")
        else:
            self.io.say("Invalid goal index or already completed.")

    def _check_and_complete_goals(self, action_type):
        for i, g in enumerate(self.goals):
            if g.completed or not getattr(g, 'goal_type', None): continue
            
            if g.goal_type == action_type:
                self.complete_goal(i)

    # --- Task System Methods ---
    def add_task(self, title, description="", task_type="", reward_type="xp", reward_amount=10):
        self.tasks.append(Task(title=title, description=description, task_type=task_type, reward_type=reward_type, reward_amount=reward_amount))
        self.io.say(f"New task added: {title}")

    def list_tasks(self):
        if not self.tasks:
            self.io.say("No active tasks.")
            return
        self.io.say("\n--- Active Tasks ---")
        for i, t in enumerate(self.tasks):
            status = "[DONE]" if t.completed else "[ACTIVE]"
            reward_desc = f"Reward: +{t.reward_amount} {t.reward_type}"
            type_desc = f"Type: {t.task_type or 'General'}"
            self.io.say(f"{i+1}. {status} {t.title} - {t.description or 'No description'} ({reward_desc}, {type_desc})")

    def complete_task(self, index):
        if 0 <= index < len(self.tasks) and not self.tasks[index].completed:
            task = self.tasks[index]
            task.completed = True
            self.io.say(f"Task completed: {task.title}!")
            
            # Apply reward
            if task.reward_type == "xp":
                self.award_xp(task.reward_amount)
            elif task.reward_type == "health":
                self.health = min(100, self.health + task.reward_amount)
            elif task.reward_type == "fatigue":
                self.fatigue = max(0, self.fatigue - task.reward_amount)
            elif task.reward_type == "food":
                self.backpack.food += task.reward_amount
            elif task.reward_type == "water":
                self.backpack.water += task.reward_amount
            elif task.reward_type == "medicine":
                self.backpack.medicine += task.reward_amount
                
            self.io.say(f"Reward applied: +{task.reward_amount} {task.reward_type}")
        else:
            self.io.say("Invalid task index or already completed.")

    def _generate_dynamic_tasks(self):
        """Creates new tasks dynamically based on game state and player progression."""
        active_task_types = [t.task_type for t in self.tasks if not t.completed]
        
        # Exploration Milestone
        if "explore" not in active_task_types:
            unvisited_count = sum(1 for y in range(self.map_size) for x in range(self.map_size) if (x, y) not in self.visited)
            target = min(unvisited_count, 5)
            if target > 0:
                self.add_task("Scout the Wastes", f"Explore {target} uncharted tiles.", task_type="explore", reward_amount=25)

        # Combat Milestone
        if "combat" not in active_task_types and self.day >= 3:
            self.add_task("Hunt the Infected", "Defeat 3 zombies to clear your sector.", task_type="combat", reward_amount=30, reward_type="xp")

        # Survival Milestone
        if "survival" not in active_task_types and (self.backpack.food == 0 or self.backpack.water == 0):
            self.add_task("Forage for Supplies", "Find food or water to sustain yourself.", task_type="survival", reward_amount=15)