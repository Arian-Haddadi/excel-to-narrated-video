"""Per-sentence sync plan for PowerPoint: when each sentence starts in each slide's audio.

Usage: python sync_plan.py <project-folder>

Reads   3-script/tts/slide-NN.txt        spoken text (from tts_prep.py)
        3-script/script-approved.md      Grok scene tables (what to show/highlight per sentence)
        4-audio/slide-NN.mp3             ElevenLabs audio
Writes  4-audio/timings.md               slide length and auto-advance time
        4-audio/sync.md                  per slide: sentence | start (s) | show | highlight
Needs ffmpeg/ffprobe on PATH.

Sentence starts come from pauses (ffmpeg silencedetect): the N-1 longest pauses inside the
speech are taken as sentence boundaries. When there are too few pauses, starts are spread by
sentence length and the slide is marked «تخمینی» for a human to check by ear.
"""
import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts_prep import HEAD, DIGITS  # noqa: E402

NOISE_DB = -35   # ponytail: fixed threshold; raise toward -30 if room noise/music hides pauses
MIN_PAUSE = 0.25  # seconds
SENT_SPLIT = re.compile(r"(?<=[.!؟?؛])\s+|\n+")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip())


def pauses(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                          f"silencedetect=noise={NOISE_DB}dB:d={MIN_PAUSE}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def sentence_starts(audio, n):
    total = duration(audio)
    ps = pauses(audio)
    speech_start, speech_end = 0.0, total
    inner = []
    for s, e in ps:
        e = total if e is None else e
        if s <= 0.05:
            speech_start = e
        elif e >= total - 0.05:
            speech_end = s
        else:
            inner.append((s, e))
    if n <= 1:
        return total, [speech_start], False
    if len(inner) >= n - 1:
        chosen = sorted(sorted(inner, key=lambda p: p[1] - p[0], reverse=True)[: n - 1])
        return total, [speech_start] + [e for _, e in chosen], False
    return total, None, True  # caller spreads by length


def spread(sents, start, end):
    weights = [max(len(s), 1) for s in sents]
    t, out = start, []
    for w in weights:
        out.append(t)
        t += (end - start) * w / sum(weights)
    return out


def scene_tables(script):
    tables, cur = {}, None
    if not script.exists():
        return tables
    for line in script.read_text(encoding="utf-8").splitlines():
        m = HEAD.match(line)
        if m:
            cur = tables.setdefault(int(m.group(1).translate(DIGITS)), [])
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else None
        if cur is None or not cells or len(cells) < 3 or set("".join(cells)) <= set("-: "):
            continue
        if cells[0] == "جمله":
            continue
        cur.append(cells[1:3])
    return tables


def fmt(t):
    return f"{t:.2f}"


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    tts_dir, audio_dir = root / "3-script" / "tts", root / "4-audio"
    scenes = scene_tables(root / "3-script" / "script-approved.md")
    timing_rows, sync, flagged, missing = [], ["# Sync plan", "",
        "در PowerPoint برای هر برجسته‌سازی: Animations › Start: **With Previous** و **Delay** = «شروع (ثانیه)».", ""], [], []

    for txt in sorted(tts_dir.glob("slide-*.txt")):
        no = int(re.search(r"(\d+)", txt.stem).group(1))
        audio = audio_dir / f"slide-{no:02d}.mp3"
        if not audio.exists():
            missing.append(f"{no:02d}")
            continue
        sents = sentences(txt.read_text(encoding="utf-8"))
        total, starts, estimated = sentence_starts(audio, len(sents))
        if estimated:
            starts = spread(sents, 0.0, total)
            flagged.append(f"{no:02d}")
        advance = math.ceil((total + 1) * 4) / 4
        timing_rows.append(f"| {no:02d} | {fmt(total)} | {advance:.2f} |")

        rows = scenes.get(no, [])
        offset = len(sents) - len(rows) if 0 <= len(sents) - len(rows) <= 1 else None
        sync += [f"## slide-{no:02d}" + (" — تخمینی، با گوش چک شود" if estimated else ""), "",
                 "| # | شروع (ثانیه) | جمله | نمایش | برجسته |", "|---|---|---|---|---|"]
        for i, (s, t) in enumerate(zip(sents, starts)):
            scene = rows[i - offset] if offset is not None and 0 <= i - offset < len(rows) else ["", ""]
            short = s if len(s) <= 60 else s[:57] + "…"
            sync.append(f"| {i + 1} | {fmt(t)} | {short} | {scene[0]} | {scene[1]} |")
        if rows and offset is None:
            sync.append(f"\nتعداد ردیف‌های جدول صحنه ({len(rows)}) با تعداد جمله‌ها ({len(sents)}) نمی‌خواند؛ نمایش/برجسته را دستی جفت کن.")
        sync.append("")

    (audio_dir / "timings.md").write_text("\n".join([
        "# Timings", "", "در PowerPoint › Transitions › After = ستون «پیشروی (ثانیه)».", "",
        "| اسلاید | طول صوت (ثانیه) | پیشروی (ثانیه) |", "|---|---|---|", *timing_rows]), encoding="utf-8")
    (audio_dir / "sync.md").write_text("\n".join(sync), encoding="utf-8")
    print(f"{len(timing_rows)} slides; estimated: {', '.join(flagged) or '-'}; missing audio: {', '.join(missing) or '-'}")
    return 1 if flagged or missing else 0


if __name__ == "__main__":
    sys.exit(main())
