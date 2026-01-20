import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
from operator import itemgetter


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
        if found is not None:
            for wrd in multword.split(" "):
                node = node.children[wrd]
            if node.id and node.id[-1] == -2:
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
            x_word = str(words[i]).lower().strip()
            if x_word in node.children:
                node = node.children[x_word]
                i += 1
            else:
                # If current node is terminal-ish, emit
                if node.id and node.id[0] != -2 and (node.state == 2 or node.state == 1):
                    t_node_list.append({'id': node.id, 'idx': i - 1})

                # If we are at root, just advance; else reset to root
                if node.id and node.id[0] == -1:
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
    df = read_tsv(data_path)

    required_cols = {'id', 'leg_term', 'term_root'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"TSV is missing required columns: {missing}. Found columns: {list(df.columns)}")

    for _, row in df.iterrows():
        if row is None or row.empty:
            continue

        leg_term = str(row['leg_term']).lower().strip()
        term_root = str(row['term_root']).lower().strip() if pd.notna(row['term_root']) else ""

        if not leg_term:
            continue

        # Multi-word term
        if len(leg_term.split()) > 1:
            mwe_key = leg_term
            if term_root and mwe_key.endswith(" " + term_root):
                mwe_key = mwe_key[: -(len(term_root) + 1)].strip()

            if mwe_key:
                mwe_trie.insert(mwe_key, int(row['id']))
        else:
            word_trie.insert(leg_term, int(row['id']))

    return [mwe_trie, word_trie]


def convert_dict(a_list):
    return [a.__dict__ for a in a_list]


def is_match(slt, idx, con_wrd):
    length = len(slt)
    if idx - length + 1 < 0:
        return False

    for l in range(1, length + 1):
        if slt[length - l].lower() != str(con_wrd[idx - l + 1]['word']).lower():
            return False
    return True


def search_mwe(
    mwe_trie,
    word_trie,
    df,
    txt,
    base_url='http://10.0.50.62:8081/nlp-web-demo/process?text=',
    timeout_seconds=20
):
    found_mwe = []

    if txt is None:
        return {'found_mwe': [], 'word_list': []}

    txt = str(txt).strip()
    if not txt:
        return {'found_mwe': [], 'word_list': []}

    # Request NLP analysis
    try:
        res = requests.get(base_url + txt, timeout=timeout_seconds)
    except requests.RequestException as e:
        # Network / timeout / connection issue
        print(f"[NLP API ERROR] {e}")
        return {'found_mwe': [], 'word_list': []}

    if res.status_code != 200:
        print(f"[NLP API STATUS] {res.status_code}")
        return {'found_mwe': [], 'word_list': []}

    soup = BeautifulSoup(res.text, "html.parser")
    try:
        res_arr = json.loads(soup.text)
    except json.JSONDecodeError:
        print("[NLP API PARSE] JSON decode failed")
        return {'found_mwe': [], 'word_list': []}

    # Flatten to a single list of token dicts
    word_list = []
    for sentence in res_arr:
        for word in sentence:
            word_list.append(word)

    con_wrd = word_list.copy()

    # MWE scan (based on surface 'word' field)
    mwe_node_list = mwe_trie.search(list(map(lambda x: x.get('word', ''), con_wrd)))

    mwe_arr_index = []
    for mwe_node in mwe_node_list:
        for mwe_id in mwe_node['id']:
            # Locate row in df by numeric id
            rows = df.loc[df['id'] == mwe_id].values.tolist()
            if not rows:
                continue
            row = rows[0]

            try:
                ner = str(row[2]).lower()
                undes = str(row[5]).lower()
                posTag = str(row[4]).upper()
            except Exception:
                continue

            res_mwe = ner.lower().replace(' ' + undes, '')
            slt = res_mwe.lower().split()

            if len(slt) == 0:
                continue
            if mwe_node['idx'] + 1 >= len(con_wrd):
                continue

            next_word = str(con_wrd[mwe_node['idx'] + 1].get('word', '')).lower()
            if next_word and next_word in res_mwe.lower():
                continue

            if is_match(slt, mwe_node['idx'], con_wrd):
                # If the next surface word equals term_root, tag it
                if next_word == undes:
                    con_wrd[mwe_node['idx'] + 1]['lemma'] = (
                        '[' + '_'.join(res_mwe.split(' ')) + '_' +
                        str(con_wrd[mwe_node['idx'] + 1].get('lemma', '')).replace('[', '')
                    )
                    con_wrd[mwe_node['idx'] + 1]['posTag'] = posTag

                    found_mwe.append({
                        'id': row[1],
                        'leg_term': str(row[2]).lower(),
                        'desc': str(row[3]).lower(),
                        'pos_tag': str(row[4]).lower(),
                        'term_root': str(row[5]).lower()
                    })
                    mwe_arr_index.append({'index': mwe_node['idx'] + 1, 'length': len(slt)})
                else:
                    # Otherwise check lemma roots list
                    lemma_val = str(con_wrd[mwe_node['idx'] + 1].get('lemma', ''))
                    wrd_roots = lemma_val.replace('[', '').replace(']', '').split(', ')
                    for wrd_root in wrd_roots:
                        if wrd_root.split('+')[0].lower() == undes:
                            con_wrd[mwe_node['idx'] + 1]['lemma'] = (
                                '[' + '_'.join(res_mwe.split(' ')) + '_' +
                                str(con_wrd[mwe_node['idx'] + 1].get('lemma', '')).replace('[', '')
                            )
                            con_wrd[mwe_node['idx'] + 1]['posTag'] = posTag

                            found_mwe.append({
                                'id': row[1],
                                'leg_term': str(row[2]).lower(),
                                'desc': str(row[3]).lower(),
                                'pos_tag': str(row[4]).lower(),
                                'term_root': str(row[5]).lower()
                            })
                            mwe_arr_index.append({'index': mwe_node['idx'] + 1, 'length': len(slt)})
                            break

    # Remove tokens covered by MWEs
    pure_con_wrd = []
    for i, cw in enumerate(con_wrd):
        covered = False
        for mwe_index in mwe_arr_index:
            if i in range(mwe_index['index'] - mwe_index['length'], mwe_index['index']):
                covered = True
                break
        if not covered:
            pure_con_wrd.append(cw)

    # Single-word scan on remaining tokens
    for cw in pure_con_wrd:
        w = str(cw.get('word', '')).lower().strip()
        if not w:
            continue
        if cw.get('posTag') == 'NM':
            continue

        q = word_trie.query(w)
        if len(q) == 0:
            continue

        max_len_wrd = sorted(q, key=itemgetter(2), reverse=True)[0]
        rows = df.loc[df['id'] == max_len_wrd[1]].values.tolist()
        if not rows:
            continue
        row = rows[0]

        try:
            undes = str(row[5]).lower()
            posTag = str(row[4]).upper()
        except Exception:
            continue

        if w == undes:
            cw['posTag'] = posTag
            found_mwe.append({
                'id': row[1],
                'leg_term': str(row[2]).lower(),
                'desc': str(row[3]).lower(),
                'pos_tag': str(row[4]).lower(),
                'term_root': str(row[5]).lower()
            })
        else:
            lemma_val = str(cw.get('lemma', ''))
            wrd_roots = lemma_val.replace('[', '').replace(']', '').split(', ')
            for wrd_root in wrd_roots:
                if wrd_root.split('+')[0].lower() == undes:
                    cw['posTag'] = posTag
                    found_mwe.append({
                        'id': row[1],
                        'leg_term': str(row[2]).lower(),
                        'desc': str(row[3]).lower(),
                        'pos_tag': str(row[4]).lower(),
                        'term_root': str(row[5]).lower()
                    })
                    break

    return {'found_mwe': found_mwe, 'word_list': pure_con_wrd}


