import json
import re

def tokenize(text):
    # Basic tokenization: split by space, but keep punctuation separate
    # This regex splits by space or specific punctuation characters, keeping punctuation
    tokens = re.findall(r"[\w']+|[.,!?;\"“”]", text)
    return tokens

def get_lemma(word):
    # Heuristic lemmatization to match requested format: [word+N+Sg+Nom]
    # This is a PLACEHOLDER. Real lemmatization requires a massive dictionary.
    # We will fake it for the purpose of maintaining data structure integrity.
    
    # Check if likely a noun (simple heuristic)
    if word[0].isupper():
        return f"[{word.lower()}+N+Sg+Nom]"
    if word == '"' or word in '.,!?;':
        return '["+Sent]'
    return f"[{word}+None]" 

def get_pos_tag(word):
    # Rule-based POS tagging
    if word in ['"', '.', '!', '?', ';']:
        return "PUN"
    if word.lower() in ['тэдгээр', 'энэ', 'тэр']: # Common mongolian pronouns
        return "PJ" # Or PRONOUN
    if word[0].isupper():
        return "NC" # Noun Common/Proper assumption
    return "NM" # Default matching existing codebase "NM" often used

def process_text_to_json_string(text):
    tokens = tokenize(text)
    
    sentence_list = []
    
    for word in tokens:
        item = {
            "word": word,
            "lemma": get_lemma(word),
            "posTag": get_pos_tag(word),
            "nameType": "O",
            "stopWordType": "None" if word not in ['тэдгээр', 'энэ'] else "PRONOUN"
        }
        sentence_list.append(item)
        
    # The API returns a list of lists (sentences). We treat the whole text as one sentence for now
    # or split by sentence ending punctuation if we want to be fancy.
    # The example showed [[{...}]] so it is a list of sentences.
    
    final_structure = [sentence_list]
    return json.dumps(final_structure, ensure_ascii=False)

if __name__ == "__main__":
    # Test with the user's example
    test_text = '"тэдгээр хуулийн этгээдийг"'
    print(process_text_to_json_string(test_text))
