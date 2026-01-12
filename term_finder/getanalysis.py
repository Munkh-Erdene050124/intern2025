import pandas as pd
import collections
import time
import sys
import os


#Data Structures

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
        # Optimization: Local variables for faster lookup
        transitions = self.transitions
        fails = self.fails
        outputs = self.outputs
        
        state = 0
        results = []
        for i, word in enumerate(words):
            while state > 0 and word not in transitions[state]:
                state = fails[state]
            
            # Optimization avoid .get()
            current_transitions = transitions[state]
            if word in current_transitions:
                state = current_transitions[word]
            else:
                state = 0
                
            if outputs[state]:
                for term in outputs[state]:
                    results.append((term, i))
        return results

class MweTrieNode:
    def __init__(self, id, word):
        self.id = id
        self.word = word
        self.state = 0
        self.desc = ''
        self.children = {}

class MweTrie(object):
    def __init__(self):
        self.root = MweTrieNode([-1], "")
        self.aho_corasick = None

    def insert(self, multword, id):
        node = self.root
        found = self.is_found_mwe(multword)
        if found != None:
            for wrd in multword.split(" "):
                node = node.children[wrd]
            if node.id[len(node.id) - 1] == -2:
                node.id.pop()
            node.id.append(id)
            node.state = 1
        else:
            for wrd in multword.split(" "):
                if wrd not in node.children:
                    node.children[wrd] = MweTrieNode([-2], wrd)
                node = node.children[wrd]
            node.id = [id]
            node.state = 2

    def is_found_mwe(self, mwe):
        return self._find_mwe(self.root, mwe)

    def _find_mwe(self, node, mwe):
        for word in mwe.split(' '):
            if word not in node.children:
                return None
            node = node.children[word]
        return node
    
    def search(self, words):
        node = self.root
        t_node_list = []
        i = 0
        while i < len(words):
            x_word = words[i].lower().strip()
            if x_word in node.children:
                node = node.children[x_word]
                i += 1
            else:
                if node.id[0] != -2 and (node.state == 2 or node.state == 1):
                    t_node_list.append({'id': node.id, 'idx': i - 1})

                if node.id[0] == -1:
                    i += 1
                else:
                    node = self.root
        return t_node_list

class WordTrieNode:
    def __init__(self, id, char):
        self.id = id
        self.char = char
        self.counter = 0
        self.children = {}

class WordTrie(object):
    def __init__(self):
        self.root = WordTrieNode(-1, "")

    def insert(self, word, id):
        node = self.root
        for char in word:
            if char in node.children:
                node = node.children[char]
            else:
                new_node = WordTrieNode(0, char)
                node.children[char] = new_node
                node = new_node
        node.id = id
        node.counter += 1

    def dfs(self, node, prefix, output):
        if node.id != -1 and node.id != 0:
            output.append((prefix + node.char, node.id, node.counter))

        for child in node.children.values():
            self.dfs(child, prefix + node.char, output)

    def query(self, x):
        output = []
        node = self.root
        for char in x:
            if char in node.children:
                node = node.children[char]
            else:
                return []
        self.dfs(node, x[:-1], output)
        return sorted(output, key=lambda x: x[1], reverse=True)

# Helper Functions
def read_tsv(tsv_path):
    try:
        df = pd.read_csv(tsv_path, sep='\t')
        df.columns = df.columns.str.strip() 
        df = df.iloc[::-1]
        return df
    except Exception as e:
        print(f"Error reading TSV: {e}")
        sys.exit(1)

def create_automata(df):
    mwe_trie = MweTrie()
    word_trie = WordTrie()
    aho_corasick = WordAhoCorasick()
    # Mapping term back to IDs for easy lookup after AC search
    term_to_id = {}

    for index, row in df.iterrows():
        # Adjust column access based on observed file structure
        try:
            # Assuming standard columns from observation:
            term_id = row['id']
            leg_term = str(row['leg_term']).strip()
            term_root = str(row['term_root']).strip()
            
            if not leg_term or leg_term == 'nan':
                 continue

            if len(leg_term.split(' ')) > 1:
                cleaned_term = leg_term.strip()
                mwe_trie.insert(cleaned_term, term_id)
                aho_corasick.add_phrase(cleaned_term.split(' '))
                term_to_id[cleaned_term] = term_id
            else:
                word_trie.insert(leg_term.lower(), term_id)
                
        except KeyError as e:
            # Fallback if columns are unnamed
            pass
            
    aho_corasick.build_automaton()
    mwe_trie.aho_corasick = aho_corasick
    return mwe_trie, word_trie, term_to_id, df

