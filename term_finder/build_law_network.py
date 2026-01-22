# -*- coding: utf-8 -*-
"""
Build a law-to-law network from term_finder outputs.

Inputs:
- v2/tsv-data/merge_lt_dict_v3.tsv
- v2/term_finder/output/term_occur00001 ... term_occur00844/{trie-output.txt, aho-output.txt}

Outputs (written to v2/tsv-data/):
- law_term_presence.tsv          (law, term_id, occurrences)
- law_network_edges.tsv          (law_a, law_b, shared_terms, jaccard)
- law_node_stats.tsv             (law, unique_terms, total_occurrences, degree, weighted_degree)
- merge_lt_dict_v3_with_occ.tsv  (dictionary rows + file_containing + line + word_place)

Edge definition:
- Two laws are connected if they share ≥1 term_id.
- Edge weight = number of shared UNIQUE term_ids.
"""

from __future__ import annotations

import csv
import itertools
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# -----------------------------
# Paths (FIXED)
# -----------------------------
# This file lives in: v2/term_finder/build_law_network.py
# Project root is:    v2/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DICT_TSV = PROJECT_ROOT / "tsv-data" / "merge_lt_dict_v3.tsv"
OUTPUT_ROOT = PROJECT_ROOT / "term_finder" / "output"
OUT_DIR = PROJECT_ROOT / "tsv-data"


# -----------------------------
# Data structures
# -----------------------------
@dataclass
class TermRow:
    term_id: str
    leg_term: str
    desc: str
    pos_tag: str
    term_root: str


# -----------------------------
# TSV readers/writers
# -----------------------------
def read_merge_dict(tsv_path: Path) -> Tuple[Dict[str, str], Dict[str, TermRow]]:
    """
    Returns:
      - term_to_id: maps leg_term -> term_id (string)
      - id_to_row: maps term_id -> TermRow
    Notes:
      Your TSV sometimes includes an extra first column (e.g. 'Unnamed: 0').
      We handle both cases robustly by reading by header names.
    """
    if not tsv_path.exists():
        raise FileNotFoundError(f"Dictionary TSV not found: {tsv_path}")

    term_to_id: Dict[str, str] = {}
    id_to_row: Dict[str, TermRow] = {}

    with tsv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        # Normalize header names for safety
        headers = [h.strip() for h in (reader.fieldnames or [])]

        required = {"id", "leg_term", "desc", "pos_tag", "term_root"}
        if not required.issubset(set(headers)):
            raise ValueError(
                f"Dictionary TSV missing required columns. "
                f"Have={headers}, need={sorted(required)}"
            )

        for row in reader:
            term_id = str(row["id"]).strip()
            leg_term = str(row["leg_term"]).strip()
            desc = str(row["desc"]).strip()
            pos_tag = str(row["pos_tag"]).strip()
            term_root = str(row["term_root"]).strip()

            if not term_id or not leg_term or leg_term.lower() == "nan":
                continue

            term_to_id[leg_term] = term_id
            id_to_row[term_id] = TermRow(
                term_id=term_id,
                leg_term=leg_term,
                desc=desc,
                pos_tag=pos_tag,
                term_root=term_root,
            )

    return term_to_id, id_to_row


