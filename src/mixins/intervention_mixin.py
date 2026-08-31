"""P1 - Commitment & Intervention Pass.

docs/PHASE_P1_COMMITMENT_INTERVENTION_SPEC.md

ONE primitive. `commit_gate` owns exactly four things and nothing else:
  1. whether / how to present the interruption,
  2. default and input semantics,
  3. one-shot / cooldown bookkeeping keyed by `key`,
  4. returning the player's commitment ("proceed" | "cancel").

Every trigger predicate and every re-arm condition lives in the CALLER,
written out at the call site (see the spec's §3). The primitive never
inspects HP / fatigue / mystery state to decide whether a situation is
dangerous - the caller already decided that before calling. That is what
keeps P1 small and the human result readable.

Interactive ios only. A bot / headless io has no `ask_commit`, so a gate
silently resolves to its default - the balance harness, the combat RNG
stream and `--mapgen v1` byte-identity are all untouched.
"""


class InterventionMixin:

    def _gate_state(self):
        gs = getattr(self, "_gate_bookkeeping", None)
        if gs is None:
            gs = self._gate_bookkeeping = {}
        return gs

    def _gate_armed(self, key, repeat):
        st = self._gate_state().get(key)
        if st is None:
            return True
        if repeat == "once":
            return False
        if isinstance(repeat, tuple) and repeat and repeat[0] == "cooldown":
            return (getattr(self, "turns", 0) - st.get("turn", -10**9)) >= repeat[1]
        return True

    def gate_rearm(self, key):
        """Callers invoke this from their OWN recovery predicate (HP back
        over 55%, weapon usable again, ...) to let a one-shot gate fire
        again."""
        self._gate_state().pop(key, None)

    def commit_gate(self, key, title, *body, default="cancel",
                    confirm_label=None, repeat="once"):
        """Present a commitment interruption.

        Returns:
          "proceed" - the player committed to the action / override
          "cancel"  - the player declined it
          "skip"    - the gate did not run (bot / headless io, or the
                      one-shot / cooldown has not re-armed). Callers MUST
                      treat "skip" as "behave exactly as if this gate did
                      not exist" - that is what keeps the bot balance
                      harness and the combat RNG stream byte-identical.

        default : "proceed" | "cancel" - what a bare Enter resolves to.
                  This is where the game's advice lives: `cancel` for the
                  one move that gets you killed, `proceed` for a
                  corrective that is almost always right.
        confirm_label : phrasing only - when set the prompt reads
                  "[Enter] {label}  ·  [n] leave it".
        repeat  : "once" | ("cooldown", n_turns)
        """
        if not self._gate_armed(key, repeat):
            return "skip"
        if not hasattr(self.io, "ask_commit"):
            return "skip"

        self.announce_event(
            title, *body,
            kind="danger" if default == "cancel" else "warning", level=2)
        choice = self.io.ask_commit(_gate_prompt(default, confirm_label), default)

        self._gate_state()[key] = {"turn": getattr(self, "turns", 0)}
        return choice


def _gate_prompt(default, confirm_label):
    if confirm_label is not None:
        return f"[Enter] {confirm_label}   ·   [n] leave it"
    if default == "cancel":
        return "[y] do it anyway   ·   [Enter] don't"
    return "[Enter] yes   ·   [n] no"
