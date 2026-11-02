"""Compare every number in a deck (.pptx) or script (.md/.txt) with an Excel workbook.

Usage: python check_numbers.py <excel.xlsx> <deck.pptx|script.md> [-o report.md]

Reads slide text, tables and chart data (stdlib zip/XML, no python-pptx needed).
Handles Persian/Arabic digits and separators. A number matches when it equals an
Excel value directly, after rounding to its shown decimals, as a percent of a
fraction, or scaled by 1e3/1e6/1e9 (unit changes). Unmatched numbers are listed
for human review; nothing is changed.
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

import openpyxl

DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
# thousands: ٬ , ، and thin/normal spaces between 3-digit groups; decimal: ٫ .
NUM_RE = re.compile(r"(?<![\w.])-?\d{1,3}(?:[٬,،]\d{3})+(?:[٫.]\d+)?|(?<![\w.])-?\d+(?:[٫.]\d+)?")
SCALES = (1, 1e3, 1e6, 1e9, 1e-3, 1e-6, 1e-9)


def parse_numbers(text):
    text = text.translate(DIGITS)
    out = []
    for m in NUM_RE.finditer(text):
        raw = m.group(0)
        s = re.sub(r"[٬,،]", "", raw).replace("٫", ".")
        try:
            out.append((raw, float(s), len(s.split(".")[1]) if "." in s else 0))
        except ValueError:
            pass
    return out


def excel_values(path):
    vals = {}
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                ref = f"{ws.title}!{getattr(c, 'coordinate', '?')}"
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    vals.setdefault(float(v), ref)
                elif isinstance(v, str):
                    for _, n, _ in parse_numbers(v):
                        vals.setdefault(n, ref)
    return vals


def match(n, decimals, vals):
    for v, ref in vals.items():
        for k in SCALES:
            for cand, how in ((v * k, "scaled" if k != 1 else "exact"), (v * 100 * k, "percent")):
                if cand == n or round(cand, decimals) == n:
                    return ref, how if (cand == n or how != "exact") else "rounded"
    return None, None


def deck_texts(path):
    """Yield (location, text) for each slide's text and its charts."""
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    slides = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda n: int(re.search(r"\d+", n.rsplit("/", 1)[1]).group()))
    for s in slides:
        no = re.search(r"slide(\d+)", s).group(1)
        xml = z.read(s).decode("utf-8")
        yield f"slide {no}", " | ".join(re.findall(r"<a:t>([^<]*)</a:t>", xml))
        rels = f"ppt/slides/_rels/slide{no}.xml.rels"
        if rels in names:
            for target in re.findall(r'Target="\.\./charts/(chart\d+\.xml)"', z.read(rels).decode("utf-8")):
                cxml = z.read(f"ppt/charts/{target}").decode("utf-8")
                yield f"slide {no} ({target})", " | ".join(re.findall(r"<c:v>([^<]*)</c:v>", cxml))


def script_texts(path):
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            yield f"line {i}", line


def check(excel, target):
    vals = excel_values(excel)
    texts = deck_texts(target) if str(target).lower().endswith(".pptx") else script_texts(target)
    rows, bad = [], 0
    for loc, text in texts:
        for raw, n, dec in parse_numbers(text):
            ref, how = match(n, dec, vals)
            if ref is None:
                bad += 1
            rows.append((loc, raw, ref or "—", how or "NOT FOUND"))
    return rows, bad


def report(rows, bad, excel, target):
    lines = [f"# Number check: `{Path(target).name}` vs `{Path(excel).name}`", "",
             f"Numbers: {len(rows)} — not found in Excel: **{bad}**", "",
             "| Where | Number | Excel cell | Match |", "|---|---|---|---|"]
    lines += [f"| {l} | {r} | {c} | {m} |" for l, r, c, m in rows]
    lines += ["", "NOT FOUND does not always mean wrong (years, counts, slide numbers): a human decides."]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("excel")
    ap.add_argument("target")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    rows, bad = check(a.excel, a.target)
    text = report(rows, bad, a.excel, a.target)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"{a.out}: {len(rows)} numbers, {bad} not found")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
