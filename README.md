# dining-places-skill

An [Agent Skill](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) that turns your **Google Maps saved places** into a personal
dining knowledge base, then gives eating-out advice that:

1. **surfaces places you already saved** (⭐ Saved),
2. **infers your taste** from the saved set, and
3. **widens the search** with fresh, taste-matched suggestions (✨ New),

…then plots everything on a **map**, summarises it in a **comparison table**, and
gives a **booking link** per place.

It works at home and while travelling, with any coding agent — Claude Code,
Codex, Cursor, Gemini CLI, Kimi, GLM-based agents, pi. See [`AGENTS.md`](AGENTS.md).

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

### Method 1 — Ask your agent to install it (any shell-capable coding agent)

Paste this prompt. Works in any agent that can run `git` and read files — Claude
Code, Codex CLI, Cursor, Gemini CLI, Kimi, GLM-based agents, pi, and so on. It
does **not** work in the claude.ai chat UI, where skills are installed via
Settings. See the claude.ai steps under Method 2 below.

```text
Install the `dining-places` Agent Skill from GitHub for me:

1. Clone https://github.com/ddalgrande/dining-places-skill into your agent's
   skills folder as dining-places:
     - Claude Code: ~/.claude/skills/dining-places (or .claude/skills/dining-places
       project-scoped)
     - Codex: ~/.codex/skills/dining-places (or .agents/skills/dining-places
       project-scoped)
     - Any other agent: wherever it discovers skills; if it has no skills
       folder, clone anywhere and read AGENTS.md.
   If that folder already exists, git pull the latest rather than re-cloning.
2. Before trusting anything, open SKILL.md and every file under scripts/ and
   give me a short summary of what they do — explicitly flag anything that
   reaches the network, writes outside the skill folder, or touches my
   credentials. Then wait for my OK.
3. Verify a valid SKILL.md (with `name:` and `description:` frontmatter) sits at
   the root of the destination folder, and that the folder name matches the
   `name:` field (it should be `dining-places`).
4. Tell me to restart Claude Code and run /skills to confirm it loaded.

Do not run the skill's parser during install — it only runs later, when I ask
for dining recommendations and provide my Google Takeout export.
```

### Method 2 — Manual install

**Claude (claude.ai / desktop / mobile)**
1. Zip the `dining-places/` folder.
2. Go to **Settings → Capabilities** and upload the zip under custom Skills.
3. That's it — Claude loads it automatically when you ask about eating out.

   Requires a paid plan (Pro/Max/Team/Enterprise) with **code execution** enabled.
   Custom Skills are per-user and don't sync across surfaces.

**Claude Code**
- Clone (or copy) into `~/.claude/skills/dining-places/` (personal) or
  `.claude/skills/dining-places/` (project-scoped) — filesystem-based, no upload:

  ```bash
  git clone https://github.com/<you>/dining-places-skill ~/.claude/skills/dining-places
  ```

  The destination folder must be **`dining-places`** (matching `name:` in
  `SKILL.md`), even though the repo is `dining-places-skill`. Confirm a valid
  `SKILL.md` sits at the folder root, restart Claude Code, then run `/skills` to
  verify it loaded.
- **Audit the code before you run it.** Skills installed from GitHub are not
  security-scanned — read `SKILL.md` and `scripts/` first.

**Codex / other SKILL.md-standard agents (Cursor, Gemini CLI, …)**
- `SKILL.md` follows the open Agent Skills standard, so place the `dining-places/`
  folder wherever your agent discovers skills. Codex reads `~/.codex/skills/`
  (user) and `.agents/skills/` (per-repo, scanned from the working dir up to the
  repo root); other tools vary — check your agent's docs for its skills path.

**Agents with no skills system (Kimi, GLM-based agents, pi, generic assistants)**
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
`scripts/parse_takeout_maps.py` to build `references/saved_places.json` → matches
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

This repo ships **no personal data**. Your generated `references/saved_places.json`
and your real `references/known_ids.md` are **git-ignored** — do not commit them.
They contain your saved restaurants and (potentially) home-adjacent locations.
The `*.example` files show the shape with dummy data.

## License

[MIT](LICENSE) — see `LICENSE`. Replace the placeholder name/year before publishing.
