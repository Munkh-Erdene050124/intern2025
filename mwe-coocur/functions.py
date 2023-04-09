import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import time
import random


class LegalTerm:
    def __init__(self, id, leg_term, desc, pos_tag, term_root):
        self.id = id
        self.leg_term = leg_term
        self.desc = desc
        self.pos_tag = pos_tag
        self.term_root = term_root

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tleg_term: ' + str(self.leg_term) + ',\n\tdesc: ' + str(self.desc) + ',\n\tpos_tag: ' + str(self.pos_tag) + ',\n\tterm_root: ' + str(self.term_root) + '\n)'


class Coocur:
    def __init__(self, id, doc_id, term_id):
        self.id = id
        self.doc_id = doc_id
        self.term_id = term_id

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tdoc_id: ' + str(self.doc_id) + ',\n\tterm_id: ' + str(self.term_id) + '\n)'


class DicDoc:
    def __init__(self, doc_id, doc_title, doc_desc):
        self.doc_id = doc_id
        self.doc_title = doc_title
        self.doc_desc = doc_desc

    def to_str(self):
        return '(' + '\n\tdoc_id: ' + str(self.doc_id) + '\n\tdoc_title: ' + str(self.doc_title) + '\n\tdoc_desc: ' + str(self.doc_desc) + '\n)'


class NewTrieNode:
    def __init__(self, id, word):
        self.id = id
        self.word = word
        self.state = 0
        self.desc = ''
        self.children = {}

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tword: ' + self.word + ',\n\tstate: ' + str(self.state) + ',\n\tdesc: ' + self.desc + ',\n\tchildren: ' + str(len(self.children)) + '\n)'


class NewTrie(object):
    def __init__(self):
        self.root = NewTrieNode([-1], "")

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
                    node.children[wrd] = NewTrieNode([-2], wrd)
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


def read_tsv(tsv_path):
    df = pd.read_csv(tsv_path, sep='\t')
    df = df.iloc[::-1]
    return df


def create_trie(data_path):
    new_trie = NewTrie()
    df = read_tsv(data_path)
    for row in df.iterrows():
        new_trie.insert(row[1]['leg_term'].replace(
            ' ' + row[1]['term_root'], ''), row[1]['id'])
    # new_trie.print_trie(1)
    return new_trie


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
def search_mwe(trie, df, txt, base_url='http://172.104.34.197/nlp-web-demo/process?text='):
    res = requests.get(base_url+txt)
    if res.status_code != 200:
        print(res.status_code)
    soup = BeautifulSoup(res.text, "html.parser")
    res_arr = json.loads(soup.text)

    word_list = []
    for sentence in res_arr:
        for word in sentence:
            word_list.append(word)

    found_mwe = []
    con_wrd = word_list.copy()
    mwe_node_list = trie.search(list(map(lambda x: x['word'], con_wrd)))
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
                            break
    return found_mwe


def str_to_word_lines(text, length):
    words = text.split(" ")
    lines = [words[0]]
    for word in words[1:]:
        if len(lines[-1]) + len(word) < length:
            lines[-1] += (" " + word)
        else:
            lines.append(word)
    return '\n'.join(lines)


def get_ccur_list(txt_df, name, trie, df, init_cur_id, split_len=300):
    coocur_list = []
    rows = txt_df.iterrows()
    cur_id = init_cur_id
    for row in rows:
        law_txt = row[1]['Unnamed: 0'].lower().strip()
        if split_len == 0:
            found_mwe_list = search_mwe(trie, df, law_txt)
            mwe_ids = set(list(map(lambda x: x['id'], found_mwe_list)))
            for mwe_id in mwe_ids:
                ccur = Coocur(cur_id, name, mwe_id)
                coocur_list.append(ccur)
        else:
            for len100 in str_to_word_lines(law_txt, split_len).split('\n'):
                found_mwe_list = search_mwe(trie, df, len100)
                mwe_ids = set(list(map(lambda x: x['id'], found_mwe_list)))
                for mwe_id in mwe_ids:
                    ccur = Coocur(cur_id, name, mwe_id)
                    coocur_list.append(ccur)
        cur_id += 1
    return coocur_list


def search_mwe_impl(f_name, f_path, df, trie, init_cur_id):
    return get_ccur_list(pd.read_csv(f_path, sep='/t'), f_name, trie, df, init_cur_id)


def create_df(data_list, df_path, drop_duplicate_cols=[], sort_vals=[]):
    df = pd.DataFrame(convert_dict(data_list))
    df = df.drop_duplicates(
        subset=drop_duplicate_cols).sort_values(by=sort_vals)
    df.to_csv(df_path, sep="\t")
