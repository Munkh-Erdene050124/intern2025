import sys
import time
from pathlib import Path
from utils import read_tsv, simple_tokenize, get_root


class MweTrieNode:

    def __init__(self, roots=None, word=""):
        self.roots = roots if roots is not None else set()
        self.word = word
        self.state = 0
        self.children = {}


class MweTrie:

    def __init__(self):
        self.root = MweTrieNode(word="")

    def insert(self, multword, root):
        node = self.root
        for wrd in multword.split(" "):
            if wrd not in node.children:
                node.children[wrd] = MweTrieNode(word=wrd)
            node = node.children[wrd]
        node.roots.add(root)
        node.state = 1

    def search(self, words):
        results = []
        for i in range(len(words)):
            node = self.root
            for j in range(i, len(words)):
                word = words[j]
                #exact-only matching because tokens are rooted before search.
                if word in node.children:
                    node = node.children[word]
                    if node.roots:
                        results.append({"roots": node.roots, "idx": j, "len": j - i + 1})
                else:
                    break
        return results


class WordTrieNode:

    def __init__(self, char=""):
        self.roots = set()
        self.char = char
        self.children = {}


class WordTrie:

    def __init__(self):
        self.root = WordTrieNode(char="")

    def insert(self, word, root):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = WordTrieNode(char)
            node = node.children[char]
        node.roots.add(root)

    def query(self, x):
        #exact-only lookup because caller passes rooted tokens.
        node = self.root
        for char in x:
            if char in node.children:
                node = node.children[char]
            else:
                return set()
        return node.roots


def load_dictionary(tsv_path):
    df = read_tsv(tsv_path)
    mwe_trie = MweTrie()
    word_trie = WordTrie()

    for _, row in df.iterrows():
        try:
            leg_term = str(row["leg_term"]).strip()
            if not leg_term or leg_term == "nan":
                continue

            _, clean_term_words = simple_tokenize(leg_term)

            #insert dictionary into rooted token space.
            rooted_term_words = [get_root(w) for w in clean_term_words]
            cleaned_term = " ".join(rooted_term_words)

            if len(rooted_term_words) > 1:
                mwe_trie.insert(cleaned_term, leg_term)
            else:
                word_trie.insert(cleaned_term, leg_term)

        except Exception:
            pass

    return mwe_trie, word_trie, df


def analyze_file(file_path, mwe_trie, word_trie):
    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return [], 0

    total_trie_time = 0

    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        _, clean_tokens = simple_tokenize(line)

        #root tokens computed once; trie searches rooted tokens.
        root_tokens = [get_root(t) for t in clean_tokens]

        t0 = time.time()
        mwe_matches = mwe_trie.search(root_tokens)
        t1 = time.time()
        total_trie_time += (t1 - t0)

        consumed_indices = set()

        mwe_matches.sort(key=lambda x: x["len"], reverse=True)

        for match in mwe_matches:
            end_idx = match["idx"]
            term_len = match["len"]
            start_idx = end_idx - term_len + 1

            is_overlap = any(k in consumed_indices for k in range(start_idx, end_idx + 1))
            if is_overlap:
                continue

            for lt in match["roots"]:
                results.append({"term": lt, "line": line_num, "word_place": start_idx + 1})

            for k in range(start_idx, end_idx + 1):
                consumed_indices.add(k)

        t2 = time.time()
        for idx, token in enumerate(clean_tokens):
            if idx in consumed_indices:
                continue
            if not token:
                continue

            #single-word lookup uses rooted token.
            for lt in word_trie.query(root_tokens[idx]):
                results.append({"term": lt, "line": line_num, "word_place": idx + 1})
        t3 = time.time()
        total_trie_time += (t3 - t2)

    return results, total_trie_time


def write_output(output_path, target_file, results, runtime):
    agg_results = {}
    for res in results:
        term = res["term"]
        if term not in agg_results:
            agg_results[term] = {"lines": [], "word_places": []}
        agg_results[term]["lines"].append(str(res["line"]))
        agg_results[term]["word_places"].append(str(res["word_place"]))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"File: {target_file}\n")
        f.write("Search Method: Trie (MWE + Single-Word)\n")
        f.write(f"Total runtime: {runtime:.6f}s\n")
        f.write(f"Found terms: {len(results)}\n\n")
        f.write(f"{'Term':<30}  {'Line':<20}  {'Word Place':<20}\n\n")

        chunk_size = 4
        for term, data in agg_results.items():
            lines = data["lines"]
            wps = data["word_places"]

            for i in range(0, len(lines), chunk_size):
                l_str = ", ".join(lines[i:i+chunk_size])
                w_str = ", ".join(wps[i:i+chunk_size])

                if i == 0:
                    f.write(f"{term:<30}  {l_str:<20}  {w_str:<20}\n")
                else:
                    f.write(f"{'':30}  {l_str:<20}  {w_str:<20}\n")


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    target_file = sys.argv[1]

    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent
    tsv_path = base_dir / "tsv-data" / "merge_lt_dict_v5.tsv"
    law_file_path = base_dir / "law_txt_files" / target_file
    output_path = script_dir.parent / "output" / "trie-output.txt"

    if not law_file_path.exists():
        print(f"Error: Input file not found: {law_file_path}")
        sys.exit(1)

    mwe_trie, word_trie, _ = load_dictionary(str(tsv_path))

    start_time = time.time()
    results, trie_time = analyze_file(str(law_file_path), mwe_trie, word_trie)
    end_time = time.time()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_output(str(output_path), target_file, results, trie_time)

    print("Trie search completed.")
    print(f"Total Runtime: {end_time - start_time:.6f} seconds")
    print(f"Search Time: {trie_time:.6f}s")


if __name__ == "__main__":
    main()