def str_to_word_lines(text, length):
    words = str(text).split(" ")
    if not words:
        return ""
    lines = [words[0]]
    for word in words[1:]:
        if len(lines[-1]) + len(word) < length:
            lines[-1] += (" " + word)
        else:
            lines.append(word)
    return '\n'.join(lines)


def get_ccur_list(lines, name, mwe_trie, word_trie, df, init_cur_id, split_len=300):
    coocur_list = []
    cur_id = init_cur_id

    for index, law_txt in enumerate(lines):
        law_txt = str(law_txt).lower().strip()
        if not law_txt:
            continue

        if split_len == 0:
            chunks = [law_txt]
        else:
            chunks = str_to_word_lines(law_txt, split_len).split('\n')

        for chunk in chunks:
            res = search_mwe(mwe_trie, word_trie, df, chunk)
            mwe_ids = set(map(lambda x: x['id'], res['found_mwe']))
            for mwe_id in mwe_ids:
                coocur_list.append(Coocur(cur_id, name, mwe_id, index))
                cur_id += 1

    return coocur_list


def search_mwe_impl(f_name, f_path, df, mwe_trie, word_trie, init_cur_id, encoding="utf-8"):
    if not os.path.exists(f_path):
        return []

    try:
        with open(f_path, "r", encoding=encoding, errors="replace") as f:
            lines = [line.strip() for line in f if line.strip()]
    except OSError as e:
        print(f"[FILE ERROR] {f_path}: {e}")
        return []

    return get_ccur_list(lines, f_name, mwe_trie, word_trie, df, init_cur_id)


def create_df(data_list, df_path, drop_duplicate_cols=None, sort_vals=None):
    drop_duplicate_cols = drop_duplicate_cols or []
    sort_vals = sort_vals or []

    df = pd.DataFrame(convert_dict(data_list))
    if drop_duplicate_cols:
        df = df.drop_duplicates(subset=drop_duplicate_cols)
    if sort_vals:
        df = df.sort_values(by=sort_vals)

    df.to_csv(df_path, sep="\t", index=False)
