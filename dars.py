#!/usr/bin/env python3
"""Darsi Kutub (dars books): the rule, the compact keys in the shared book list, and darsi-kutub.csv.

The rule
  A kitab with more than one copy keeps ONE copy in the madrasah library; the other copies are
  madrasah (dars) copies used by the year groups.
    library copy     = 1
    madrasah copies  = total copies (c) - 1, unless the master catalogue gives "Madrasah copies"
                       (some dars books keep their class copies outside the library)

Where the data lives: the master catalogue (the library spreadsheet build.py reads), and nowhere
else. Three optional columns per row:
    Dars             yes / no / blank
    Years            year groups, separated by commas or semicolons: "Year 1, Year 2, Iftā"
    Madrasah copies  a number, only to override c - 1

    Dars = no                -> not darsi
    Dars = yes               -> darsi
    Dars blank and c > 1     -> darsi as a SUGGESTION (more than one copy is not proof)
    A darsi book with no Years is "unconfirmed" and is listed under Unassigned until a teacher
    sets its year groups.

What goes into books.<hash>.json (on the book's row, next to c):
    mc  madrasah copies (int). Present only on darsi books, so its presence means "darsi".
    y   year groups (list of str). Present only once a teacher has set them (= confirmed).

Using it from build.py (three calls):
    import dars
    # 1. per spreadsheet row, while building P["books"][id] (after c is known):
    book.update(dars.fields(row, book.get("c", 1)))      # row: that row's {column: value}
    # 2. after P is complete and the WHERE layout is known:
    dars.write_csv(P, where, "darsi-kutub.csv")
    # 3. add './dars.html' to the pages it stamps (sw.js PAGES), './darsi-kutub.csv' to OTHER,
    #    and copy the WHERE layout into dars.html's <script id="where"> as it does for index.html.

Until build.py is changed, `python3 dars.py` does the same to the files already in this folder:
it applies the rule to the current books.<hash>.json (keeping any y/mc already in it), writes it
under its new hash, points every page and sw.js at it, copies the WHERE layout from index.html
into dars.html, stamps a new VERSION in sw.js and writes darsi-kutub.csv.
"""
import csv
import glob
import hashlib
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = ["index.html", "shelves.html", "3d.html", "dars.html"]

# the order year groups are listed in (anything else follows, alphabetically)
YEAR_ORDER = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6", "Year 7", "Year 8",
              "Dawrah", "Takhaṣṣuṣ", "Iftā"]
UNASSIGNED = "Unassigned"


def _col(row, *names):
    """A row's value for the first column whose name matches (case and spaces ignored)."""
    want = {re.sub(r"[\s_]+", "", n.lower()) for n in names}
    for k, v in (row or {}).items():
        if re.sub(r"[\s_]+", "", str(k).lower()) in want:
            return v
    return None


