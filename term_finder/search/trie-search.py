import sys
import os
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

    def is_found_mwe(self, mwe):
        return self._find_mwe(self.root, mwe)

    def _find_mwe(self, node, mwe):
        for word in mwe.split(' '):
            if word not in node.children:
                return None
            node = node.children[word]
        return node
    
    def search(self, words):
        results = []
        for i in range(len(words)):
            node = self.root
            for j in range(i, len(words)):
                word = words[j]
                
                # Check exact match first
                if word in node.children:
                    node = node.children[word]
                    if node.roots:
                        results.append({'roots': node.roots, 'idx': j, 'len': j - i + 1})
                elif j == i or j > i: # Potential last word match
                    # If middle word doesn't match exactly, checking get_root is only allowed 
                    root_word = get_root(word)
                    if root_word != word and root_word in node.children:
                        target_node = node.children[root_word]
                        if target_node.roots: # It IS a terminal match
                            results.append({'roots': target_node.roots, 'idx': j, 'len': j - i + 1})
                    
                    # If it didn't match exactly and wasn't a root-based terminal match, 
                    # we must stop searching from this start index i.
                    break
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
        # Check exact match
        node = self.root
        found = True
        for char in x:
            if char in node.children:
                node = node.children[char]
            else:
                found = False
                break
        
        if found and node.roots:
            return node.roots
            
        # Try root-based match for single words
        root_x = get_root(x)
        if root_x != x:
            node = self.root
            for char in root_x:
                if char in node.children:
                    node = node.children[char]
                else:
                    return set()
            return node.roots
            
        return set()


def load_dictionary(tsv_path):
    df = read_tsv(tsv_path)
    mwe_trie = MweTrie()
    word_trie = WordTrie()
    
    for index, row in df.iterrows():
        try:
            leg_term = str(row['leg_term']).strip()
            
            if not leg_term or leg_term == 'nan':
                continue

            # Normalize for consistent matching
            _, clean_term_words = simple_tokenize(leg_term)
            cleaned_term = " ".join(clean_term_words)

            if len(clean_term_words) > 1:
                mwe_trie.insert(cleaned_term, leg_term)
            else:
                word_trie.insert(cleaned_term, leg_term)
                
        except Exception:
            pass
            
    return mwe_trie, word_trie, df


def analyze_file(file_path, mwe_trie, word_trie, df):
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return [], 0

    total_trie_time = 0
    term_map_by_id = df.set_index('id')['leg_term'].to_dict()
    
    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        raw_tokens, clean_tokens = simple_tokenize(line)
        
        t0 = time.time()
        mwe_matches = mwe_trie.search(clean_tokens)
        t1 = time.time()
        total_trie_time += (t1 - t0)
        
        consumed_indices = set()

        # Sort MWEs by length (desc) to prioritize longest match
        mwe_matches.sort(key=lambda x: x['len'], reverse=True)

        for match in mwe_matches:
            end_idx = match['idx']
            term_len = match['len']
            start_idx = end_idx - term_len + 1
            
            # Greedy: if any part of this MWE is consumed, skip
            is_overlap = False
            for k in range(start_idx, end_idx + 1):
                if k in consumed_indices:
                    is_overlap = True
                    break
            if is_overlap:
                continue

            leg_terms = match['roots'] # Now contains leg_term strings
            for lt in leg_terms:
                results.append({
                    'term': lt,
                    'line': line_num,
                    'word_place': start_idx + 1
                })
            
            # Mark indices as consumed
            for k in range(start_idx, end_idx + 1):
                consumed_indices.add(k)

        t2 = time.time()
        for idx, token in enumerate(clean_tokens):
            if idx in consumed_indices:
                continue
            if not token:
                continue
            
            leg_terms = word_trie.query(token)
            for lt in leg_terms:
                results.append({
                    'term': lt,
                    'line': line_num,
                    'word_place': idx + 1
                })
        t3 = time.time()
        total_trie_time += (t3 - t2)

    return results, total_trie_time


def write_output(output_path, target_file, results, runtime):
    agg_results = {}
    for res in results:
        term = res['term']
        if term not in agg_results:
            agg_results[term] = {'lines': [], 'word_places': []}
        
        agg_results[term]['lines'].append(str(res['line']))
        agg_results[term]['word_places'].append(str(res['word_place']))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"File: {target_file}\n")
        f.write(f"Search Method: Trie (MWE + Single-Word)\n")
        f.write(f"Total runtime: {runtime:.6f}s\n")
        f.write(f"Found terms: {len(results)}\n")
        f.write("\n")
        f.write(f"{'Term':<30}  {'Line':<20}  {'Word Place':<20}\n")
        f.write("\n")
        
        for term, data in agg_results.items():
            lines = data['lines']
            wps = data['word_places']
            
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
    if len(sys.argv) < 2:
        sys.exit(1)
    
    target_file = sys.argv[1]
    
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent
    tsv_path = base_dir / 'tsv-data' / 'merge_lt_dict_v5.tsv'
    law_file_path = base_dir / 'law_txt_files' / target_file
    output_path = script_dir.parent / 'output' / 'trie-output.txt'
    
    if not law_file_path.exists():
        print(f"Error: Input file not found: {law_file_path}")
        sys.exit(1)
    
    mwe_trie, word_trie, df = load_dictionary(str(tsv_path))
    
    start_time = time.time()
    results, trie_time = analyze_file(str(law_file_path), mwe_trie, word_trie, df)
    end_time = time.time()
    total_runtime = end_time - start_time
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_output(str(output_path), target_file, results, trie_time)
    
    print("Trie search completed.")
    print(f"Total Runtime: {total_runtime:.6f} seconds")
    print(f"Search Time: {trie_time:.6f}s")


if __name__ == "__main__":
    main()
