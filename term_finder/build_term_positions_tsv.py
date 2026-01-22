import re
from pathlib import Path
import pandas as pd
from collections import defaultdict


# Paths
TERM_FINDER_DIR = Path(__file__).resolve().parent            # .../term_finder
PROJECT_DIR = TERM_FINDER_DIR.parent                         # .../v2 (or your repo root)
OUTPUT_ROOT = TERM_FINDER_DIR / "output"                     # term_finder/output/term_occur00001...
DICT_PATH = PROJECT_DIR / "tsv-data" / "merge_lt_dict_v3.tsv"
OUT_PATH = PROJECT_DIR / "tsv-data" / "merge_lt_dict_v3_with_positions.tsv"  #output

PREFERRED_OUTPUT_FILENAME = "trie-output.txt"
FALLBACK_OUTPUT_FILENAME = "aho-output.txt"

HEADER_FILE_RE = re.compile(r"^File:\s*(.+)$")
TERM_LINE_RE = re.compile(r"^(?P<term>\S.*?)\s{2,}(?P<lines>[\d,\s]+)\s{2,}(?P<wps>[\d,\s]+)\s*$")
CONT_LINE_RE = re.compile(r"^\s{2,}(?P<lines>[\d,\s]+)\s{2,}(?P<wps>[\d,\s]+)\s*$")


def _to_int_list(s: str):
    s = s.replace(" ", "")
    if not s:
        return []
    return [int(x) for x in s.split(",") if x != ""]


def _zip_positions(line_str: str, wp_str: str):
    ls = _to_int_list(line_str)
    ws = _to_int_list(wp_str)
    n = min(len(ls), len(ws))
    return list(zip(ls[:n], ws[:n]))


def normalize_doc_id(doc_file: str | None):
    if not doc_file:
        return None
    doc_file = doc_file.strip()
    if doc_file.lower().endswith(".txt"):
        doc_file = doc_file[:-4]
    return doc_file


def parse_output_txt(txt_path: Path):
    """
    Returns (doc_id, occurrences):
      occurrences: term(str) -> list[(line:int, word_place:int)] (duplicates kept)
    """
    if not txt_path.exists():
        return None, {}

    doc_file = None
    occurrences = defaultdict(list)

    lines = txt_path.read_text(encoding="utf-8", errors="replace").splitlines()
    current_term = None

    for raw in lines:
        raw = raw.rstrip("\n")

        mfile = HEADER_FILE_RE.match(raw)
        if mfile:
            doc_file = mfile.group(1).strip()
            continue

        m = TERM_LINE_RE.match(raw)
        if m:
            current_term = m.group("term").strip()
            occurrences[current_term].extend(_zip_positions(m.group("lines").strip(), m.group("wps").strip()))
            continue

        mc = CONT_LINE_RE.match(raw)
        if mc and current_term is not None:
            occurrences[current_term].extend(_zip_positions(mc.group("lines").strip(), mc.group("wps").strip()))
            continue

    return normalize_doc_id(doc_file), dict(occurrences)


# Main build
def main():
    df_dict = pd.read_csv(DICT_PATH, sep="\t", dtype=str).fillna("")
    required = {"id", "leg_term", "desc", "pos_tag", "term_root"}
    missing = required - set(df_dict.columns)
    if missing:
        raise ValueError(f"merge_lt_dict_v3.tsv missing columns: {missing}. Found: {list(df_dict.columns)}")

    # Map leg_term -> list of ids (string), to be safe with duplicates
    term_to_ids = defaultdict(list)
    for _, r in df_dict.iterrows():
        lt = str(r["leg_term"]).strip()
        if lt:
            term_to_ids[lt].append(str(r["id"]).strip())

    # Accumulator:
    # term_id -> doc_id -> list of (line, wp)
    hits = defaultdict(lambda: defaultdict(list))

    occur_dirs = sorted([p for p in OUTPUT_ROOT.glob("term_occur*") if p.is_dir()])
    if not occur_dirs:
        raise FileNotFoundError(f"No term_occur folders found under: {OUTPUT_ROOT}")

    for occur_dir in occur_dirs:
        preferred = occur_dir / PREFERRED_OUTPUT_FILENAME
        fallback = occur_dir / FALLBACK_OUTPUT_FILENAME
        txt_path = preferred if preferred.exists() else fallback

        doc_id, occ = parse_output_txt(txt_path)
        if not doc_id:
            # last-resort label
            doc_id = occur_dir.name

        for term, positions in occ.items():
            # Join output term -> dictionary id(s)
            ids = term_to_ids.get(term)
            if not ids:
                continue

            for term_id in ids:
                hits[term_id][doc_id].extend(positions)

    # Build aggregated columns aligned to df_dict row order (same number of rows)
    file_containing_col = []
    line_col = []
    wp_col = []

    for _, r in df_dict.iterrows():
        term_id = str(r["id"]).strip()
        doc_map = hits.get(term_id, {})

        if not doc_map:
            file_containing_col.append("")
            line_col.append("")
            wp_col.append("")
            continue

        # Stable order: by doc_id
        doc_ids = sorted(doc_map.keys())

        file_containing_col.append(", ".join(doc_ids))

        # Build per-doc position strings
        doc_line_parts = []
        doc_wp_parts = []
        for d in doc_ids:
            pos = doc_map[d]
            # Keep duplicates (reflects real repeated occurrences)
            lines = ", ".join(str(x[0]) for x in pos)
            wps = ", ".join(str(x[1]) for x in pos)
            doc_line_parts.append(f"{d}: {lines}")
            doc_wp_parts.append(f"{d}: {wps}")

        # Use " | " delimiter between docs
        line_col.append(" | ".join(doc_line_parts))
        wp_col.append(" | ".join(doc_wp_parts))

    df_out = df_dict.copy()
    df_out["file_containing"] = file_containing_col
    df_out["line"] = line_col
    df_out["word_place"] = wp_col

    # Write back into tsv-data with same name (overwrite)
    df_out.to_csv(OUT_PATH, sep="\t", index=False, encoding="utf-8")
    print(f"Saved: {OUT_PATH}")
    print(f"Rows: {len(df_out)} (same as dictionary)")

if __name__ == "__main__":
    main()
