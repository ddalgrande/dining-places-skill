# AGENTS.md

This repo is a portable **Agent Skill**: it turns a user's exported Google Maps
saved places into a personal dining knowledge base and gives calibrated
eating-out advice. It is not an application — there is nothing to build, serve,
or deploy.

`SKILL.md` is the operational spec. Any coding agent — Claude Code, Codex, Cursor,
Gemini CLI, Kimi, GLM-based agents, or a generic assistant — can use this repo by
reading `SKILL.md` and following it. The `name:` / `description:` frontmatter in
`SKILL.md` follows the open Agent Skills standard.

## How to use it, by agent capability

- **Your agent supports skills** (Claude Code, Codex, Cursor, Gemini CLI, …):
  install the skill folder where your agent discovers skills. See `README.md`
  → *Install*. After that, nothing is invoked by hand — the agent loads
  `SKILL.md` automatically when the user asks about eating out.

- **Your agent has no skills mechanism** (Kimi CLI, many Claude Code-compatible
  clients, plain chat assistants): treat `SKILL.md` as a standing instruction
  set. When the user asks where to eat / drink, for a restaurant or bar
  recommendation, for somewhere near a location, or references their saved /
  want-to-go / starred places — open `SKILL.md` and follow its workflow.

## The one command

```bash
python3 scripts/parse_takeout_maps.py <folder> --out references/saved_places.json --dedupe
```

`<folder>` is a Takeout `.zip`, a folder of zips, or an extracted folder. The
script is Python 3.9+, standard library only — no third-party packages, no
network access. Enrichment (cuisine, rating, price, hours, map) happens at
advice-time through whatever Places/maps tool the agent has; it is not part of
this repo.

## Ground rules

- **Never commit personal data.** `references/saved_places.json` and
  `references/known_ids.md` are git-ignored. The `*.example` files show the
  shape with dummy data.
- **Don't run the parser during install.** It runs only when the user asks for a
  recommendation and has provided their Takeout export.
- **Booking is side-effecting.** Confirm place / date / party size with the user
  before submitting anything; never auto-submit.

For agent-specific install paths and the full workflow, see `README.md` and
`SKILL.md`.
