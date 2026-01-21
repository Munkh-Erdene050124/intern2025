import re
from pathlib import Path
from collections import Counter


TERM_LINE_RE = re.compile(r"^(.{1,30})\s{2,}(.+?)\s{2,}(.+?)\s*$")


def parse_output_file(path: Path):
    """
      - found_terms_header: int or None
      - occurrences: Counter of (term, line, word_place) to preserve duplicates
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    found_terms_header = None

    m = re.search(r"Found terms:\s*(\d+)", text)
    if m:
        found_terms_header = int(m.group(1))

    lines = text.splitlines()

    occurrences = Counter()
    current_term = None

    in_table = False
    for ln in lines:
        if ln.strip().startswith("Term") and "Word Place" in ln:
            in_table = True
            continue
        if not in_table:
            continue
        if not ln.strip():
            continue

        # rows look like:
        # term<spaces> line-list<spaces> wordplace-list
        # or:
        # <blank term col> line-list<spaces> wordplace-list
        m = TERM_LINE_RE.match(ln)
        if not m:
            # ignore anything that doesn't match table rows
            continue

        term_col = m.group(1).rstrip()
        line_col = m.group(2).strip()
        wp_col = m.group(3).strip()

        if term_col.strip():
            current_term = term_col.strip()
        if not current_term:
            # malformed row; skip
            continue

        line_nums = [x.strip() for x in line_col.split(",") if x.strip()]
        wp_nums = [x.strip() for x in wp_col.split(",") if x.strip()]

        for line_id, wp in zip(line_nums, wp_nums):
            try:
                occurrences[(current_term, int(line_id), int(wp))] += 1
            except ValueError:
                # non-integer line/wp => skip
                continue

    return found_terms_header, occurrences


def compare_dir(term_dir: Path):
    aho_path = term_dir / "aho-output.txt"
    trie_path = term_dir / "trie-output.txt"

    if not aho_path.exists() or not trie_path.exists():
        return {
            "dir": term_dir.name,
            "status": "MISSING",
            "detail": f"missing: {'' if aho_path.exists() else 'aho-output.txt '} {'' if trie_path.exists() else 'trie-output.txt'}".strip()
        }

    aho_found, aho_occ = parse_output_file(aho_path)
    trie_found, trie_occ = parse_output_file(trie_path)

    # Compare header counts (informational)
    header_same = (aho_found == trie_found)

    # Compare occurrences exactly (including duplicates)
    if aho_occ == trie_occ and header_same:
        return {"dir": term_dir.name, "status": "OK", "detail": f"Found terms: {aho_found}"}

    # Build diffs
    only_in_aho = aho_occ - trie_occ
    only_in_trie = trie_occ - aho_occ

    # Show up to 10 diffs for readability
    def sample(counter: Counter, n=10):
        items = list(counter.items())[:n]
        return items

    detail_lines = []
    if not header_same:
        detail_lines.append(f"Header Found terms differ: aho={aho_found} trie={trie_found}")

    if only_in_aho:
        detail_lines.append(f"Only in AHO (sample): {sample(only_in_aho)}")
    if only_in_trie:
        detail_lines.append(f"Only in TRIE (sample): {sample(only_in_trie)}")

    return {"dir": term_dir.name, "status": "DIFF", "detail": " | ".join(detail_lines)}


def main():
    output_root = Path(__file__).parent / "output"

    term_dirs = sorted([p for p in output_root.iterdir() if p.is_dir() and p.name.startswith("term_occur")])

    if not term_dirs:
        print(f"No term_occur folders found under: {output_root}")
        return

    ok = 0
    diff = 0
    missing = 0

    for d in term_dirs:
        res = compare_dir(d)
        if res["status"] == "OK":
            ok += 1
        elif res["status"] == "DIFF":
            diff += 1
        else:
            missing += 1

        print(f"{res['dir']}: {res['status']} - {res['detail']}")

    print("\nSummary")
    print(f"OK:      {ok}")
    print(f"DIFF:    {diff}")
    print(f"MISSING: {missing}")
    print(f"TOTAL:   {len(term_dirs)}")


if __name__ == "__main__":
    main()
