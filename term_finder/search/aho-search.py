import sys
import os
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

    def search_text(self, words, root_func=None):
        """Search for phrases in a list of words, with optional root-based matching for last words."""
        transitions = self.transitions
        fails = self.fails
        outputs = self.outputs
        
        state = 0
        results = []
        for i, word in enumerate(words):
            # Standard AC transition logic
            while state > 0 and word not in transitions[state]:
                state = fails[state]
            
            # Check for exact match transition
            if word in transitions[state]:
                state = transitions[state][word]
                if outputs[state]:
                    for term in outputs[state]:
                        results.append((term, i))
            else:
                if root_func:
                    root_word = root_func(word)
                    if root_word != word:
                        # Temporary transition to check for terminal root match
                        temp_state = state
                        while temp_state > 0 and root_word not in transitions[temp_state]:
                            temp_state = fails[temp_state]
                        
                        if root_word in transitions[temp_state]:
                            next_temp = transitions[temp_state][root_word]
                            if outputs[next_temp]:
                                for term in outputs[next_temp]:
                                    results.append((term, i))
                
                state = 0 # Reset state as per standard AC on total mismatch
                
        return results


def load_dictionary(tsv_path):
    df = read_tsv(tsv_path)
    aho_corasick = WordAhoCorasick()
    # Mapping: lowercase variant phrase -> set of unique leg_terms to report
    variant_to_leg_terms = collections.defaultdict(set)
    
    for index, row in df.iterrows():
        try:
            leg_term = str(row['leg_term']).strip()
            
            if not leg_term or leg_term == 'nan':
                continue

            # Clean leg_term for insertion into the automaton
            _, clean_term_words = simple_tokenize(leg_term)
            cleaned_variant = " ".join(clean_term_words)
            
            aho_corasick.add_phrase(clean_term_words)
            variant_to_leg_terms[cleaned_variant].add(leg_term)
                
        except Exception:
            pass
            
    aho_corasick.build_automaton()
    return aho_corasick, variant_to_leg_terms, df


def analyze_file(file_path, aho_corasick, variant_to_leg_terms, df):
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return [], 0

    total_ac_time = 0
    
    # Process line by line
    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        raw_tokens, clean_tokens = simple_tokenize(line)
        
        # Original tokens for variant extraction
        words_original = line.split()

        # AC Search with timing
        t0 = time.time()
        # Find all matches, using get_root for last-word matching
        all_matches = aho_corasick.search_text(clean_tokens, root_func=get_root)
        t1 = time.time()
        total_ac_time += (t1 - t0)
        
        consumed_indices = set()
        
        # MWEs vs Singles
        mwes = [m for m in all_matches if len(m[0].split()) > 1]
        singles = [m for m in all_matches if len(m[0].split()) == 1]
        
        # Sort MWEs by length (descending) to prioritize longest matches
        mwes.sort(key=lambda x: len(x[0].split()), reverse=True)
        
        # Process MWEs
        for term_variant, end_idx in mwes:
            term_words = term_variant.split()
            term_len = len(term_words)
            start_idx = end_idx - term_len + 1
            
            # Check if index is already covered by a longer MWE
            is_covered = False
            for k in range(start_idx, end_idx + 1):
                if k in consumed_indices:
                    is_covered = True
                    break
            
            if not is_covered:
                if term_variant in variant_to_leg_terms:
                    leg_terms = variant_to_leg_terms[term_variant]
                    for lt in leg_terms:
                        results.append({
                            'term': lt,
                            'line': line_num,
                            'word_place': start_idx + 1
                        })
                    for k in range(start_idx, end_idx + 1):
                        consumed_indices.add(k)

        # Process Singles if not consumed
        for term_variant, end_idx in singles:
            if end_idx not in consumed_indices:
                if term_variant in variant_to_leg_terms:
                    leg_terms = variant_to_leg_terms[term_variant]
                    for lt in leg_terms:
                        results.append({
                            'term': lt,
                            'line': line_num,
                            'word_place': end_idx + 1
                        })

    return results, total_ac_time


def write_output(output_path, target_file, results, runtime):
    # Aggregate results
    agg_results = {}
    for res in results:
        term = res['term']
        if term not in agg_results:
            agg_results[term] = {'lines': [], 'word_places': []}
        
        agg_results[term]['lines'].append(str(res['line']))
        agg_results[term]['word_places'].append(str(res['word_place']))

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"File: {target_file}\n")
        f.write(f"Search Method: Aho-Corasick\n")
        f.write(f"Total runtime: {runtime:.6f}s\n")
        f.write(f"Found terms: {len(results)}\n")
        f.write("\n")
        f.write(f"{'Term':<30}  {'Line':<20}  {'Word Place':<20}\n")
        f.write("\n")
        
        for term, data in agg_results.items():
            lines = data['lines']
            wps = data['word_places']
            
            # Chunk output to avoid very long lines
            chunk_size = 4
            
            for i in range(0, len(lines), chunk_size):
                l_chunk = lines[i:i+chunk_size]
                w_chunk = wps[i:i+chunk_size]
                
                l_str = ", ".join(l_chunk)
                w_str = ", ".join(w_chunk)
                
                if i == 0:
                    f.write(f"{term:<30}  {l_str:<20}  {w_str:<20}\n")
                else:
                    f.write(f"{'':30}  {l_str:<20}  {w_str:<20}\n")


def main():
    # Parse command-line arguments
    if len(sys.argv) < 2:
        sys.exit(1)
    
    target_file = sys.argv[1]
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent  
    tsv_path = base_dir / 'tsv-data' / 'merge_lt_dict_v5.tsv'
    law_file_path = base_dir / 'law_txt_files' / target_file
    output_path = script_dir.parent / 'output' / 'aho-output.txt'
    
    # Verify input file exists
    if not law_file_path.exists():
        print(f"Error: Input file not found: {law_file_path}")
        sys.exit(1)
    
    # Load dictionary
    aho_corasick, variant_to_leg_terms, df = load_dictionary(str(tsv_path))
    
    start_time = time.time()
    results, ac_time = analyze_file(str(law_file_path), aho_corasick, variant_to_leg_terms, df)
    end_time = time.time()
    total_runtime = end_time - start_time
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_output(str(output_path), target_file, results, ac_time)
    
    # Report results
    print(f"Aho-Corasick Search Completed.")
    print(f"Total Runtime: {total_runtime:.6f} seconds")
    print(f"Search Time: {ac_time:.6f}s")


if __name__ == "__main__":
    main()
