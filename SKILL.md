---
name: excel-to-narrated-video
description: Team workflow for turning a financial Excel into an approved Persian PowerPoint, narration script, ElevenLabs voiceover, and a PowerPoint-exported narrated video (e.g. an AGM / فیلم مجمع). People do each stage in Grok, ElevenLabs, and PowerPoint and approve it; the agent sets up the project folder, checks every number against the Excel, prepares TTS text, and computes slide timings. Projects are handed off between team members.
example-prompt: یک پروژه‌ی جدید فیلم مجمع ۱۴۰۵ در D:\Majmae-1405 بساز.
---

# Excel → Deck → Narration → Voice → Video (human-run, team handoff)

People run every stage in the tool's own UI and approve it. The agent assists; it never automates Grok/ElevenLabs, skips an approval, or fixes a number on its own.

## Start or resume a project

- **New project:** `python scripts/new_project.py "<folder>" --name "<project name>" --year <year>`. It creates `1-excel` … `5-video`, `PROJECT.md`, `settings.md`, `approvals.md`, and `handoff-log.md`. It never overwrites files. Then ask who holds each role and write them in `PROJECT.md`.
- **Existing project:** read `PROJECT.md` first, starting with «تحویل و وضعیت فعلی». It is the source for decisions, roles, file names, prompts, and the next step. Do only that step.

`PROJECT.md` (from `assets/project-template/`) holds the full stage guide, the Grok prompts, the file-naming rules, and the PowerPoint steps. Do not duplicate it here.

## What the agent does per stage

1. **Excel** — List sheets and key figures with sheet/cell as the review reference. Never edit the Excel.
2. **Deck** — `python scripts/check_numbers.py <approved.xlsx> <deck-vN.pptx> -o 2-deck/deck-vN-check.md`. Also check Persian RTL, Persian digits, and fonts by rendering a slide or reading the text.
3. **Script** — Run the same check on `script-vN.md`. Then write `3-script/script-tts.md`: the same text per slide, with numbers, percentages, dates, and units as Persian words.
4. **Audio** — Check that there is one `slide-NN.mp3` per slide, non-empty. Measure lengths with `ffprobe`. Write `4-audio/timings.md`: slide, audio length, and auto-advance = length + 1 s (rounded up to 0.25 s).
5. **Video** — After export, check the MP4 with `ffprobe`: duration ≈ sum of the timings, one video and one audio stream.

After each step, update «تحویل و وضعیت فعلی» and the stage checkbox in `PROJECT.md`. Add a row to `handoff-log.md` when the owner changes.

## check_numbers.py

- Reads slide text, tables, and chart data (stdlib; needs only `openpyxl`). Handles Persian/Arabic digits and ٬ ٫ separators.
- Match types: `exact`, `rounded` (to the decimals shown), `percent` (fraction ×100), and `scaled` (unit change ×1e3/1e6/1e9). `scaled` matches need a human look: the unit label must fit.
- `NOT FOUND` is a review item, not proof of an error (years, counts). Exit code 1 means at least one is not found.

## Rules

- The Excel the finance expert approved is the only source of numbers. Grok output is a draft until a person approves it.
- Approved files (`-approved`) are never edited. New versions get `-vN+1`.
- Keep paths relative to the project folder so the folder can move between people and computers.
- No passwords or API keys in the project folder or in chat. `settings.md` holds account names, voice, and model settings only.
- Do not upload, send, or publish anything unless the user asks for that step.
