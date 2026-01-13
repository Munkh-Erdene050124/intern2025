import csv

def check_missing_ids(v3_path, v5_path):
    print(f"Checking IDs from {v3_path} against {v5_path}...")
    
    try:
        # Load IDs from v3
        v3_ids = set()
        with open(v3_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if 'id' in row and row['id']:
                    v3_ids.add(row['id'])
        print(f"Loaded {len(v3_ids)} unique IDs from v3.")

        # Load IDs from v5
        v5_ids = set()
        with open(v5_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if 'id' in row and row['id']:
                    v5_ids.add(row['id'])
        print(f"Loaded {len(v5_ids)} unique IDs from v5.")

        # Find missing IDs
        missing_ids = v3_ids - v5_ids
        
        if missing_ids:
            print(f" Found {len(missing_ids)} IDs in v3 that are MISSING in v5:")
            # Sort for easier reading, printing first 20 if there are many
            sorted_missing = sorted(list(missing_ids))
            for mid in sorted_missing[:20]:
                print(f" - {mid}")
            if len(sorted_missing) > 20:
                print(f"... and {len(sorted_missing) - 20} more.")
        else:
            print(" SUCCESS: All IDs from v3 are present in v5.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    v3_file = r"c:\Visual_studio\intern\v2\tsv-data\merge_lt_dict_v3.tsv"
    v5_file = r"c:\Visual_studio\intern\v2\tsv-data\merge_lt_dict_v5.tsv"
    check_missing_ids(v3_file, v5_file)
