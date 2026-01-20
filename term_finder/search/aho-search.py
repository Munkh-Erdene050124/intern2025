import sys
import time
import collections
from pathlib import Path
from utils import read_tsv, simple_tokenize, get_root


class WordAhoCorasick:

    def __init__(self):
        self.transitions = {0: {}}
        self.outputs = collections.defaultdict(set)
        self.fails = {}
        self.new_state = 0

    def add_phrase(self, phrase_words):
        state = 0
        for word in phrase_words:
            if word not in self.transitions[state]:
                self.new_state += 1
                self.transitions[state][word] = self.new_state
                self.transitions[self.new_state] = {}
            state = self.transitions[state][word]
        self.outputs[state].add(" ".join(phrase_words))

    def build_automaton(self):
        queue = collections.deque()
        for word, next_state in self.transitions[0].items():
            self.fails[next_state] = 0
            queue.append(next_state)

        while queue:
            r = queue.popleft()
            for word, s in self.transitions[r].items():
                queue.append(s)
                state = self.fails[r]
                while state > 0 and word not in self.transitions[state]:
                    state = self.fails[state]
                self.fails[s] = self.transitions[state].get(word, 0)
                self.outputs[s] |= self.outputs[self.fails[s]]

    def search_text(self, words):
        transitions = self.transitions
        fails = self.fails
        outputs = self.outputs

        state = 0
        results = []

        for i, word in enumerate(words):
            while state > 0 and word not in transitions[state]:
                state = fails[state]

            if word in transitions[state]:
                state = transitions[state][word]
                if outputs[state]:
                    for term in outputs[state]:
                        results.append((term, i))
            else:
                state = 0

        return results


def load_dictionary(tsv_path):
    df = read_tsv(tsv_path)
    aho_corasick = WordAhoCorasick()
    variant_to_leg_terms = collections.defaultdict(set)

    for _, row in df.iterrows():
        try:
            leg_term = str(row["leg_term"]).strip()
            if not leg_term or leg_term == "nan":
                continue

            _, clean_term_words = simple_tokenize(leg_term)

            #dictionary phrase inserted in root-token space.
            rooted_term_words = [get_root(w) for w in clean_term_words]
            cleaned_variant = " ".join(rooted_term_words)

            aho_corasick.add_phrase(rooted_term_words)
            variant_to_leg_terms[cleaned_variant].add(leg_term)

        except Exception:
            pass

    aho_corasick.build_automaton()
    return aho_corasick, variant_to_leg_terms, df


def analyze_file(file_path, aho_corasick, variant_to_leg_terms):
    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return [], 0

    total_ac_time = 0

    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        _, clean_tokens = simple_tokenize(line)

        #root tokens computed once per line, then searched exactly.
        root_tokens = [get_root(t) for t in clean_tokens]

        t0 = time.time()
        all_matches = aho_corasick.search_text(root_tokens)
        t1 = time.time()
        total_ac_time += (t1 - t0)

        consumed_indices = set()

        mwes = [m for m in all_matches if len(m[0].split()) > 1]
        singles = [m for m in all_matches if len(m[0].split()) == 1]

        mwes.sort(key=lambda x: len(x[0].split()), reverse=True)

        for term_variant, end_idx in mwes:
            term_words = term_variant.split()
            term_len = len(term_words)
            start_idx = end_idx - term_len + 1

            is_covered = any(k in consumed_indices for k in range(start_idx, end_idx + 1))
            if is_covered:
                continue

            if term_variant in variant_to_leg_terms:
                for lt in variant_to_leg_terms[term_variant]:
                    results.append({"term": lt, "line": line_num, "word_place": start_idx + 1})
                for k in range(start_idx, end_idx + 1):
                    consumed_indices.add(k)

        for term_variant, end_idx in singles:
            if end_idx in consumed_indices:
                continue
            if term_variant in variant_to_leg_terms:
                for lt in variant_to_leg_terms[term_variant]:
                    results.append({"term": lt, "line": line_num, "word_place": end_idx + 1})

    return results, total_ac_time


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
        f.write("Search Method: Aho-Corasick\n")
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
    output_path = script_dir.parent / "output" / "aho-output.txt"

    if not law_file_path.exists():
        print(f"Error: Input file not found: {law_file_path}")
        sys.exit(1)

    aho_corasick, variant_to_leg_terms, _ = load_dictionary(str(tsv_path))

    start_time = time.time()
    results, ac_time = analyze_file(str(law_file_path), aho_corasick, variant_to_leg_terms)
    end_time = time.time()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_output(str(output_path), target_file, results, ac_time)

    print("Aho-Corasick Search Completed.")
    print(f"Total Runtime: {end_time - start_time:.6f} seconds")
    print(f"Search Time: {ac_time:.6f}s")


if __name__ == "__main__":
    main()
