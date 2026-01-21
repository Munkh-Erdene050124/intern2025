import pandas as pd
import sys
import re
import requests
from functools import lru_cache
from bs4 import BeautifulSoup
import json

#use the teacher pipeline endpoint that your working functions.py uses.
NLP_URL = "http://speech.mn:8081/nlp-web-demo/process?text="

_session = requests.Session()

#print fallback message only once across the whole run.
_server_failed_once = False


def read_tsv(tsv_path):
    try:
        df = pd.read_csv(tsv_path, sep="\t")
        df.columns = df.columns.str.strip()
        df = df.iloc[::-1]
        return df
    except Exception as e:
        print(f"Error reading TSV: {e}")
        sys.exit(1)


def simple_tokenize(text):
    raw_tokens = text.split()
    clean_tokens = []

    for t in raw_tokens:
        clean_t = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", t)
        clean_tokens.append(clean_t.lower())

    return raw_tokens, clean_tokens


def _suffix_strip_root(word):
    if not word:
        return ""

    case_suffixes = [
        "ын", "ийн", "ны", "ний",
        "д", "т",
        "аас", "ээс", "оос", "өөс",
        "аар", "ээр", "оор", "өөр",
        "тай", "тэй", "той",
        "руу", "рүү",
        "г", "ийг", "ыг",
        "а", "э", "и", "о", "ө", "у", "ү", "я", "е", "ё"
    ]
    plural_suffixes = [
        "ууд", "үүд", "нууд", "нүүд"
    ]

    all_suffixes = sorted(case_suffixes + plural_suffixes, key=len, reverse=True)

    current = word.lower()
    while True:
        matched = False
        for suffix in all_suffixes:
            if current.endswith(suffix) and len(current) > len(suffix):
                current = current[:-len(suffix)]
                matched = True
                break
        if not matched:
            break

    return current


def _teacher_api_token_root(word: str, timeout_seconds: int = 3) -> str:
    if not word:
        return ""

    # Use GET
    res = _session.get(NLP_URL + word, timeout=timeout_seconds)
    if res.status_code != 200:
        return ""

    soup = BeautifulSoup(res.text, "html.parser")

    try:
        payload = json.loads(soup.text)
    except Exception:
        return ""

    # payload is expected as: list(sentences), sentence is list(tokens)
    # For a single word request, take the first token we can find
    try:
        for sentence in payload:
            for token in sentence:
                lemma = token.get("lemma", "")
                if isinstance(lemma, str) and lemma.strip():
                    # Normalize lemma roots list to first root if list-like
                    cleaned = lemma.replace("[", "").replace("]", "").strip()
                    if cleaned:
                        first = cleaned.split(",")[0].strip()
                        root = first.split("+")[0].strip().lower()
                        if root:
                            return root

                # If lemma missing, fallback to word itself
                w = token.get("word", "")
                if isinstance(w, str) and w.strip():
                    return w.strip().lower()
    except Exception:
        return ""

    return ""


@lru_cache(maxsize=200_000)
def get_root(word):
    global _server_failed_once

    if not word:
        return ""

    w = word.lower()
    if len(w) <= 1 or w.isdigit():
        return w

    try:
        root = _teacher_api_token_root(w, timeout_seconds=3)
        if root:
            return root
        raise RuntimeError("teacher_api_empty")
    except Exception:
        if not _server_failed_once:
            print("Server failed changed to simple suffix strip method")
            _server_failed_once = True
        return _suffix_strip_root(w)
