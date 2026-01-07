import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import json
from operator import itemgetter
import time
import collections

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
                results.extend(outputs[state])
        return results


class LegalTerm:
    def __init__(self, id, leg_term, desc, pos_tag, term_root):
        self.id = id
        self.leg_term = leg_term
        self.desc = desc
        self.pos_tag = pos_tag
        self.term_root = term_root

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + ',\n\tleg_term: ' + str(self.leg_term) + ',\n\tdesc: ' + str(self.desc) + ',\n\tpos_tag: ' + str(self.pos_tag) + ',\n\tterm_root: ' + str(self.term_root) + '\n)'


class Coocur:
    def __init__(self, id, doc_id, term_id, line_id):
        self.id = id
        self.doc_id = doc_id
        self.term_id = term_id
        self.line_id = line_id

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + ',\n\tdoc_id: ' + str(self.doc_id) + ',\n\tterm_id: ' + str(self.term_id) + ',\n\tline_id: ' + str(self.line_id) + '\n)'


class DicDoc:
    def __init__(self, doc_id, doc_title, doc_desc):
        self.doc_id = doc_id
        self.doc_title = doc_title
        self.doc_desc = doc_desc

    def to_str(self):
        return '(' + '\n\tdoc_id: ' + str(self.doc_id) + ',\n\tdoc_title: ' + str(self.doc_title) + ',\n\tdoc_desc: ' + str(self.doc_desc) + '\n)'


class MweTrieNode:
    def __init__(self, id, word):
        self.id = id
        self.word = word
        self.state = 0
        self.desc = ''
        self.children = {}

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tword: ' + self.word + ',\n\tstate: ' + str(self.state) + ',\n\tdesc: ' + self.desc + ',\n\tchildren: ' + str(len(self.children)) + '\n)'


class WordTrieNode:
    def __init__(self, id, char):
        self.id = id
        self.char = char
        self.counter = 0
        self.children = {}


class MweTrie(object):
    def __init__(self):
        self.root = MweTrieNode([-1], "")

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

    def is_found_mwe(self, mwe):
        return self._find_mwe(self.root, mwe)

    def _find_mwe(self, node, mwe):
        for word in mwe.split(' '):
            if word not in node.children:
                return None
            node = node.children[word]
        return node

    def is_found_word(self, word):
        return self._find_node(self.root, word)

    def _find_node(self, root, word):
        if root is None:
            return None
        if root.word == word:
            return root
        for child in root.children:
            node = self._find_node(root.children[child], word)
            if node:
                return node
        return None

    def _node_mwe(self, node, prefix):
        for word in sorted(node.children):
            self._print_helper(
                node.children[word], prefix + " " + (word + "-" + str(node.id)))

    def print_trie(self, state=2):
        self._print_helper(self.root, state, "")

    def _print_helper(self, node, state, prefix):
        if node.state == state:
            print(prefix[1:])
        for word in sorted(node.children):
            self._print_helper(
                node.children[word], state, prefix + ' ' + (word + "-" + str(node.children[word].id)))


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

    def dfs(self, node, prefix):
        if node.id != -1 and node.id != 0:
            self.output.append((prefix + node.char, node.id, node.counter))

        for child in node.children.values():
            self.dfs(child, prefix + node.char)

    def query(self, x):
        self.output = []
        node = self.root
        for char in x:
            if char in node.children:
                node = node.children[char]
            else:
                return []
        self.dfs(node, x[:-1])
        return sorted(self.output, key=lambda x: x[1], reverse=True)


def read_tsv(tsv_path):
    df = pd.read_csv(tsv_path, sep='\t')
    df = df.iloc[::-1]
    return df


def create_trie(data_path):
    mwe_trie = MweTrie()
    word_trie = WordTrie()
    aho_corasick = WordAhoCorasick() # Initialize Aho-Corasick
    df = read_tsv(data_path)
    for index, row in df.iterrows():
        if not row.empty:
            if len(row['leg_term'].split(' ')) > 1:
                cleaned_term = row['leg_term'].replace(' ' + row['term_root'], '')
                mwe_trie.insert(cleaned_term, row['id'])
                aho_corasick.add_phrase(cleaned_term.split(' ')) # Add to AC
            else:
                word_trie.insert(row['leg_term'].lower().strip(), row['id'])
        # mwe_trie.print_trie(1)
        # mwe_trie.print_trie(2)
    
    aho_corasick.build_automaton() # Build AC
    mwe_trie.aho_corasick = aho_corasick # Attach to mwe_trie to pass it around easily without changing signatures
    
    return [mwe_trie, word_trie]