def simple_tokenize(text):
    import re
    raw_tokens = text.split()
    clean_tokens = []

    # Suffix handling configuration
    # Тийн ялгалтууд болон олон тооны залгаасууд
    case_suffixes = [
        'ын', 'ийн', 'ны', 'ний',
        'д', 'т',
        'аас', 'ээс', 'оос', 'өөс',
        'аар', 'ээр', 'оор', 'өөр',
        'тай', 'тэй', 'той',
        'руу', 'рүү',
        'г', 'ийг', 'ыг'
    ]
    plural_suffixes = [
        'ууд', 'үүд', 'нууд', 'нүүд'
    ]
    
    # Combined and sorted by length (descending) for longest-suffix-first matching
    all_suffixes = sorted(case_suffixes + plural_suffixes, key=len, reverse=True)
    
    # Attempt to get valid terms set from the function attribute if available
    valid_terms = getattr(simple_tokenize, 'valid_terms', None)

    for t in raw_tokens:
        # Clean by removing punctuation from start and end
        clean_t = re.sub(r'^[^\w]+|[^\w]+$', '', t)
        
        # Normalize tokens by stripping suffixes
        current = clean_t
        
        while True:
            matched = False
            for suffix in all_suffixes:
                if current.endswith(suffix):
                    # Strip suffix
                    current = current[:-len(suffix)]
                    matched = True
                    # Restart loop to check for further suffixes (plural + case)
                    break 
            
            if not matched:
                break
        
        # If the original and stripped form are both valid, prefer original.
        if valid_terms and (clean_t in valid_terms) and (current in valid_terms):
            clean_tokens.append(clean_t)
        else:
            clean_tokens.append(current)

    return raw_tokens, clean_tokens

def analyze_file(file_path, mwe_trie, word_trie, term_to_id, df):
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return [], 0, 0

    total_ac_time = 0
    total_trie_time = 0
    # Process line by line
    for line_idx, line in enumerate(lines):
        line_num = line_idx + 1
        raw_tokens, clean_tokens = simple_tokenize(line)
        
        # Benchmarking
        # 1. Trie Search
        t0 = time.time()
        mwe_nodes = mwe_trie.search(clean_tokens)
        t1 = time.time()
        total_trie_time += (t1 - t0)
        
        # 2. AC Search
        t2 = time.time()
        matches_ac = mwe_trie.aho_corasick.search_text(clean_tokens)
        t3 = time.time()
        total_ac_time += (t3 - t2)
        
        term_map_by_id = df.set_index('id')['leg_term'].to_dict()
        consumed_indices = set()

        for node in mwe_nodes:
            mwe_ids = node['id']
            end_idx = node['idx']
            
            for m_id in mwe_ids:
                if m_id in term_map_by_id:
                    term_str = str(term_map_by_id[m_id])
                    
                    term_len = len(term_str.split()) 
                    start_idx = end_idx - term_len + 1

                    # Mark indices as consumed so single-word search skips them
                    for k in range(start_idx, end_idx + 1):
                        consumed_indices.add(k)

                    word_place = start_idx + 1 # 1-based output

                    results.append({
                        'term': term_str,
                        'line': line_num,
                        'word_place': word_place,
                        'type': 'MWE_Trie' 
                    })

        # 3. Single Word Search (WordTrie)
        for idx, token in enumerate(clean_tokens):
            if idx in consumed_indices:
                continue
            if not token: continue
            token_lower = token.lower()
            trie_matches = word_trie.query(token_lower)
            for tm in trie_matches:
                if tm[0] == token_lower:
                     results.append({
                        'term': tm[0],
                        'line': line_num,
                        'word_place': idx + 1,
                        'type': 'Single'
                    })
                     break

    return results, total_trie_time, total_ac_time

def main():
    # Configuration
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # intern/v2
    tsv_path = os.path.join(base_dir, 'tsv-data', 'merge_lt_dict_v5.tsv')
    
    # Input file
    target_file = 'MNCLW00019.txt' 
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    
    law_file_path = os.path.join(base_dir, 'law_txt_files', target_file)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output2.txt')

    df = read_tsv(tsv_path)
    mwe_trie, word_trie, term_to_id, df = create_automata(df)
    
    start_total = time.time()
    results, trie_time, ac_time = analyze_file(law_file_path, mwe_trie, word_trie, term_to_id, df)
    end_total = time.time()
    total_runtime = end_total - start_total

    print(f"Analysis Complete.")
    print(f"Total Runtime: {total_runtime:.6f} seconds")
    print(f"Trie Search Time: {trie_time:.6f}s")
    print(f"AC Search Time:   {ac_time:.6f}s")
    print(f"Found {len(results)} terms.")

    agg_results = {}
    for res in results:
        term = res['term']
        if term not in agg_results:
            agg_results[term] = {'lines': [], 'word_places': []}
        
        agg_results[term]['lines'].append(str(res['line']))
        agg_results[term]['word_places'].append(str(res['word_place']))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"File: {target_file}\n")
        f.write(f"Total runtime: {total_runtime:.6f}s\n")
        f.write(f"Search Times > Trie: {trie_time:.6f}s | AC: {ac_time:.6f}s\n")
        f.write("\n")
        f.write(f"{'Term':<30}  {'Line':<20}  {'Word Place':<20}\n")
        f.write("\n")
        
        for term, data in agg_results.items():
            lines = data['lines']
            wps = data['word_places']
            
            #Numbers that will be in a 1 line to avoid very long lines
            chunk_size = 4
            
            for i in range(0, len(lines), chunk_size):
                l_chunk = lines[i:i+chunk_size]
                w_chunk = wps[i:i+chunk_size]
                
                l_str = ", ".join(l_chunk)
                w_str = ", ".join(w_chunk)
                
                if i == 0:
                    f.write(f"{term:<30}  {l_str:<20}  {w_str:<20}\n")
                else:
                    f.write(f"{'':<30}  {l_str:<20}  {w_str:<20}\n")
    
    print(f"output.txt for full list.")

if __name__ == "__main__":
    main()
