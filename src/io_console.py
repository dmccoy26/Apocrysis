# v3 SPRINT step 6: the I/O seam. print()/input() calls are scattered
# across CombatMixin (fight/flee), PersistenceMixin (save/delete
# filename prompts), UIMixin, and ActionsMixin - not just UIMixin,
# which is why a real TUI (see
# src/tui.py) can't just swap that one mixin's rendering. Every mixin
# call site uses self.io.say()/self.io.ask()/self.io.ask_yes_no()
# instead of bare print()/input().
#
# ConsoleIO is the default - thin wrappers that behave byte-identical
# to the original bare print()/input() calls (say() forwards *args/
# **kwargs straight to print(), so a multi-arg or no-arg print() call
# site needed no special-casing to migrate). run_tests(), auto_play(),
# and the existing unittest suite all use this, unaffected by the TUI
# existing at all.


class ConsoleIO:

    # v3 SPRINT: False means ui_mixin.py's run_game_loop() prints its
    # own classic two-column ASCII block every turn, as it always has.
    # tui.py's TextualIO sets this True so that block is skipped
    # instead of flooding the TUI's log with a redundant duplicate of
    # what its own native map/stats widgets already show.
    renders_natively = False

    def say(self, *args, **kwargs):
        print(*args, **kwargs)

    def ask(self, prompt=""):
        return input(prompt)

    def ask_yes_no(self, prompt):
        while True:
            answer = input(f"{prompt} (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print("Please answer y or n.")

    def ask_combat_letter(self):
        """Encounter card (combat_mixin._encounter_card): 'f' / 'e' / 'w'.
        Accepts y/n as aliases so the old 'fight? y/n' habit still works."""
        while True:
            a = input("  [f] fight   [e] escape   [w] weapons: ").strip().lower()
            if a in ("f", "fight", "y", "yes"):
                return "f"
            if a in ("e", "escape", "flee", "n", "no"):
                return "e"
            if a in ("w", "weapon", "weapons"):
                return "w"
            print("Type f (fight), e (escape), or w (weapons).")
