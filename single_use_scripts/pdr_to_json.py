#!/usr/bin/env python3
"""
pdr_to_json.py
Parse a "Project Decision Report (PDR).docx" and emit:
{
  "project_name": "...",
  "metrics": {
    "<metric name>": {"score": int, "evaluation": str|null}
  }
}

Heuristics tailored to the sample PDR:
- Sub-metric scores appear in 2-column tables: [name, 1..5]
- Evaluations appear as "Name (x/5): text" lines OR a header
  "Name (x/5):" followed by the next paragraph as the text.
- Project name is read from a key-value row like "Project – Proje | <value>"
  (if empty in the file, the result will be "").
"""
import sys, json, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def _doc_xml(docx_path: Path, part="word/document.xml") -> bytes:
    with zipfile.ZipFile(docx_path, "r") as z:
        return z.read(part)

def _wtext(el) -> str:
    return "".join((t.text or "") for t in el.findall(".//w:t", NS))

def _split_bilingual(label: str) -> str:
    # Prefer the left side when label is "English – Turkish" or "English - Turkish"
    if "–" in label:
        return label.split("–", 1)[0].strip()
    if " - " in label:
        return label.split(" - ", 1)[0].strip()
    return label.strip()

def parse_pdr(docx_path: Path) -> dict:
    root = ET.fromstring(_doc_xml(docx_path))
    paragraphs = [_wtext(p).strip() for p in root.findall(".//w:p", NS)]
    tables = []
    for tbl in root.findall(".//w:tbl", NS):
        rows = []
        for tr in tbl.findall("w:tr", NS):
            row = []
            for tc in tr.findall("w:tc", NS):
                row.append(_wtext(tc).strip())
            rows.append(row)
        tables.append(rows)

    # 1) Project name from KV row like "Project – Proje"
    project_name = ""
    proj_key = re.compile(r"^Project\s*[–-]\s*Proje\b|^Project\s*[–-]\b|^Project Name\b", re.IGNORECASE)
    for tbl in tables:
        for row in tbl:
            if len(row) >= 2 and proj_key.match(row[0] or ""):
                project_name = row[1].strip()
                break
        if project_name:
            break

    metrics: dict[str, dict] = {}

    # helper: add numeric score from table
    def add_score(name_raw: str, val: str):
        name = _split_bilingual(name_raw)
        m = re.fullmatch(r"\s*([1-5])\s*", val)
        if not m:
            return
        score = int(m.group(1))
        entry = metrics.setdefault(name, {"score": score, "evaluation": None})
        entry["score"] = score

    # 2) Pick up scores from 2-col rows
    for tbl in tables:
        for row in tbl:
            if len(row) == 2:
                add_score(row[0], row[1])

    # 3) Evaluations from inline "Name (x/5): text"
    note_inline = re.compile(r"^\s*(?P<name>.+?)\s*\((?P<s>[1-5])\/5\)\s*:\s*(?P<txt>.+)$", re.DOTALL)
    for p in paragraphs:
        m = note_inline.match(p)
        if not m:
            continue
        name = _split_bilingual(m.group("name").strip())
        score = int(m.group("s"))
        text = m.group("txt").strip()
        entry = metrics.setdefault(name, {"score": score, "evaluation": text})
        entry["score"] = score
        if entry.get("evaluation"):
            if text not in entry["evaluation"]:
                entry["evaluation"] += " " + text
        else:
            entry["evaluation"] = text

    # 4) Evaluations from header + next paragraph
    header_pat = re.compile(r"^\s*(?P<name>.+?)\s*\((?P<s>[1-5])\/5\)\s*:\s*$")
    for i, p in enumerate(paragraphs):
        m = header_pat.match(p)
        if not m:
            continue
        name = _split_bilingual(m.group("name").strip())
        score = int(m.group("s"))
        nxt = paragraphs[i+1].strip() if i+1 < len(paragraphs) else ""
        # skip if next is another header/inline
        if header_pat.match(nxt) or note_inline.match(nxt):
            text = ""
        else:
            text = nxt
        entry = metrics.setdefault(name, {"score": score, "evaluation": text or None})
        entry["score"] = score
        if text:
            if entry.get("evaluation"):
                if text not in entry["evaluation"]:
                    entry["evaluation"] += " " + text
            else:
                entry["evaluation"] = text

    # 5) Single-cell effort notes, attach if missing
    single_cells = []
    for tbl in tables:
        if len(tbl) == 1 and len(tbl[0]) == 1:
            t = (tbl[0][0] or "").strip()
            if t and not note_inline.match(t) and not header_pat.match(t):
                single_cells.append(t)
    if single_cells:
        generic = " ".join(single_cells)
        for k in list(metrics.keys()):
            lk = k.lower()
            if any(term in lk for term in ["timeline", "effort", "person-day", "duration", "team footprint"]):
                if not metrics[k].get("evaluation"):
                    metrics[k]["evaluation"] = generic

    return {"project_name": project_name, "metrics": metrics}

def main():
    in_doc = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Project Decision Report (PDR).docx")
    out_json = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("pdr_output.json")
    data = parse_pdr(in_doc)
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}")

if __name__ == "__main__":
    main()
