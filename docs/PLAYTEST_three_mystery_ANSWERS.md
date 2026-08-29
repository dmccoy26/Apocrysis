# Three-mystery blind comprehension test — answer sheet

Phase gate `69d78812` / `9ae794b9`. Fill one block per run. Play blind —
don't read the facilitator key until all three are done.

## How to run

```
python3 tools/playtest_three.py shuffle     # blind — don't peek at the code
```

Do this **three times**. `shuffle` picks one of A/B/C at random without
telling you which. (If a family repeats, just run it again — or force
the missing one with `python3 tools/playtest_three.py A|B|C` and have
someone else tell you nothing.) `--log` is on; transcripts land via the
in-game `log` toggle path.

Answer from what the game showed you — **do not reread the scrollback**.
If you had to scroll back to answer, that question fails.

---

## Run 1

| Question | Answer | Pass? |
|---|---|---|
| What am I trying to accomplish? | | |
| What is my current lead? | | |
| Where should I go? | | |
| What am I trying to understand? | | |
| What should I do next? (`▸` line) | | |
| When something changed, did I notice? (a banner interrupted) | | |
| After a wrong action, did I understand the consequence? | | |

**Gold question — what did you think the game wanted you to figure out?**

>

Turns played: ___   Outcome: ___

---

## Run 2

| Question | Answer | Pass? |
|---|---|---|
| What am I trying to accomplish? | | |
| What is my current lead? | | |
| Where should I go? | | |
| What am I trying to understand? | | |
| What should I do next? (`▸` line) | | |
| When something changed, did I notice? (a banner interrupted) | | |
| After a wrong action, did I understand the consequence? | | |

**Gold question — what did you think the game wanted you to figure out?**

>

Turns played: ___   Outcome: ___

---

## Run 3

| Question | Answer | Pass? |
|---|---|---|
| What am I trying to accomplish? | | |
| What is my current lead? | | |
| Where should I go? | | |
| What am I trying to understand? | | |
| What should I do next? (`▸` line) | | |
| When something changed, did I notice? (a banner interrupted) | | |
| After a wrong action, did I understand the consequence? | | |

**Gold question — what did you think the game wanted you to figure out?**

>

Turns played: ___   Outcome: ___

---

## Verdict

The test **passes** if the three gold answers describe three different
*kinds of problem*, e.g.:

- "find / locate something" (spatial)
- "figure out what powers / what the dependency is" (infrastructural)
- "figure out which control actually matters" (experimental)

If two runs blur together, or you were confused about *what kind of
problem you were in*, the banners or the `▸` objective phrasing need
work before Tier-2 families get built. Note which run and which
question below.

Notes:

>

---

## Facilitator key — DO NOT READ UNTIL DONE

<details>
<summary>slot → mechanism → family</summary>

- **A** = `mountain_pass` — spatial — "where is the route?"
- **B** = `power_station` — infrastructural — "gate ← hydro station ← fuel; apply the fuel at the generator, not the gate"
- **C** = `dam_valves` — experimental — "which of the dam controls is it? the obvious one (the main sluice) is never right"

</details>
