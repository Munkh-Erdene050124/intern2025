import sys
import subprocess
import shutil
from pathlib import Path


def run_for_file(target_file, idx, total, search_dir, output_root):
    print(f"[{idx}/{total}] Processing {target_file}")

    term_dir = output_root / f"term_occur{idx:05d}"
    term_dir.mkdir(parents=True, exist_ok=True)

    #AHO-CORASICK
    aho_script = search_dir / "aho-search.py"
    subprocess.run(
        [sys.executable, str(aho_script), target_file],
        cwd=str(search_dir),
        timeout=300
    )

    # Move aho-output.txt
    aho_out = output_root / "aho-output.txt"
    if aho_out.exists():
        shutil.move(str(aho_out), str(term_dir / "aho-output.txt"))
    else:
        print("WARNING: aho-output.txt not found")

    #TRIE
    trie_script = search_dir / "trie-search.py"
    subprocess.run(
        [sys.executable, str(trie_script), target_file],
        cwd=str(search_dir),
        timeout=300
    )

    # Move trie-output.txt
    trie_out = output_root / "trie-output.txt"
    if trie_out.exists():
        shutil.move(str(trie_out), str(term_dir / "trie-output.txt"))
    else:
        print("WARNING: trie-output.txt not found")


def main():
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    law_dir = base_dir / "law_txt_files"
    search_dir = script_dir / "search"
    output_root = script_dir / "output"

    output_root.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(law_dir.glob("MNCLW*.txt"))
    total = len(txt_files)

    print(f"Found {total} MNCLW files")

    for idx, law_file in enumerate(txt_files, start=1):
        run_for_file(law_file.name, idx, total, search_dir, output_root)


if __name__ == "__main__":
    main()