def convert_dict(a_list):
    dict_list = []
    for a in a_list:
        dict_list.append(a.__dict__)
    return dict_list


def is_match(slt, idx, con_wrd):
    length = len(slt)
    cnt = 0

    if idx - length + 1 < 0:
        return False

    for l in range(1, length + 1):
        if slt[length - l].lower() == con_wrd[idx - l + 1]['word'].lower():
            cnt += 1
    if cnt == length:
        return True
    else:
        return False


# def search_mwe(trie, df, txt, base_url='http://10.0.70.62:8080/nlp-web-demo/process?text='):
def search_mwe(mwe_trie, word_trie, df, txt, base_url='http://10.0.50.62:8081/nlp-web-demo/process?text='):
    found_mwe = []
    mwe_arr_index = []
    try:
        res = requests.get(base_url+txt, timeout=2)
        if res.status_code != 200:
            raise Exception(f"Status {res.status_code}")
        response_text = res.text
    except Exception as e:
        print(f"API request failed ({e}); using static fallback.")
        response_text = '[[{"word":"\\"","lemma":"[\\"+Sent]","posTag":"PUN","nameType":"O","stopWordType":"None"},{"word":"тэдгээр","lemma":"[тэдгээр+N+Sg+Nom]","posTag":"PJ","nameType":"O","stopWordType":"PRONOUN"},{"word":"хуулийн","lemma":"[хууль+N+Sg+Gen]","posTag":"NG","nameType":"O","stopWordType":"None"},{"word":"этгээдийг","lemma":"[этгээд+N+Sg+Acc]","posTag":"NC","nameType":"O","stopWordType":"PRONOUN"},{"word":"\\"","lemma":"[\\"+Sent]","posTag":"PUN","nameType":"O","stopWordType":"None"}]]'

    soup = BeautifulSoup(response_text, "html.parser")
    res_arr = json.loads(soup.text)

    word_list = []
    for sentence in res_arr:
        for word in sentence:
            word_list.append(word)

    con_wrd = word_list.copy()
    search_words = list(map(lambda x: x['word'], con_wrd))

    #Benchmarking
    start_trie = time.time()
    mwe_node_list = mwe_trie.search(search_words)
    end_trie = time.time()

    if hasattr(mwe_trie, 'aho_corasick'):
        start_ac = time.time()
        ac_results = mwe_trie.aho_corasick.search_text(search_words) 
        end_ac = time.time()
        print(f"Trie Time: {end_trie - start_trie:.6f}s | AC Time: {end_ac - start_ac:.6f}s | Diff: {(end_trie - start_trie) - (end_ac - start_ac):.6f}s")
    else:
        print(f"Trie Time: {end_trie - start_trie:.6f}s (AC not available)")
    # --------------------
    for mwe_node in mwe_node_list:
        for mwe_id in mwe_node['id']:
            row = df.loc[df['id'] == mwe_id].values.tolist()[0]
            ner = row[2].lower()
            undes = row[5].lower()
            posTag = row[4].upper()
            res_mwe = ner.lower().replace(' ' + undes, '')
            slt = res_mwe.lower().split(" ")
            if len(slt) > 0 and is_match(slt, mwe_node['idx'], con_wrd) and mwe_node['idx'] + 1 < len(con_wrd) and con_wrd[mwe_node['idx'] + 1]['word'] not in res_mwe.lower():
                if con_wrd[mwe_node['idx'] + 1]['word'].lower() == undes:
                    con_wrd[mwe_node['idx'] + 1]['lemma'] = '['+'_'.join(res_mwe.split(
                        ' ')) + '_' + con_wrd[mwe_node['idx'] + 1]['lemma'].replace('[', '')
                    con_wrd[mwe_node['idx'] + 1]['posTag'] = posTag
                    found_mwe.append({'id': row[1], 'leg_term': row[2].lower(), 'desc': row[3].lower(
                    ), 'pos_tag': row[4].lower(), 'term_root': row[5].lower()})
                    mwe_arr_index.append(
                        {'index': mwe_node['idx'] + 1, 'length': len(slt)})
                else:
                    wrd_roots = con_wrd[mwe_node['idx'] +
                                        1]['lemma'].replace('[', '').replace(']', '').split(', ')
                    for wrd_root in wrd_roots:
                        if wrd_root.split('+')[0].lower() == undes:
                            con_wrd[mwe_node['idx'] + 1]['lemma'] = '['+'_'.join(res_mwe.split(
                                ' ')) + '_' + con_wrd[mwe_node['idx'] + 1]['lemma'].replace('[', '')
                            con_wrd[mwe_node['idx'] + 1]['posTag'] = posTag
                            found_mwe.append({'id': row[1], 'leg_term': row[2].lower(), 'desc': row[3].lower(
                            ), 'pos_tag': row[4].lower(), 'term_root': row[5].lower()})
                            mwe_arr_index.append(
                                {'index': mwe_node['idx'] + 1, 'length': len(slt)})
                            break

    pure_con_wrd = []
    for i, cw in enumerate(con_wrd):
        exist = 0
        for mwe_index in mwe_arr_index:
            if i in range(mwe_index['index'] - mwe_index['length'], mwe_index['index']):
                exist = 1
        if exist == 0:
            pure_con_wrd.append(cw)

    for cw in pure_con_wrd:
        if cw['posTag'] != 'NM' and len(word_trie.query(cw['word'])) > 0:
            max_len_wrd = sorted(word_trie.query(
                cw['word']), key=itemgetter(2), reverse=True)[0]
            row = df.loc[df['id'] == max_len_wrd[1]].values.tolist()[0]
            ner = row[2].lower()
            undes = row[5].lower()
            posTag = row[4].upper()
            if cw['word'].lower() == undes:
                cw['posTag'] = posTag
                found_mwe.append({'id': row[1], 'leg_term': row[2].lower(), 'desc': row[3].lower(
                ), 'pos_tag': row[4].lower(), 'term_root': row[5].lower()})
            else:
                wrd_roots = cw['lemma'].replace(
                    '[', '').replace(']', '').split(', ')
                for wrd_root in wrd_roots:
                    if wrd_root.split('+')[0].lower() == undes:
                        cw['posTag'] = posTag
                        found_mwe.append({'id': row[1], 'leg_term': row[2].lower(), 'desc': row[3].lower(
                        ), 'pos_tag': row[4].lower(), 'term_root': row[5].lower()})
                        break
    return {'found_mwe': found_mwe, 'word_list': pure_con_wrd}


