# dining-places-skill

[![skills.sh](https://skills.sh/b/ddalgrande/dining-places-skill)](https://skills.sh/ddalgrande/dining-places-skill)

An [Agent Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) that turns your **Google Maps saved places** into a personal
dining knowledge base, then gives eating-out advice that:

1. **surfaces places you already saved** (⭐ Saved),
2. **infers your taste** from the saved set, and
3. **widens the search** with fresh, taste-matched suggestions (✨ New),

…then plots everything on a **map**, summarises it in a **comparison table**, and
gives a **booking link** per place.

It works at home and while travelling, with any coding agent — Claude Code,
Codex, Cursor, Gemini CLI, Kimi, GLM-based agents, or pi. See
[`AGENTS.md`](AGENTS.md).

## Why Takeout?

Google has no API for personal saved places. The only export route is
[Google Takeout](https://takeout.google.com/). An export contains **two**
different structures:

| Source | What it is |
|---|---|
| `Maps (your places)/Saved Places.json` | Individually saved / starred places |
| `Saved/<List>.csv` (one per List) | Lists — Favourites, Want to go, To visit, custom |

Both are parsed and merged. Note the consequence: a *location* search only works
on rows that have coordinates, so List-only places must be enriched (via a Places
lookup) before they can be filtered by neighbourhood. See `SKILL.md`.

## Prepare your data (do this first)

A Takeout export can take a while to generate, so kick it off before you install
the skill.

1. In [Takeout](https://takeout.google.com/), **deselect everything, then tick
   both `Maps (your places)` *and* `Saved`** — you need both: `Maps (your places)`
   holds your starred places (with coordinates), `Saved` holds your Lists (*Want
   to go*, *To visit*, *Favourites*, custom). Miss one and you lose either the
   coordinates or the Lists. Set delivery to **Add to Drive** (optionally schedule
   a recurring export every ~2 months).
2. **Enable the Google Drive connector** in your agent so it can read the export
   from `My Drive/Takeout` — **or** plan to upload the zip directly in chat.

## Install

### Method 1 — skills.sh CLI (recommended)

The skill is published for the [skills.sh](https://skills.sh) open agent skills
ecosystem, so one command installs it into Claude Code, Codex, Cursor, Gemini
CLI, OpenCode, Kimi Code CLI, pi and [many more agents](https://skills.sh). Needs
Node.js 22.20+.

```bash
# Preview what will be installed (installs nothing)
npx skills add ddalgrande/dining-places-skill --list

# Install for every project (recommended — it's a personal skill)
npx skills add ddalgrande/dining-places-skill -g

# …or only for the current project, for specific agents, non-interactively
npx skills add ddalgrande/dining-places-skill -a claude-code -a codex -y
```

The CLI detects your agents and installs the skill as **`dining-places`**
(from `name:` in `SKILL.md`) into each agent's skills folder, e.g.:

| Agent | Project (default) | Global (`-g`) |
|---|---|---|
| Claude Code | `.claude/skills/dining-places/` | `~/.claude/skills/dining-places/` |
| Codex, Kimi Code CLI, pi | `.agents/skills/dining-places/` | `~/.agents/skills/dining-places/` |
| Cursor | `.agents/skills/dining-places/` | `~/.cursor/skills/dining-places/` |
| Gemini CLI | `.agents/skills/dining-places/` | `~/.gemini/skills/dining-places/` |
| OpenCode | `.agents/skills/dining-places/` | `~/.config/opencode/skills/dining-places/` |

Keep it current or remove it later (drop `-g` if you installed per project):

```bash
npx skills check                    # any updates available?
npx skills update dining-places -g  # pull the latest — back up your data first (below)
npx skills remove dining-places -g
```

> **Your data survives updates.** `skills update` replaces the installed
> `dining-places/` folder, so the skill keeps your knowledge base outside it, in
> `~/.dining-places/` (override with `DINING_PLACES_HOME`). If an older install
> left `saved_places.json` or `known_ids.md` under the skill's `references/`
> folder, the agent copies them to `~/.dining-places/` on first use. Run the
> update after that has happened.

Then restart your agent (in Claude Code, run `/skills` to confirm it loaded).

> **Audit before you trust it.** skills.sh is a directory, not a security review.
> Read `SKILL.md` and `scripts/` first (the `--list` preview above, or on GitHub).
> The parser is standard-library Python with no network access.
>
> The CLI sends anonymous usage telemetry; set `DISABLE_TELEMETRY=1` to opt out.

### Method 2 — Ask your agent to install it (no Node.js)

Paste this prompt into any agent that can run `git` and read files. It does
**not** work in the claude.ai chat UI, where skills are installed via Settings
(see Method 3).

```text
Install the `dining-places` Agent Skill from GitHub for me:

1. If Node.js 22.20+ is available, run:
     npx skills add ddalgrande/dining-places-skill -g
   Otherwise clone https://github.com/ddalgrande/dining-places-skill into your
   agent's skills folder as dining-places:
     - Claude Code: ~/.claude/skills/dining-places (or .claude/skills/dining-places
       project-scoped)
     - Codex: ~/.agents/skills/dining-places (or .agents/skills/dining-places
       project-scoped)
     - Any other agent: wherever it discovers skills; if it has no skills
       folder, clone anywhere and read AGENTS.md.
   If that folder already exists, update it (npx skills update dining-places,
   or git pull) rather than reinstalling.
2. Before trusting anything, open SKILL.md and every file under scripts/ and
   give me a short summary of what they do — explicitly flag anything that
   reaches the network, writes outside the skill folder, or touches my
   credentials. Then wait for my OK.
3. Verify a valid SKILL.md (with `name:` and `description:` frontmatter) sits at
   the root of the destination folder, and that the folder name matches the
   `name:` field (it should be `dining-places`).
4. Tell me to restart my agent (in Claude Code, run /skills) to confirm it loaded.

Do not run the skill's parser during install — it only runs later, when I ask
for dining recommendations and provide my Google Takeout export.
```

### Method 3 — Manual install

**Claude (claude.ai / desktop / mobile)**
1. Zip the `dining-places/` folder.
2. Go to **Settings → Capabilities** and upload the zip under custom Skills.
3. That's it — Claude loads it automatically when you ask about eating out.

   Requires a paid plan (Pro/Max/Team/Enterprise) with **code execution** enabled.
   Custom Skills are per-user and don't sync across surfaces.

**Claude Code / Codex / other SKILL.md-standard agents (git clone)**

```bash
git clone https://github.com/ddalgrande/dining-places-skill ~/.claude/skills/dining-places
```

The destination folder must be **`dining-places`** (matching `name:` in
`SKILL.md`), even though the repo is `dining-places-skill`. Use the paths in the
table above for other agents, or check your agent's docs for its skills path.

**Agents with no skills system (generic assistants, GLM-based agents, …)**
- Clone the repo anywhere the agent can read it and point the agent at
  **`AGENTS.md`** (mirrored as `CLAUDE.md`). It tells the agent to treat
  `SKILL.md` as a standing instruction set and follow that workflow whenever you
  ask where to eat or drink. Nothing else to configure.

## Use it (nothing to run by hand)

With your export in Drive (or to hand) and the skill installed, just ask
naturally — e.g. *"where should I eat near the Heath tonight, from my saved
places?"* or *"somewhere for drinks around here."* The agent does the parsing
and enrichment.

Behind the scenes the agent then: reads the export → runs
`scripts/parse_takeout_maps.py` to build `~/.dining-places/saved_places.json` → matches
your saved places to the area → enriches + widens → replies with a **map**, a
**comparison table**, and a **booking link** per place.

## How your saved places get used (the clever bit)

Takeout gives your **starred** places coordinates, but your **List** places
(*Want to go*, *To visit*, *Favourites*, custom lists) have none, so a naive
location search silently skips them. `SKILL.md` Step 3 fixes that without any API
key:

> **pre-filter** List places by relevance → **resolve** a small set via the Places
> tool, biased to the target area → **keep** the in-area hits → **cache** the
> resolved coordinates back into the snapshot.

Each place is looked up at most once, so the snapshot self-completes and the skill
gets **cheaper every time you use it**.

## Requirements

- An agent with **code execution** (to run the parser) and a **Places/maps tool**
  (to enrich cuisine / rating / price / hours — none of which are in Takeout — and
  to plot the map).
- Python 3.9+ in that sandbox — standard library only, no third-party deps.

## Privacy

This repo ships **no personal data**. Your generated `saved_places.json` and
`known_ids.md` live in `~/.dining-places/`, outside the repo and the installed
skill folder. Don't copy them into the repo; the legacy `references/` paths stay
git-ignored as a safety net.
They contain your saved restaurants and (potentially) home-adjacent locations.
The `*.example` files show the shape with dummy data.

## License

[MIT](LICENSE) — see `LICENSE`. Replace the placeholder name/year before publishing.
