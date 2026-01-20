import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import random
import re


class LegalTerm:
    def __init__(self, leg_term, desc, pos_tag, term_root):
        self.id = round(time.time()*1000)*10000 + random.randint(1000, 9999)
        self.leg_term = leg_term
        self.desc = desc
        self.pos_tag = pos_tag
        self.term_root = term_root

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tleg_term: ' + str(self.leg_term) + ',\n\tdesc: ' + str(self.desc) + ',\n\tpos_tag: ' + str(self.pos_tag) + ',\n\tterm_root: ' + str(self.term_root) + '\n)'


def get_lt_list(txt_df, name):
    lterm_list = []
    rows = txt_df.iterrows()
    for row in rows:
        law_txt = row[1]['Unnamed: 0'].lower().strip()
        title_matches = re.findall(r'\."([^"]*)"\sгэж\s', law_txt)
        if len(title_matches) > 0:
            desc_matches = re.findall(r'\sгэж\s.*', law_txt)
            t_mtch = title_matches[0].strip().lower()
            d_mtch = desc_matches[0].replace(' гэж ', '').replace(
                ';', '').replace('.', '').strip().lower()
            slt = t_mtch.split(' ')
            lt = LegalTerm(t_mtch, d_mtch, 'NM', slt[len(slt) - 1])
            lterm_list.append(lt)
        else:
            title_matches = re.findall(r'\.“([^“]*)”\sгэж\s', law_txt)
            if len(title_matches) > 0:
                desc_matches = re.findall(r'\sгэж\s.*', law_txt)
                t_mtch = title_matches[0].strip().lower()
                d_mtch = desc_matches[0].replace(' гэж ', '').replace(
                    ';', '').replace('.', '').strip().lower()
                slt = t_mtch.split(' ')
                lt = LegalTerm(t_mtch, d_mtch, 'NM', slt[len(slt) - 1])
                lterm_list.append(lt)
    return lterm_list


def read_tsv(data_path):
    try:
        df = pd.read_csv(data_path, sep='\t', dtype=str, keep_default_na=False)
    except pd.errors.ParserError:
        df = pd.read_csv(
            data_path,
            sep='\t',
            dtype=str,
            keep_default_na=False,
            engine='python',
            on_bad_lines='skip'  # skip malformed lines instead of dying
        )

    if 'Unnamed: 0' not in df.columns:
        if df.shape[1] >= 1:
            df = df.rename(columns={df.columns[0]: 'Unnamed: 0'})
        else:
            raise ValueError(f"{data_path} has no columns; cannot extract text.")

    return df



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