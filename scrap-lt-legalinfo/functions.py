import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import json
import time
import random

legalinfo_back = 'https://legalinfo.mn/mn/knowledgeList'
legalinfo_front = 'https://legalinfo.mn/mn/knowledge'
headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9,mn;q=0.8',
    'Connection': 'keep-alive',
    'Content-Length': 30,
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Host': 'legalinfo.mn',
    'Origin': 'https://legalinfo.mn',
    'Referer': 'https://legalinfo.mn/mn/knowledge'
}


def convert_dict(a_list):
    dict_list = []
    for a in a_list:
        dict_list.append(a.__dict__)
    return dict_list


def create_df(data_list, df_path, drop_duplicate_cols=[], sort_vals=[]):
    df = pd.DataFrame(convert_dict(data_list))
    df = df.drop_duplicates(
        subset=drop_duplicate_cols).sort_values(by=sort_vals, key=lambda x: x.str.len())
    df.to_csv(df_path, sep="\t")


class LegalTerm:
    def __init__(self, leg_term, desc, pos_tag, term_root):
        self.id = round(time.time()*1000)*10000 + random.randint(1000, 9999)
        self.leg_term = leg_term
        self.desc = desc
        self.pos_tag = pos_tag
        self.term_root = term_root

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tleg_term: ' + str(self.leg_term) + ',\n\tdesc: ' + str(self.desc) + ',\n\tpos_tag: ' + str(self.pos_tag) + ',\n\tterm_root: ' + str(self.term_root) + '\n)'


def get_leg_letter():
    letter_list = []
    lres = requests.post(legalinfo_back)
    if lres.status_code != 200:
        print(lres.status_code)
    soup = BeautifulSoup(lres.text, "html.parser")
    l_list = soup.find_all(
        'ul', {'class': 'uk-flex list-none huuli-filter-useg'})
    for lett in l_list:
        list_li = lett.find_all('li')
        for li in list_li:
            # print(li.text.lower())
            letter_list.append(li.text.lower())
    return letter_list


def get_leg_pages(letter_list):
    lett_page_list = []
    for lett in letter_list:
        pres = requests.post(legalinfo_back, {'useg': lett}, headers)
        if pres.status_code != 200:
            print(pres.status_code)
        soup = BeautifulSoup(json.loads(pres.text)['Html'], "html.parser")
        p_num_list = soup.find_all('li', {'class': 'number uk-disabled'})
        for idx, pnum in enumerate(p_num_list):
            if idx == 0:
                slt1 = pnum.text.split('/')
                # print(lett + ' ' + slt1[1] * 1)
                lett_page_list.append({'useg': lett, 'pagecnt': int(slt1[1])})
    return lett_page_list


def get_legal_term():
    lterm_list = []
    for lett_page in get_leg_pages(get_leg_letter()):
        if lett_page['pagecnt'] > 0:
            for pg in range(1, lett_page['pagecnt']):
                data = {'useg': lett_page['useg'],
                        'offset': pg, 'name': '', 'description': ''}
                res = requests.post(legalinfo_front, data, headers)
                if res.status_code != 200:
                    print(res.status_code)
                    print("error: ", legalinfo_front)
                soup = BeautifulSoup(json.loads(res.text)[
                                     'Html'], "html.parser")
                tr_list = soup.find_all('tr')
                for tr in tr_list:
                    sp = tr.find('span', {'class': 'table-desc-bold'})
                    desc_list = tr.find_all('span', {'class': 'table-desc'})
                    if sp != None and desc_list != None and sp.text != '#':
                        desc = desc_list[1].text.lower().strip()
                        slt = sp.text.lower().strip().split(' ')
                        lt = LegalTerm(sp.text.lower(), desc,
                                       'NM', slt[len(slt) - 1])
                        print(lt.to_str())
                        lterm_list.append(lt)
    return lterm_list


class LegalTerm:
    def __init__(self, leg_term, desc, pos_tag, term_root):
        self.id = round(time.time()*1000)*10000 + random.randint(1000, 9999)
        self.leg_term = leg_term
        self.desc = desc
        self.pos_tag = pos_tag
        self.term_root = term_root

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tleg_term: ' + str(self.leg_term) + ',\n\tdesc: ' + str(self.desc) + ',\n\tpos_tag: ' + str(self.pos_tag) + ',\n\tterm_root: ' + str(self.term_root) + '\n)'
