# The Apocrysis Attention System (spec)

Owner-proposed 2026-08-30 from the playtest. **The core problem, in the
owner's words:** *"the game currently presents radically different
levels of importance using the same visual language."* A movement line
and an Elite Heavy encounter are both white prose, when mechanically
one is "continue" and the other is "STOP, make a decision, your life
depends on it."

> **This is a presentation-layer change. It touches NO balance** —
> combat, escape odds, encounter rate, loot, hunger/thirst rates,
> map generation are all untouched. It changes only how events are
> *labelled and rendered*.

## Scope — the event stream is the point; the HUD is a bonus

The owner's actual ask is **the ongoing story / event feed**: every
line that scrolls past should tell the player, at a glance, whether
it's ordinary narration, an objective, a warning, a discovery, a story
beat, a success, or a life-threatening event — *before* they parse the
words.

| | | |
|---|---|---|
| **Attention System** | the semantic vocabulary (below) | |
| **Event stream** | **primary application** — build this first | zombie = red, low food/water = orange, objective = blue |
| **HUD escalation** | secondary application of the same vocabulary | resource numbers shade white → orange → red |

Keep both in this doc, but implement the event stream first. The HUD
change is useful and consistent but it is not what was asked for.

## Semantic channels, NOT seven alarm levels

The classes are **channels** (what kind of thing is this?), not a
loudness ladder. Visual prominence is deliberately uneven:

```
  ‼ DANGER      LOUD        - interrupts, own banner, red
  ⚠ WARNING     NOTICEABLE  - orange, a clear line, not a banner
  ◆ OBJECTIVE   PERSISTENT  - blue, and directionally prominent
                             (the navigation finding: the heading is
                              shown and ignored - blue must carry weight)
  ✦ DISCOVERY   ACCENT      - yellow, a coloured word, quiet
  ◈ STORY       ACCENT      - purple, a coloured word, quiet
  ✓ SUCCESS     BRIEF       - green, momentary positive feedback
    NARRATIVE   PLAIN       - white, the default
```

A purple STORY line must **not** scream just because it's purple. Only
DANGER interrupts; WARNING is a clear line; OBJECTIVE is persistent;
the rest are accents on otherwise-normal text. The terminal must not
become Skittles.

## The deterioration ladder — the clearest first demo

White → orange → red is one intuitive progression the player learns
immediately:

```
  Food: 43        white     nothing special
  Food: 22        orange    becoming a problem
  Food: 8         orange    still a problem
  ‼ STARVING      red       a problem RIGHT NOW
```

Same shape for a zombie: `‼ ZOMBIE ENCOUNTER` on sight is the loudest
thing the exploration feed ever does — which is correct, because it's
the most consequential.

## What already exists (build on this, don't replace it)

`ui_mixin.announce_event(title, *body, kind=…)` **already** implements
"the renderer owns the colour/glyph per semantic kind" — 9 kinds today
(`warn / solved / lore / milestone / correction / lead / discovery /
objective / info`). The gaps this spec closes:

1. **Combat doesn't use it.** `encounter_zombie` / `_encounter_card`
   emit plain `io.say`. The single most important state transition on
   the map has no visual voice.
2. **`warn` is overloaded.** It's red, and it carries *both* "you're
   starving now" (a DANGER) and "getting hungry" (a WARNING). Those are
   different urgencies and need different colours.
3. **No glyph vocabulary.** The glyphs (`[!]`, `◆`, `●`, `✗`) grew
   ad hoc; a reader who can't tell the colours apart gets no hierarchy.
4. **Ordinary narration is unclassed** — every `io.say` is white, so
   an OBJECTIVE line and a "you move through forest" line compete
   equally.
5. **The HUD doesn't escalate.** Resource numbers are one colour until
   a banner fires; they should shade orange → red as they fall.

## The seven classes

| class | colour | glyph | means | examples |
|---|---|---|---|---|
| **OBJECTIVE** | blue (`BLUE`) | `◆` | *where to go / what's next* | evacuation route heading, the active lead, the destination, "▸ head for the way out" |
| **DANGER** | red (`RED`) | `‼` | *deal with this NOW* | zombie encounter, critical HP, escape failed, starvation attrition, death, causeway flooding |
| **WARNING** | orange (`ORANGE` = `\033[38;5;208m`) | `⚠` | *something is getting worse* | low food / water, high fatigue, weapon worn, tide turning |
| **DISCOVERY** | yellow (`YELLOW`) | `✦` | *worth investigating / an opportunity* | a clue found, a named site reached, a rare weapon, a new lead surfaced |
| **STORY** | purple (`MAGENTA`) | `◈` | *the narrative just changed* | a milestone fact, a hypothesis-ladder correction, the radio voice, the ending beats |
| **SUCCESS** | green (`GREEN`) | `✓` | *that went well* | enemy defeated, obstacle opened, mystery solved, successful escape, healed, expedition won |
| **NARRATIVE** | default | — | *ordinary world* | movement, terrain description, routine actions |

### The one hard rule — reserve red

> **RED = "pay attention right now."** If everything is red, nothing
> is. Ordinary hunger / thirst / fatigue / a chipped blade are
> **WARNING (orange)**. Red is only: a live threat, lethal state, a
> failed escape, death.

### Colour + glyph, never colour alone

Every class carries its glyph *and* its label, so the hierarchy reads
in a mono terminal, a colour-blind eye, or a screenshot:

