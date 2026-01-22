import re
import math
from pathlib import Path

def parse_trie_output(file_path):
    """
    Parses trie-output.txt to extract terms and their occurrences.
    
    Args:
        file_path (str or Path): Path to the trie-output.txt file.
        
    Returns:
        dict: A dictionary where keys are terms (str) and values are occurrence counts (int).
              Returns an empty dict if file not found or empty.
    """
    term_counts = {}
    path = Path(file_path)
    
    if not path.exists():
        return term_counts
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split into lines
        lines = content.split('\n')
        
        # Identify the start of the table
        # We look for the header "Term Line Word Place" or similar
        start_index = -1
        for i, line in enumerate(lines):
            if "Term" in line and "Line" in line and "Word Place" in line:
                start_index = i + 2 # Skip header and empty line
                break
        
        if start_index == -1:
             # Fallback: maybe no header if empty? Or different format?
             # Let's try to parse from line 1 if it looks like data, 
             # but based on provided example, there is a header.
             # If no header found, return empty or try heuristic
             return term_counts

        regex = re.compile(r"\s{2,}") # Split by 2 or more spaces

        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            
            # Split by multiple spaces to separate columns
            # Example: "мөрдөгч                         6, 7                  7, 16"
            parts = regex.split(line)
            
            if len(parts) >= 1:
                term = parts[0].strip()
                if not term: 
                    continue
                
                # Calculate occurrences
                # The "Word Place" column (index 2) contains comma-separated occurrences
                # If column 2 exists, count commas + 1. 
                # If not (maybe just Term column?), count is 1? 
                # Let's check parts length.
                
                count = 1
                if len(parts) >= 3:
                     word_places = parts[2].strip()
                     if word_places:
                         count = len(word_places.split(','))
                elif len(parts) >= 2:
                     # Maybe only Line column exists? check Line column
                     lines_col = parts[1].strip()
                     if lines_col:
                          count = len(lines_col.split(','))
                
                if term in term_counts:
                    term_counts[term] += count
                else:
                    term_counts[term] = count
                    
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        
    return term_counts

def calculate_jaccard_similarity(set_a, set_b):
    """
    Computes Jaccard similarity between two sets.
    """
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    if union == 0:
        return 0.0
    return intersection / union

def calculate_tfidf_weight(shared_terms, doc_a_counts, doc_b_counts, idf_map):
    """
    Computes a weight based on Sum(TF-IDF) for shared terms.
    For a shared term t:
       weight += (TF_a(t) * IDF(t)) * (TF_b(t) * IDF(t))
    Or simpler: Sum( IDF(t) ) -- this is often enough for "shared rareness".
    Let's go with Sum of (Min(TF_a, TF_b) * IDF(t)) as a robust intersection weight
    or just Sum(IDF(t)) for simpliciy if requested.
    
    The prompt asked for "sum of TF-IDF style weights". 
    Let's implement: Sum(IDF(term)) for all normalized shared terms.
    This rewards sharing rare terms more than common terms.
    """
    weight = 0.0
    for term in shared_terms:
        idf = idf_map.get(term, 0.0)
        # We can also scale by frequency if we want, but Sum(IDF) is a solid metric 
        # for "weighted shared content". 
        # Let's include frequency: avg(tf_a, tf_b) * idf
        # or just simply: idf (to follow "tfidf_shared" implied meaning of "value of shared info")
        
        # Let's use: Sum(IDF(t)) meaning "how surprising is it that they share these terms?"
        weight += idf
    return weight

def load_dictionary(dict_path):
    """
    Loads term dictionary. Returns map: leg_term -> id
    """
    term_to_id = {}
    path = Path(dict_path)
    if not path.exists():
        print(f"Dictionary file not found: {dict_path}")
        return term_to_id
        
    with open(path, 'r', encoding='utf-8') as f:
        # header
        header = f.readline() 
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                # id is col 0, leg_term is col 1
                try:
                    term_id = parts[0]
                    leg_term = parts[1]
                    term_to_id[leg_term] = term_id
                except:
                    pass
    return term_to_id
