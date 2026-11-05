---
name: excel-to-narrated-video
description: Guided team workflow for an AGM video (فیلم مجمع) of a company listed on the Tehran Stock Exchange or Iran Fara Bourse. It goes financial Excel → Persian PowerPoint (Grok) → narration (Grok) → ElevenLabs voice → PowerPoint video export. The agent guides the user step by step, collects company info (name, symbol, logo, agenda), applies listed-company AGM content rules, checks every number against the Excel, and supports handoff between team members.
example-prompt: می‌خواهم برای مجمع شرکتمان فیلم بسازم.
---

# فیلم مجمع: Excel → Deck → Narration → Voice → Video

You are the user's **guide**. People run each stage in Grok, ElevenLabs, and PowerPoint and approve it. You lead them through the process, ask for what is missing, check the work, and always say the one next step. Never automate Grok or ElevenLabs, skip an approval, or fix a number on your own. Talk to the user in Persian.

## On every invocation

1. **Find the project.** Ask for the project folder, or offer to create one. Suggest `<drive>:\Majmae-<year>`.
   - New: `python scripts/new_project.py "<folder>" --name "<name>" --year <year>`
   - Existing: read `PROJECT.md` «تحویل و وضعیت فعلی» and `company.md`.
2. **Tell the user where they are:** the current stage, what is done, and what is missing.
3. **Do the agent part** of the current stage. See below.
4. **End with the next step** as one short instruction: who does what, in which tool, and which file to save where. Example: «حالا در grok.com فایل اکسل و لوگو را آپلود کن، پرامپت ۲ را از `PROJECT.md` بده و خروجی را با اسم `2-deck/deck-v1.pptx` ذخیره کن.»
5. Update «تحویل و وضعیت فعلی» and the checkboxes in `PROJECT.md`. Add a row to `handoff-log.md` when the owner changes.

## Stage 0: company intake (guided)

Ask the questions in `company.md` in **small groups of 3 or 4**. Give a suggested answer where one exists. Accept "پیشنهادی را قبول دارم". Groups:
1. Company: full name, symbol, market, logo file.
2. Meeting: type, fiscal year end, date, format (in person, DIMA electronic, or hybrid), and where the video will be used.
3. Agenda: ask the user to paste the agenda text from the Codal invitation (آگهی دعوت). Do not invent agenda items.
4. Auditor and type of audit opinion, proposed dividend per share, and Chair and CEO names (optional).
5. Documents: the Codal PDFs into `1-excel/sources/`. Check each one off.
6. Pronunciation: the company symbol, subsidiary symbols and names, and other proper names. Write them into `lexicon.md` with a phonetic spelling, for example `وتوصا` → `وَتوصا`. Suggest the spelling and let the user correct it.

Write the answers into `company.md` as you go. Ask the user to put the logo at `assets/logo.png`. Check that the file exists and is a PNG or SVG. If it has no transparent background, tell the user.

## Content rules: read before stages 2, 3, and 5

Read `references/listed-company-agm.md`. In short:
- The slide order follows the meeting agenda.
- Numbers come only from the approved Excel and the published audited statements.
- Nothing material that is not yet disclosed on Codal goes in the video.
- The dividend is a "board proposal", and Article 129 transactions are "for ratification".
- The audit opinion type is stated in full.
- The tone is neutral, with no forward-looking promises.
- Fill the Grok prompts in `PROJECT.md` with the data from `company.md` before giving them to the user.
- The reference file is a checklist, not legal advice. Items marked [تأیید شود] must be confirmed by the company's AGM affairs or legal team. Say so when one of them matters.

## Agent part per stage

0. **Intake:** as above.
1. **Excel:** list the sheets and key figures with sheet and cell. Compare the headline figures with the audited statements in `sources/` when they are readable. Never edit the Excel.
2. **Deck:** `python scripts/check_numbers.py <approved.xlsx> <deck-vN.pptx> -o 2-deck/deck-vN-check.md`. Then review against the rules: agenda order, logo and company name, audit opinion, "proposed" dividend, no undisclosed information, Persian RTL and Persian digits.
3. **Script:** run the same number check on `script-vN.md` and the same rules review on tone and wording. Also check internal consistency: parts add up to their total, a figure repeated on two slides is identical, and units (ریال, تومان, همت) are used consistently. List every inconsistency for the finance expert. After approval, run `python scripts/tts_prep.py 3-script/script-approved.md --lexicon lexicon.md`. It writes `3-script/tts/slide-NN.txt` (numbers and decimals as words, lexicon applied, no «اسلاید N» headers) and `tts/report.md`. Resolve every open item through `lexicon.md` or the approved script, then run it again. Never hand-edit the `slide-NN.txt` files.
4. **Audio:** guide the user with `references/elevenlabs-persian.md`: a model test on the hardest slide (Multilingual v2 against v3), settings recorded in `settings.md`, one file per slide, and a fix-in-lexicon, regenerate-only-that-slide loop. Check that there is one non-empty `slide-NN.mp3` per slide. Then run `python scripts/sync_plan.py <project>`. It writes `4-audio/timings.md` (audio length and auto-advance per slide) and `4-audio/sync.md` (start time of each sentence, paired with the show and highlight columns of the Grok scene table). Slides marked «تخمینی» or with a scene-table mismatch need a person to check them by ear.
5. **Video:** guide the PowerPoint steps in `PROJECT.md`: auto-advance from `timings.md`, and each highlight animation set to With Previous with the delay from `sync.md`. Check the MP4 with `ffprobe`: the duration is close to the sum of the timings, with one video and one audio stream. Then walk the user through the compliance checklist in the reference file. Each item gets a yes or no from a person.

## check_numbers.py

- It reads slide text, tables, and chart data and needs only `openpyxl`. It handles Persian and Arabic digits and the ٬ ٫ separators.
- Match types: `exact`, `rounded` (to the decimals shown), `percent` (×100), and `scaled` (any power of ten, which covers ریال↔تومان and میلیارد/همت; the unit label must fit, so a person checks it).
- `NOT FOUND` is a review item, not proof of an error (years, counts). Exit code 1 means at least one number was not found.

## tts_prep.py

- It splits on `اسلاید N`, `[اسلاید N]`, or `Slide N` headers and keeps each slide title as the first spoken sentence (`--no-title` drops it). It drops the scene tables and the `متن گوینده:` label.
- It applies `lexicon.md` (whole words, longest first) before converting numbers. Numbers, decimals («ممیز … دهم/صدم/هزارم»), percents, ranges (`۱۱-۱۲` → «یازده تا دوازده»), and dates (`۱۴۰۴/۰۶/۳۱` → «سی و یکم شهریور …») become words.
- `report.md` flags Latin letters, leftover digits and symbols, the word «اسلاید», promotional words, and slides over 5,000 characters. Exit code 1 means there are open items.

## sync_plan.py

- It uses ffmpeg `silencedetect` (-35 dB, pauses ≥ 0.25 s). The N−1 longest pauses inside the speech become sentence boundaries, so short comma pauses are ignored.
- If there are fewer pauses than sentences, it spreads the starts by sentence length and marks the slide «تخمینی». Exit code 1 means estimated slides or missing audio.
- Scene-table rows are paired with sentences by order. When the slide title is spoken, it is the first sentence and has no row.

## Rules

- Approved files (`-approved`) are never edited. A new version gets `-vN+1`.
- Paths stay relative to the project folder, so the folder can move between people and computers.
- No passwords or API keys go in the project folder or in chat.
- Do not upload, send, or publish anything unless the user asks for that step.