def parse_years(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        parts = v
    else:
        parts = re.split(r"[,;\n،]+", str(v))
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", str(p)).strip()
        if re.fullmatch(r"\d+", p):
            p = "Year " + p
        m = re.fullmatch(r"(?i)y(?:ea)?r\.?\s*(\d+)", p)
        if m:
            p = "Year " + m.group(1)
        if p and p not in out:
            out.append(p)
    return sorted(out, key=year_key)


def year_key(y):
    return (YEAR_ORDER.index(y), "") if y in YEAR_ORDER else (len(YEAR_ORDER), y.lower())


def fields(row, c):
    """The compact dars keys for one book: {} if not darsi, else {'mc': n} plus 'y' once confirmed."""
    c = int(c or 1)
    flag = str(_col(row, "dars", "darsi") or "").strip().lower()
    if flag in ("no", "n", "false", "0", "x"):
        return {}
    if flag not in ("yes", "y", "true", "1") and c <= 1:
        return {}
    mc = _col(row, "madrasah copies", "madrasahcopies", "mc")
    try:
        mc = int(float(mc)) if mc not in (None, "") else max(c - 1, 0)
    except (TypeError, ValueError):
        mc = max(c - 1, 0)
    out = {"mc": mc}
    years = parse_years(_col(row, "years", "year groups", "y"))
    if years:
        out["y"] = years
    return out


# ---------------------------------------------------------------- the darsi list (CSV)

def _entries(P):
    """The Search page's entries (merged rows, with their patches), as the pages rebuild them."""
    B = P["books"]
    for x in P["search"]:
        ids, patch = (x[0], x[1]) if isinstance(x[0], list) else (x, {})
        b = dict(B[ids[0]])
        for k in patch.get("_d", []):
            b.pop(k, None)
        b.update({k: v for k, v in patch.items() if k != "_d"})
        b["s"] = ids
        yield b


def shelves_of(ids, where):
    """Plain-words locations of a book from the Shelf Map layout."""
    if not where or "shelves" not in where:
        return ""
    want = set(ids)
    levels = where.get("levels", 6)
    found = []
    for sid, items in where["shelves"].items():
        for si, row, _n in items:
            if f'{where["sheets"][si]}!{row}' in want:
                if sid == "tray":
                    found.append("In the tray (not shelved yet)")
                else:
                    case, lvl = sid.split("-")
                    lvl = int(lvl)
                    words = "top shelf" if lvl == 1 else "bottom shelf" if lvl == levels else f"shelf {lvl} from the top"
                    found.append(f"Case {case}, {words} ({sid})")
    return "; ".join(dict.fromkeys(found)) or "Not on the shelves yet"


def rows(P, where=None):
    cats = P["cats"]
    out = []
    for b in _entries(P):
        if "mc" not in b:
            continue
        ks = b["k"] if isinstance(b["k"], list) else [b["k"]]
        out.append({
            "Title": b["t"], "Author": b.get("a", ""),
            "Category": " / ".join(cats[k]["en"] for k in ks),
            "Year groups": ", ".join(b.get("y", [])) or "Unassigned (unconfirmed)",
            "Total copies": b.get("c", 1), "Library copy": 1, "Madrasah copies": b["mc"],
            "Shelf": shelves_of(b["s"], where),
            "_ids": b["s"],
        })
    out.sort(key=lambda r: (r["Year groups"].startswith("Unassigned"), r["Year groups"], r["Title"]))
    return out


COLUMNS = ["Title", "Author", "Category", "Year groups", "Total copies", "Library copy", "Madrasah copies", "Shelf"]


def write_csv(P, where, path):
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLUMNS, extrasaction="ignore", lineterminator="\r\n")
    w.writeheader()
    for r in rows(P, where):
        w.writerow(r)
    # a BOM so Excel opens the Arabic and Urdu as UTF-8
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(buf.getvalue())


# ---------------------------------------------------------------- restamp the files in this folder

def _where_from(html):
    m = re.search(r'<script type="application/json" id="where">(.*?)</script>', html, re.S)
    return m.group(1) if m else None


def main():
    os.chdir(HERE)
    sw = open("sw.js", encoding="utf-8").read()
    old = re.search(r"const BOOKS = '\./(books\.[0-9a-f]+\.json)'", sw).group(1)
    P = json.load(open(old, encoding="utf-8"))
    for row_id, b in P["books"].items():
        keep = {"dars": "yes"} if "mc" in b else {}
        if "y" in b:
            keep["years"] = b["y"]
        if "mc" in b and b["mc"] != max(int(b.get("c", 1)) - 1, 0):
            keep["madrasah copies"] = b["mc"]
        b.pop("mc", None)
        b.pop("y", None)
        b.update(fields(keep, b.get("c", 1)))
    raw = json.dumps(P, ensure_ascii=False, separators=(",", ":")).encode()
    new = f"books.{hashlib.sha256(raw).hexdigest()[:10]}.json"
    if new != old:
        open(new, "wb").write(raw)
        for f in glob.glob("books.*.json"):
            if f != new:
                os.remove(f)
    where_txt = _where_from(open("index.html", encoding="utf-8").read())
    for page in PAGES + ["sw.js"]:
        if not os.path.exists(page):
            continue
        t = open(page, encoding="utf-8").read()
        t2 = re.sub(r"books\.[0-9a-f]{10}\.json", new, t)
        if page == "dars.html" and where_txt is not None:
            t2 = re.sub(r'(<script type="application/json" id="where">).*?(</script>)',
                        lambda m: m.group(1) + where_txt + m.group(2), t2, flags=re.S)
        if page == "sw.js":
            t2 = re.sub(r"const VERSION = '\d+';", f"const VERSION = '{time.strftime('%Y%m%d%H%M')}';", t2)
        if t2 != t:
            open(page, "w", encoding="utf-8").write(t2)
    write_csv(P, json.loads(where_txt) if where_txt else None, "darsi-kutub.csv")
    n = sum(1 for b in _entries(P) if "mc" in b)
    print(f"{new}: {n} darsi titles; darsi-kutub.csv written", file=sys.stderr)


if __name__ == "__main__":
    main()
