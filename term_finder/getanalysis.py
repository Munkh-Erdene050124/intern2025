import sys
import subprocess
from pathlib import Path


def main():
    target_file = 'MNCLW00243.txt' 
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    script_dir = Path(__file__).parent
    search_dir = script_dir / 'search'
    output_dir = script_dir / 'output'
    
    output_dir.mkdir(parents=True, exist_ok=True)

    aho_success = False
    trie_success = False
    
    # Run Aho-Corasick search
    try:
        aho_script = search_dir / 'aho-search.py'
        result = subprocess.run(
            [sys.executable, str(aho_script), target_file],
            cwd=str(search_dir),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Display output
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            aho_success = True
        else:
            print(f"Aho-Corasick search failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        print("Aho-Corasick search timed out")
    except Exception as e:
        print(f"Aho-Corasick search error: {e}")
    
    print()
    
    # Run Trie search
    try:
        trie_script = search_dir / 'trie-search.py'
        result = subprocess.run(
            [sys.executable, str(trie_script), target_file],
            cwd=str(search_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Display output
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            trie_success = True
        else:
            print(f"Trie search failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        print("Trie search timed out")
    except Exception as e:
        print(f"Trie search error: {e}")
    
    print()
    print(f"Aho-Corasick Search: {'SUCCESS' if aho_success else ' FAILED'}")
    print(f"Trie Search:         {'SUCCESS' if trie_success else ' FAILED'}")
    print()

    # Exit with status code
    if aho_success and trie_success:
        sys.exit(0)
    elif aho_success or trie_success:
        sys.exit(1)  # Partial success
    else:
        sys.exit(2)  # Complete failure


if __name__ == "__main__":
    main()