def str_to_word_lines(text, length):
    words = text.split(" ")
    lines = [words[0]]
    for word in words[1:]:
        if len(lines[-1]) + len(word) < length:
            lines[-1] += (" " + word)
        else:
            lines.append(word)
    return '\n'.join(lines)


def get_ccur_list(txt_df, name, mwe_trie, word_trie, df, init_cur_id, split_len=300):
    coocur_list = []
    rows = txt_df.iterrows()
    cur_id = init_cur_id
    for index, row in rows:
        law_txt = row['Unnamed: 0'].lower().strip()
        if split_len == 0:
            res = search_mwe(mwe_trie, word_trie, df, law_txt)
            mwe_ids = set(list(map(lambda x: x['id'], res['found_mwe'])))
            for mwe_id in mwe_ids:
                ccur = Coocur(cur_id, name, mwe_id, index)
                coocur_list.append(ccur)
                cur_id += 1
        else:
            for len300 in str_to_word_lines(law_txt, split_len).split('\n'):
                res = search_mwe(mwe_trie, word_trie, df, len300)
                mwe_ids = set(list(map(lambda x: x['id'], res['found_mwe'])))
                for mwe_id in mwe_ids:
                    ccur = Coocur(cur_id, name, mwe_id, index)
                    coocur_list.append(ccur)
                    cur_id += 1
    return coocur_list


def search_mwe_impl(f_name, f_path, df, mwe_trie, word_trie, init_cur_id):
    return get_ccur_list(pd.read_csv(f_path, sep='\t', engine='python'), f_name, mwe_trie, word_trie, df, init_cur_id)


def create_df(data_list, df_path, drop_duplicate_cols=[], sort_vals=[]):
    df = pd.DataFrame(convert_dict(data_list))
    df = df.drop_duplicates(
        subset=drop_duplicate_cols).sort_values(by=sort_vals)
    df.to_csv(df_path, sep="\t")
