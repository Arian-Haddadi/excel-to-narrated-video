"""Turn an approved narration script into clean per-slide text for ElevenLabs.

Usage: python tts_prep.py <script-approved.md> [--lexicon lexicon.md] [--out 3-script/tts] [--no-title]

- Splits on slide headers (`اسلاید N`, `[اسلاید N]`, `Slide N`); headers never reach the audio text.
- Drops scene-timing tables, markdown, and the `متن گوینده:` label.
- Applies the pronunciation lexicon (whole words, longest first): P/E, NAV, همت, symbols, names.
- Writes numbers, decimals (ممیز ... دهم/صدم/هزارم), percents, ranges and dates as Persian words.
- Writes slide-NN.txt per slide, script-tts.md (headers outside the text) and report.md that lists
  leftovers to fix: Latin letters, digits, symbols, the word «اسلاید», promotional words, long slides.
Exit code 1 when report.md has open items.
"""
import argparse
import re
import sys
from pathlib import Path

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
ONES = ["صفر", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نُه"]
TEENS = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
TENS = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
HUNDREDS = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نُهصد"]
SCALES = ["", "هزار", "میلیون", "میلیارد", "هزار میلیارد"]
FRACTIONS = {1: "دهم", 2: "صدم", 3: "هزارم"}
MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
TONE_WORDS = ["خیره‌کننده", "درخشان", "بی‌سابقه", "فوق‌العاده", "بی‌نظیر", "تضمین"]
MAX_CHARS = 5000  # ElevenLabs per-request limit on the strictest model; split longer slides

NUM = r"\d{1,3}(?:[٬,،]\d{3})+(?:[٫.]\d+)?|\d+(?:[٫.]\d+)?"
HEAD = re.compile(r"^[\s*#\[]*(?:اسلاید|slide)\s*([0-9۰-۹]+)[\]\s*]*[—–:\-]?\s*(.*?)[\s*]*$", re.I)


def under_1000(n):
    h, r = divmod(n, 100)
    parts = [HUNDREDS[h]] if h else []
    if 10 <= r < 20:
        parts.append(TEENS[r - 10])
    else:
        t, o = divmod(r, 10)
        if t:
            parts.append(TENS[t])
        if o:
            parts.append(ONES[o])
    return " و ".join(parts)


def words(n):
    if n == 0:
        return "صفر"
    groups, i = [], 0
    while n:
        n, g = divmod(n, 1000)
        if g:
            if i >= len(SCALES):
                raise ValueError("number too large")
            head = "" if g == 1 and SCALES[i].startswith("هزار") else under_1000(g)
            groups.append(f"{head} {SCALES[i]}".strip())
        i += 1
    return " و ".join(reversed(groups))


def number_words(raw):
    s = re.sub(r"[٬,،]", "", raw).replace("٫", ".")
    ip, _, fp = s.partition(".")
    out = words(int(ip))
    fp = fp.rstrip("0")
    if fp:
        if len(fp) in FRACTIONS:
            out += f" ممیز {words(int(fp))} {FRACTIONS[len(fp)]}"
        else:
            out += " ممیز " + " ".join(ONES[int(d)] for d in fp)
    return out


def ordinal(n):
    w = words(n)
    if w.endswith("سه"):
        return w[:-2] + "سوم"
    if w.endswith("ی"):
        return w + "‌اُم"
    return w + "م"


def date_words(m):
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= mo <= 12:
        return m.group(0)
    return f"{ordinal(d)} {MONTHS[mo - 1]} {words(y)}"


def load_lexicon(path):
    lex = {}
    if path and Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and cells[1] and cells[0] != "نوشتار" and not set(cells[0]) <= set("-: "):
                lex[cells[0]] = cells[1]
    return lex


def apply_lexicon(text, lex):
    if not lex:
        return text
    keys = sorted(lex, key=len, reverse=True)
    pat = re.compile(r"(?<![\w‌])(" + "|".join(map(re.escape, keys)) + r")(?![\w‌])", re.I)
    low = {k.lower(): v for k, v in lex.items()}
    return pat.sub(lambda m: low[m.group(1).lower()], text)


def to_speech(text, lex):
    text = apply_lexicon(text, lex)
    text = text.translate(DIGITS)
    text = re.sub(r"(?<!\d)(\d{4})/(\d{1,2})/(\d{1,2})(?!\d)", date_words, text)
    text = re.sub(rf"({NUM})\s*[-–]\s*({NUM})", r"\1 تا \2", text)
    text = re.sub(rf"(?<![\w\d])-\s*(?=\d)", "منفی ", text)
    text = re.sub(rf"({NUM})\s*[%٪]", lambda m: number_words(m.group(1)) + " درصد", text)
    text = re.sub(NUM, lambda m: number_words(m.group(0)), text)
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_slides(path, with_title=True):
    slides, cur = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = HEAD.match(line)
        if m:
            title = m.group(2).strip(" *—–-:")
            cur = {"no": int(m.group(1).translate(DIGITS)), "lines": []}
            if with_title and title:
                cur["lines"].append(title if title[-1] in ".؟!:؛" else title + ".")
            slides.append(cur)
            continue
        s = line.strip()
        if cur is None or not s or s.startswith("|") or s.startswith("---") or s.startswith("زمان‌بندی"):
            continue
        s = re.sub(r"^(?:[#>*\-•]+\s*)+", "", s)
        s = re.sub(r"^متن گوینده\s*:\s*", "", s).replace("**", "")
        if s:
            cur["lines"].append(s)
    return slides


def issues_of(text):
    found = []
    if re.search(r"[A-Za-z]", text):
        found.append("حرف لاتین: " + ", ".join(sorted(set(re.findall(r"[A-Za-z][A-Za-z/&.]*", text)))) + " → به lexicon.md اضافه شود")
    if re.search(r"\d", text):
        found.append("عدد تبدیل‌نشده: " + ", ".join(sorted(set(re.findall(r"\d[\d.,/]*", text)))))
    sym = sorted(set(re.findall(r"[%٪/\\_=+<>@#&*()\[\]{}|~^$\-–]", text)))
    if sym:
        found.append("نماد: " + " ".join(sym))
    if "اسلاید" in text:
        found.append("کلمه‌ی «اسلاید» در متن صدا")
    tone = [w for w in TONE_WORDS if w in text]
    if tone:
        found.append("لحن تبلیغاتی (قواعد مجمع): " + "، ".join(tone))
    if len(text) > MAX_CHARS:
        found.append(f"{len(text)} کاراکتر؛ بیشتر از {MAX_CHARS}، دو تکه شود")
    if not text:
        found.append("متن خالی")
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--lexicon")
    ap.add_argument("--out")
    ap.add_argument("--no-title", action="store_true")
    a = ap.parse_args()

    out = Path(a.out) if a.out else Path(a.script).parent / "tts"
    out.mkdir(parents=True, exist_ok=True)
    lex = load_lexicon(a.lexicon)
    slides = parse_slides(a.script, not a.no_title)
    if not slides:
        sys.exit("No slide headers found (expected lines like «اسلاید ۱» or «[اسلاید ۱]»).")

    seen, combined, rows, open_items = set(), [], [], 0
    for s in slides:
        text = to_speech("\n".join(s["lines"]), lex)
        found = issues_of(text)
        if s["no"] in seen:
            found.append("شماره‌ی تکراری")
        seen.add(s["no"])
        (out / f"slide-{s['no']:02d}.txt").write_text(text + "\n", encoding="utf-8")
        combined += [f"## slide-{s['no']:02d}", "", text, ""]
        rows.append(f"| {s['no']:02d} | {len(text)} | {'؛ '.join(found) or '✓'} |")
        open_items += len(found)

    (out / "script-tts.md").write_text("\n".join(combined), encoding="utf-8")
    report = ["# TTS report", "", f"اسلاید: {len(slides)} — موارد باز: **{open_items}** — واژه‌نامه: {len(lex)} مدخل", "",
              "| اسلاید | کاراکتر | مورد |", "|---|---|---|", *rows, "",
              "هر مورد باز را در lexicon.md یا متن تأییدشده اصلاح کن و دوباره اجرا کن؛ فایل‌های slide-NN.txt را دستی ویرایش نکن."]
    (out / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"{out}: {len(slides)} slides, {open_items} open items")
    return 1 if open_items else 0


if __name__ == "__main__":
    sys.exit(main())
