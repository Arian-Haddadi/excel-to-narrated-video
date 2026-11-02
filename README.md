# excel-to-narrated-video

Agent skill for a human-run team workflow: **financial Excel → Persian PowerPoint (Grok) → narration script (Grok) → voiceover (ElevenLabs) → narrated video (PowerPoint export)**, for example an AGM video (فیلم مجمع).

Built for AGMs of companies listed on the Tehran Stock Exchange / Iran Fara Bourse. When invoked, the agent guides the user step by step, asks for company info (name, symbol, logo, agenda from the Codal invitation), and applies listed-company AGM content rules. People do each stage in the tool's own UI and approve it. The agent sets up the project folder, checks every number on the slides and in the script against the Excel, prepares TTS-ready text, and computes slide timings. A project can be handed off between team members.

## Install

**Any agent (Claude Code, Codex, Cursor, Gemini CLI, …)** with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add Arian-Haddadi/excel-to-narrated-video
```

**Manual:** copy this repository as a folder named `excel-to-narrated-video` into the agent's skills folder:

| Agent | Folder |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| Others (Agent Skills standard) | `~/.agents/skills/` or `.agents/skills/` in a project |

```bash
git clone https://github.com/Arian-Haddadi/excel-to-narrated-video ~/.claude/skills/excel-to-narrated-video
```

Requirements: Python 3.10+ with `openpyxl`, and `ffmpeg`/`ffprobe` for audio and video checks. PowerPoint is needed for the video export.

## Use

Ask your agent:

- «می‌خواهم برای مجمع شرکتمان فیلم بسازم.»
- «یک پروژه‌ی جدید فیلم مجمع ۱۴۰۵ در `D:\Majmae-1405` بساز.»
- "Check the numbers in `2-deck/deck-v1.pptx` against the approved Excel."

## Contents

| Path | Purpose |
|---|---|
| `SKILL.md` | Agent instructions |
| `references/listed-company-agm.md` | AGM content rules and compliance checklist (checklist, not legal advice) |
| `assets/project-template/` | `company.md` (company and meeting intake), `PROJECT.md` (stage guide, Grok prompts, naming, PowerPoint steps), `settings.md`, `approvals.md`, `handoff-log.md` |
| `scripts/new_project.py` | Create a project folder from the template |
| `scripts/check_numbers.py` | Compare numbers in a `.pptx` or `.md` with an `.xlsx` |

```bash
python scripts/new_project.py "D:/Majmae-1405" --name "فیلم مجمع ۱۴۰۵" --year 1405
python scripts/check_numbers.py 1-excel/majmae-1405-approved.xlsx 2-deck/deck-v1.pptx -o 2-deck/deck-v1-check.md
```