```
◆  OBJECTIVE — the evacuation corridor lies south-east.
‼  ZOMBIE — Elite Heavy. EXTREME. Fight ~0%.
⚠  LOW WATER — 6 left.
✦  NEW CLUE — a calendar with one date circled.
◈  A PIECE FALLS INTO PLACE — they didn't all die. They left.
✓  You got clear of the Regular Zombie.
```

## Persistent state vs transient events

Two different surfaces, so the screen never becomes a rainbow:

| | where | rendering |
|---|---|---|
| **persistent** (things that stay true) | HUD / panels | the resource number / bar takes the class colour: `Food 6` orange, `HP 14/100` red, the objective strip blue |
| **transient** (things that just happened) | the event stream | one `announce_event` flare, class-coloured, then it recedes to white history |

The HUD escalation ladder (persistent):

| resource | normal | WARNING (orange) | DANGER (red) |
|---|---|---|---|
| hunger / thirst | ≥ 40 | 15–39 | < 15 (attrition imminent / active) |
| HP | > 40 % | 20–40 % | < 20 % |
| fatigue | ≤ 50 | 51–85 | > 85 |
| equipped weapon | > 25 % dur | 10–25 % | ≤ 10 % / empty |

One transient DANGER line fires **once** on crossing into the red band
(`⚠ YOUR WOUNDS ARE DANGEROUS`), not every turn — the escalating
hunger/thirst warnings already do this (`_hunger_thirst_warn`
re-arms > 45); extend the pattern.

## Combat gets its own voice

`_encounter_card` becomes a **DANGER** banner. The card content is
unchanged (it's from `COMBAT_INFO_SPEC.md` — threat, fight %, escape %,
weapon verdict); it's just wrapped so the exploration → danger
transition is unmistakable:

```
‼ ══════════════════════════════════════════
‼  ZOMBIE — Elite Heavy Zombie
‼  EXTREME THREAT
‼
‼  Fight  ~0%      Escape  ~50%
‼  Your Steel Katana is poorly suited.
‼  If the escape fails, you're fighting it anyway.
‼ ══════════════════════════════════════════
   [f] fight   [e] escape   [w] weapons
```

`Successfully fled` → **SUCCESS**. `Failed to flee` / `critically
wounded` → **DANGER**. `defeated!` → **SUCCESS**.

## Implementation shape — event stream first

**Phase 1 — the event feed (the actual ask):**

1. `constants.py` — add `ORANGE = "\033[38;5;208m"` (256-colour; falls
   back acceptably on a 16-colour terminal).
2. `ui_mixin.announce_event` — remap the `kind` table to the seven
   classes. Keep the old kind strings as **aliases** (`lead`/`discovery`
   → DISCOVERY, `objective` → OBJECTIVE, `solved` → SUCCESS,
   `milestone`/`correction` → STORY, `warn` → WARNING) so **no call
   site changes in this commit**. Prominence per the "semantic
   channels" section — only DANGER gets the full `═══` banner; WARNING
   / SUCCESS / DISCOVERY / STORY are a single coloured, glyph-prefixed
   line.
3. `combat_mixin._encounter_card` — the encounter fires a **DANGER**
   flare (`‼ ZOMBIE ENCOUNTER — <name>`) on sight, then the info card.
   `Successfully fled` → SUCCESS; `Failed to flee` / `critically
   wounded` → DANGER; `defeated!` → SUCCESS.
4. Split the overloaded `warn` at its ~4 call sites: "getting hungry /
   thirsty / tired / weapon worn" stay WARNING (orange); "starving now
   / 0 hunger attrition / causeway flooded" become DANGER (red).
5. Ordinary movement / terrain `io.say` stays NARRATIVE (no change).
6. `TextualIO` — map the ANSI classes to Rich styles once, centrally.
7. `test_attention.py` — every class renders a distinct non-empty
   glyph + colour; `warn` alias still resolves; a zombie encounter
   emits a DANGER-classed line; a movement line stays plain.

**Phase 2 — the HUD escalation (secondary):** colour the resource
readouts in `tui._status_block` / classic `_status_block` by the
deterioration-ladder bands; one transient DANGER line on crossing into
red, re-armed on recovery (the `_hunger_thirst_warn` pattern).

Phase 2 can wait, or be skipped, without blocking Phase 1.

## What this is NOT

- Not a balance change (see the header).
- **Not** the escape-informed-by-threat combat-model change. The
  playtest exposed that an independent flat 50 % flee roll contradicts
  a "Fight ~0%" card — *"the game told me not to fight, I listened, I
  died anyway."* Making `escape %` a function of the threat assessment
  (a nightmare enemy you can't beat should usually be one you *can*
  flee) is a real combat-model change and belongs in its own
  hypothesis, **after** the blind playtest, alongside the
  dangerous-enemy-reward experiment. Track it; don't build it here.
- Not a Pyglet / graphical change. This is the terminal attention
  language; the eventual renderer inherits the same seven classes.

## Sequencing

Presentation-only, so it *could* land during the playtest without
confounding the balance evidence — but it changes what the player sees
every turn, which muddies "did the player act on the objective — was it
the blue, or the run?". **Recommended: Phase 1 right after the current
blind playtest, as the first piece of the visual-language work.** The
navigation finding ("the heading is shown and ignored") is a direct
input to exactly how prominent OBJECTIVE-blue needs to be — the
playtest is calibrating that.

Phase 2 (HUD) is optional and can follow whenever.

---

*Presentation layer. No balance touched. Extends the existing
`announce_event(kind=…)` seam into a consistent seven-class attention
language with reserved red, glyph+colour redundancy, and a
persistent/transient split.*
