
import os
import sys
# Mimic what main.py/flask does with path
sys.path.append(os.getcwd())

print("Step 1: Importing main_app components...")
try:
    from main_app import trie, df, load_global_data
    from main_app.services import mwe_service
    print(f"Imports successful. Trie type: {type(trie)}, DF type: {type(df)}")
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

print("\nStep 2: Checking Global Data...")
if trie is None or df is None:
    print("Globals are None. Attempting load_global_data()...")
    load_global_data()
    from main_app import trie, df
    print(f"Reloaded. Trie type: {type(trie)}, DF type: {type(df)}")
    
if trie is None:
    print("CRITICAL: Trie is still None. Cannot proceed.")
    sys.exit(1)

print("\nStep 3: Simulating MWE Extraction...")
text_content = "Монгол Улсын хууль тогтоомж"
try:
    print(f"Extracting from text: {text_content}")
    # Logic from views.py
    for chunk in mwe_service.str_to_word_lines(text_content, 300).split('\n'):
        res = mwe_service.search_mwe(trie[0], trie[1], df, chunk)
        print(f"Result found: {len(res['found_mwe'])} terms.")
        for term in res['found_mwe']:
            print(f"- {term['leg_term']}")
    print("SUCCESS: Extraction logic passed.")
except Exception as e:
    print(f"CRITICAL ERROR in extraction: {e}")
    import traceback
    traceback.print_exc()