def write_tsv(path: Path, headers: List[str], rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(headers)
        w.writerows(rows)


# -----------------------------
# Parsing term_finder outputs
# -----------------------------
def _split_columns(line: str) -> List[str]:
    """
    The output files are fixed-width columns separated by multiple spaces.
    This splits into columns without needing exact widths.
    """
    # Split on 2+ spaces
    parts = []
    buf = ""
    space_run = 0
    for ch in line.rstrip("\n"):
        if ch == " ":
            space_run += 1
            if space_run >= 2:
                if buf.strip():
                    parts.append(buf.strip())
                buf = ""
                continue
        else:
            if space_run >= 2:
                space_run = 0
            else:
                space_run = 0
        buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def parse_term_output_file(txt_path: Path) -> Tuple[str, Dict[str, List[Tuple[int, int]]]]:
    """
    Returns:
      - law_file: e.g. "MNCLW00001.txt"
      - term_occ: dict term_str -> list of (line, word_place) occurrences

    Parsing logic:
    - Reads the "File:" header to get law file name
    - Parses the table where each term line contains:
        Term | Line(s) | Word Place(s)
      Continuation lines may have blank Term; they continue the previous term.
    - Line and Word Place lists are comma-separated; we pair them by index.
    """
    if not txt_path.exists():
        raise FileNotFoundError(f"Output file not found: {txt_path}")

    with txt_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    law_file = ""
    for ln in lines[:10]:
        if ln.startswith("File:"):
            law_file = ln.split("File:", 1)[1].strip()
            break
    if not law_file:
        raise ValueError(f"Could not read 'File:' header from {txt_path}")

    # Find the start of the table header
    # We look for a line that starts with "Term" and contains "Word Place"
    table_start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("Term") and "Word Place" in ln:
            table_start = i + 1
            break
    if table_start is None:
        # Some files might have 0 terms and no table rows; still OK
        return law_file, {}

    term_occ: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    current_term: Optional[str] = None

    for ln in lines[table_start:]:
        if not ln.strip():
            continue
        cols = _split_columns(ln)

        # Expected formats:
        # 1) ["term", "6, 7", "7, 16"]
        # 2) ["6, 7", "7, 16"]  (continuation; term omitted)
        if len(cols) == 3:
            term_str, line_str, wp_str = cols
            current_term = term_str
        elif len(cols) == 2 and current_term is not None:
            line_str, wp_str = cols
            term_str = current_term
        else:
            # Non-table noise or malformed; skip
            continue

        # Parse lists
        line_nums = [x.strip() for x in line_str.split(",") if x.strip()]
        wp_nums = [x.strip() for x in wp_str.split(",") if x.strip()]

        # Pair by index; if mismatch, use min length (defensive)
        k = min(len(line_nums), len(wp_nums))
        for j in range(k):
            try:
                L = int(line_nums[j])
                W = int(wp_nums[j])
                term_occ[term_str].append((L, W))
            except Exception:
                # Skip bad entries
                pass

    return law_file, term_occ


def pick_output_file(folder: Path) -> Optional[Path]:
    """
    Prefer trie-output.txt because you already validated AHO≈TRIE for most cases.
    Fallback to aho-output.txt if trie is missing.
    """
    trie = folder / "trie-output.txt"
    aho = folder / "aho-output.txt"
    if trie.exists():
        return trie
    if aho.exists():
        return aho
    return None


# -----------------------------
# Build law network
# -----------------------------
def main() -> None:
    # 1) Read dictionary
    term_to_id, id_to_row = read_merge_dict(DICT_TSV)

    # 2) Iterate all term_occur folders; collect term occurrences per law
    if not OUTPUT_ROOT.exists():
        raise FileNotFoundError(f"Output directory not found: {OUTPUT_ROOT}")

    law_to_term_occ: Dict[str, Dict[str, List[Tuple[int, int]]]] = {}
    # term_id -> law -> list[(line,wp)]
    termid_to_law_occ: Dict[str, Dict[str, List[Tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))

    term_folders = sorted([p for p in OUTPUT_ROOT.iterdir() if p.is_dir() and p.name.startswith("term_occur")])

    for folder in term_folders:
        txt_path = pick_output_file(folder)
        if txt_path is None:
            # No output files; skip
            continue

        law_file, term_occ = parse_term_output_file(txt_path)
        law_id = law_file.replace(".txt", "")  # MNCLW00001

        law_to_term_occ[law_id] = term_occ

        # Convert term string -> term_id using merge dictionary
        for term_str, occ_list in term_occ.items():
            term_id = term_to_id.get(term_str)
            if term_id is None:
                # term appears in outputs but not in merge_lt_dict_v3.tsv
                # Keep it out of network to stay consistent with your dictionary IDs.
                continue
            termid_to_law_occ[term_id][law_id].extend(occ_list)

    laws = sorted(law_to_term_occ.keys())

    # 3) Build law->set(term_id) and basic stats
    law_to_termids = {}
    law_to_total_occ = {}
    for law in laws:
        termids = set()
        total_occ = 0
        for term_str, occ_list in law_to_term_occ[law].items():
            tid = term_to_id.get(term_str)
            if tid is None:
                continue
            termids.add(tid)
            total_occ += len(occ_list)
        law_to_termids[law] = termids
        law_to_total_occ[law] = total_occ

    # 4) Build edges: for each term_id, connect all laws containing it
    edge_weight = defaultdict(int)  # (law_a, law_b) -> shared_unique_terms_count
    for term_id, law_map in termid_to_law_occ.items():
        law_list = sorted(law_map.keys())
        if len(law_list) < 2:
            continue
        for a, b in itertools.combinations(law_list, 2):
            edge_weight[(a, b)] += 1

    # 5) Write law_network_edges.tsv with Jaccard similarity
    edge_rows = []
    for (a, b), w in sorted(edge_weight.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
        A = law_to_termids.get(a, set())
        B = law_to_termids.get(b, set())
        union = len(A | B)
        jacc = (w / union) if union else 0.0
        edge_rows.append([a, b, str(w), f"{jacc:.6f}"])

    write_tsv(
        OUT_DIR / "law_network_edges.tsv",
        ["law_a", "law_b", "shared_terms", "jaccard"],
        edge_rows
    )

    # 6) Write law_term_presence.tsv: (law, term_id, occurrences_count)
    presence_rows = []
    for term_id, law_map in termid_to_law_occ.items():
        for law, occs in law_map.items():
            presence_rows.append([law, term_id, str(len(occs))])
    presence_rows.sort(key=lambda r: (r[0], int(r[1])))

    write_tsv(
        OUT_DIR / "law_term_presence.tsv",
        ["law", "term_id", "occurrences"],
        presence_rows
    )

    # 7) Node stats: degree and weighted degree
    degree = defaultdict(int)
    wdegree = defaultdict(int)
    for (a, b), w in edge_weight.items():
        degree[a] += 1
        degree[b] += 1
        wdegree[a] += w
        wdegree[b] += w

    node_rows = []
    for law in laws:
        node_rows.append([
            law,
            str(len(law_to_termids.get(law, set()))),
            str(law_to_total_occ.get(law, 0)),
            str(degree.get(law, 0)),
            str(wdegree.get(law, 0)),
        ])

    write_tsv(
        OUT_DIR / "law_node_stats.tsv",
        ["law", "unique_terms", "total_occurrences", "degree", "weighted_degree"],
        node_rows
    )

    # 8) Build dictionary-augmented TSV: one row per term_id with file list + line/wp maps
    # Format:
    # file_containing: "MNCLW00001, MNCLW00005, ..."
    # line: "MNCLW00001: 6, 7 | MNCLW00005: 114, 114, ..."
    # word_place: same format
    merged_rows = []
    for term_id, row in id_to_row.items():
        law_map = termid_to_law_occ.get(term_id, {})
        if law_map:
            files = sorted(law_map.keys())
            file_containing = ", ".join(files)

            # Aggregate per law
            line_parts = []
            wp_parts = []
            for law in files:
                occs = law_map[law]
                lines_only = [str(L) for (L, W) in occs]
                wps_only = [str(W) for (L, W) in occs]
                line_parts.append(f"{law}: " + ", ".join(lines_only))
                wp_parts.append(f"{law}: " + ", ".join(wps_only))

            line_str = " | ".join(line_parts)
            wp_str = " | ".join(wp_parts)
        else:
            file_containing = ""
            line_str = ""
            wp_str = ""

        merged_rows.append([
            row.term_id,
            row.leg_term,
            row.desc,
            row.pos_tag,
            row.term_root,
            file_containing,
            line_str,
            wp_str,
        ])

    merged_rows.sort(key=lambda r: int(r[0]) if r[0].isdigit() else r[0])

    write_tsv(
        OUT_DIR / "merge_lt_dict_v3_with_occ.tsv",
        ["id", "leg_term", "desc", "pos_tag", "term_root", "file_containing", "line", "word_place"],
        merged_rows
    )

    print("Done.")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Read dict:    {DICT_TSV}")
    print(f"Read outputs: {OUTPUT_ROOT}")
    print(f"Wrote edges:  {OUT_DIR / 'law_network_edges.tsv'}")
    print(f"Wrote nodes:  {OUT_DIR / 'law_node_stats.tsv'}")
    print(f"Wrote pres:   {OUT_DIR / 'law_term_presence.tsv'}")
    print(f"Wrote dict+:  {OUT_DIR / 'merge_lt_dict_v3_with_occ.tsv'}")


if __name__ == "__main__":
    main()
