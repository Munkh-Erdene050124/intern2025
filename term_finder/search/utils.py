import pandas as pd
import sys
import re


def read_tsv(tsv_path):
    try:
        df = pd.read_csv(tsv_path, sep='\t')
        df.columns = df.columns.str.strip() 
        df = df.iloc[::-1]
        return df
    except Exception as e:
        print(f"Error reading TSV: {e}")
        sys.exit(1)


def get_root(word):
    if not word:
        return ""
    
    case_suffixes = [
        'ын', 'ийн', 'ны', 'ний',
        'д', 'т',
        'аас', 'ээс', 'оос', 'өөс',
        'аар', 'ээр', 'оор', 'өөр',
        'тай', 'тэй', 'той',
        'руу', 'рүү',
        'г', 'ийг', 'ыг',
        'а', 'э', 'и', 'о', 'ө', 'у', 'ү', 'я', 'е', 'ё'
    ]
    plural_suffixes = [
        'ууд', 'үүд', 'нууд', 'нүүд'
    ]
    
    # Combined and sorted by length (descending) for longest-suffix-first matching
    all_suffixes = sorted(case_suffixes + plural_suffixes, key=len, reverse=True)
    
    current = word.lower()
    while True:
        matched = False
        for suffix in all_suffixes:
            if current.endswith(suffix):
                # Strip suffix and check for more (e.g. plural + case)
                current = current[:-len(suffix)]
                matched = True
                break
        if not matched:
            break
            
    return current


def simple_tokenize(text):
    raw_tokens = text.split()
    clean_tokens = []
    
    for t in raw_tokens:
        # Clean by removing punctuation from start and end
        # This handles things like "байгууллага," or "(байгууллага)"
        clean_t = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', t)
        clean_tokens.append(clean_t.lower())
        
    return raw_tokens, clean_tokens
