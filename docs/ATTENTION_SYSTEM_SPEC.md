# The Apocrysis Attention System (spec)

Owner-proposed 2026-08-30 from the playtest: colour is currently
decoration (blue = map goal, red = hungry) and a zombie encounter — one
of the most consequential moments on the map — renders as ordinary
white story text. Colour should become the game's **attention
language**: consistent, semantic, and reserved.

> **This is a presentation-layer change. It touches NO balance** —
> combat, escape odds, encounter rate, loot, hunger/thirst rates,
> map generation are all untouched. It changes only how events are
> *labelled and rendered*.

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

## Implementation shape

1. `constants.py` — add `ORANGE = "\033[38;5;208m"` (256-colour;
   falls back to yellow-ish on a 16-colour terminal, acceptable).
2. `ui_mixin.announce_event` — remap the `kind` table to the seven
   classes. Keep the old kind strings as **aliases** (`lead`/`discovery`
   → DISCOVERY, `objective` → OBJECTIVE, `solved` → SUCCESS,
   `milestone`/`correction` → STORY, `warn` → WARNING) so no call site
   changes in the same commit; then a follow-up sweeps call sites to the
   new names and splits the few `warn`→`danger` cases.
3. `combat_mixin._encounter_card` — route the card through
   `announce_event(kind="danger")` (or a dedicated `_danger_banner`).
   `Successfully fled` etc. get their classes.
4. HUD (`tui._status_block` / `_investigation_strip`, classic
   `_status_block`) — colour resource readouts by the §ladder bands.
5. `TextualIO` — Textual markup already supports colour; map the ANSI
   classes to Rich styles once, centrally.
6. A `test_attention.py` — every `announce_event` kind renders a
   non-empty glyph + a colour; the seven classes are distinct; `warn`
   alias still red-family; combat encounter emits a DANGER-classed line.

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

The attention system is presentation-only, so it *could* land during
the playtest without confounding the balance evidence — but it changes
what the player sees on every turn, so a mid-playtest switch muddies
"did the player act on the objective?" (was it the blue, or the run?).
**Recommended: build it right after the current blind playtest, as the
first piece of the visual-language work** — the playtest's navigation
finding ("the heading is shown and ignored") is a direct input to how
prominent OBJECTIVE-blue needs to be.

---

*Presentation layer. No balance touched. Extends the existing
`announce_event(kind=…)` seam into a consistent seven-class attention
language with reserved red, glyph+colour redundancy, and a
persistent/transient split.*
