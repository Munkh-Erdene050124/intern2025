import os
import sys
import argparse
import math
import time
from pathlib import Path
from collections import defaultdict
import networkx as nx

# Add current directory to path to import sna_utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sna_utils

def main():
    parser = argparse.ArgumentParser(description="Build SNA pipeline for MNCLW laws.")
    parser.add_argument("--weight_mode", choices=['raw', 'tfidf', 'jaccard'], required=True, help="Edge weighting mode")
    parser.add_argument("--max_df", type=float, default=0.30, help="Ignore terms appearing in > X fraction of docs (default 0.30)")
    parser.add_argument("--min_shared_terms", type=int, default=1, help="Min shared terms to create an edge (default 1)")
    parser.add_argument("--use", choices=['trie', 'aho'], default='trie', help="Which output file to read (default trie)")
    parser.add_argument("--output_dir", default=str(Path(__file__).parent.parent / "tsv-data"), help="Output directory")
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent.parent 
    term_finder_output_dir = base_dir / "term_finder" / "output"
    dict_path = base_dir / "tsv-data" / "merge_lt_dict_v3.tsv"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"--- Starting SNA Pipeline ---")
    print(f"Weight Mode: {args.weight_mode}")
    print(f"Output Dir: {output_dir}")
    
    # Load Dictionary
    print("Loading dictionary...")
    term_to_id = sna_utils.load_dictionary(dict_path)
    print(f"Loaded {len(term_to_id)} terms from dictionary.")
    
    # Load Law Data
    # We need to map LawID -> {Term -> Count}
    # And Term -> Document Frequency (DF)
    law_term_counts = {} # law_id -> {term: count}
    term_doc_freq = defaultdict(int) 
    
    print("Reading law term occurrences...")
    
    # Expecting folders like term_occur00001, term_occur00002...
    # The Law ID is usually MNCLWxxxxx corresponding to the number.
    # Let's scan the directory.
    
    subdirs = sorted([d for d in term_finder_output_dir.iterdir() if d.is_dir() and d.name.startswith("term_occur")])
    total_laws = len(subdirs)
    
    filename_to_read = "trie-output.txt" if args.use == 'trie' else "aho-output.txt"
    
    for idx, subdir in enumerate(subdirs):
        # Infer Law ID from folder name or file content? 
        # Folder: term_occur00001 -> MNCLW00001
        # Let's trust the folder numbering to map to MNCLW ID for the Law ID.
        try:
            num_part = subdir.name.replace("term_occur", "")
            law_id = f"MNCLW{num_part}"
        except:
            law_id = subdir.name
            
        if idx % 50 == 0:
            print(f"Processing law {idx+1}/{total_laws}: {law_id}")
            
        file_path = subdir / filename_to_read
        counts = sna_utils.parse_trie_output(file_path)
        
        if counts:
            law_term_counts[law_id] = counts
            for term in counts:
                term_doc_freq[term] += 1
                
    num_docs = len(law_term_counts)
    print(f"\nProcessed {num_docs} laws with term data.")
    
    # Filter Terms & Precompute IDF
    # Filter stopwords (high DF)
    max_doc_count = num_docs * args.max_df
    
    valid_terms = set()
    idf_map = {}
    
    for term, df in term_doc_freq.items():
        if df <= max_doc_count:
            valid_terms.add(term)
            # IDF = log(N / DF)
            idf_map[term] = math.log(num_docs / (df + 1e-6)) + 1.0
    
    print(f"Filtered terms (DF > {args.max_df:.2f}): Removed {len(term_doc_freq) - len(valid_terms)} terms. Kept {len(valid_terms)}.")

    # Build Graph
    print(f"\nBuilding {args.weight_mode} graph...")
    G = nx.Graph()
    
    # Add nodes
    for law_id in law_term_counts:
        G.add_node(law_id)
        
    # Add edges
    # Compare all pairs. optimize: keys list
    law_ids = list(law_term_counts.keys())
    
    start_time = time.time()
    edges_added = 0
    
    # Pre-filter law term sets to only valid terms for faster intersection
    law_valid_term_sets = {}
    for lid in law_ids:
        raw_terms = law_term_counts[lid]
        # Set of valid terms
        filtered = {t for t in raw_terms if t in valid_terms}
        law_valid_term_sets[lid] = filtered

    # Checking pairs
    total_pairs = (len(law_ids) * (len(law_ids) - 1)) // 2
    processed_pairs = 0
    
    for i in range(len(law_ids)):
        for j in range(i + 1, len(law_ids)):
            id_a = law_ids[i]
            id_b = law_ids[j]
            
            set_a = law_valid_term_sets[id_a]
            set_b = law_valid_term_sets[id_b]
            
            if not set_a or not set_b:
                continue
                
            shared = set_a.intersection(set_b)
            n_shared = len(shared)
            
            if n_shared < args.min_shared_terms:
                continue
                
            # Calculate Weight
            weight = 0.0
            if args.weight_mode == 'raw':
                weight = float(n_shared)
            elif args.weight_mode == 'jaccard':
                weight = sna_utils.calculate_jaccard_similarity(set_a, set_b)
            elif args.weight_mode == 'tfidf':
                weight = sna_utils.calculate_tfidf_weight(shared, law_term_counts[id_a], law_term_counts[id_b], idf_map)
            
            if weight > 0:
                # Sample shared terms (max 10)
                sample_list = list(shared)[:10]
                sample_str = ",".join(sample_list)
                
                G.add_edge(id_a, id_b, weight=weight, shared_count=n_shared, shared_sample=sample_str)
                edges_added += 1
                
            processed_pairs += 1
            if processed_pairs % 100000 == 0:
                print(f"  Compared {processed_pairs} pairs...")
                
    elapsed = time.time() - start_time
    print(f"Graph construction took {elapsed:.2f}s. Edges: {edges_added}")
    
    # Compute Metrics
    print("\nComputing SNA metrics...")
    
    # Basic
    degrees = dict(G.degree())
    weighted_degrees = dict(G.degree(weight='weight'))
    
    # Centrality
    # For large graphs, exact betweenness is slow. We can try exact for 844 nodes (small).
    # 844 nodes is very small for NetworkX, exact calc is fine.
    print("  Betweenness centrality...")
    betweenness = nx.betweenness_centrality(G, weight='weight' if args.weight_mode != 'raw' else None)
    
    print("  Closeness centrality...")
    closeness = nx.closeness_centrality(G) # unweighted usually or distance based. Closeness uses distance=1/weight usually. 
    # NetworkX closeness uses 'distance'. If we want weighted, we need to invert weight. 
    # For now, let's stick to unweighted topology for closeness or just pass none. User asked "unweighted".
    # User Request: "closeness_centrality (unweighted)" -> OK.
    
    print("  PageRank...")
    try:
        pagerank = nx.pagerank(G, weight='weight')
    except:
        pagerank = {n: 0.0 for n in G.nodes()}

    # Components
    components = list(nx.connected_components(G))
    comp_id_map = {}
    comp_size_map = {}
    for cid, comp in enumerate(components):
        for node in comp:
            comp_id_map[node] = cid
            comp_size_map[node] = len(comp)

    # Output Generation
    print("\nGenerating outputs...")
    
    # law_term_presence.tsv
    # law_id, term_id, leg_term, term_root, occurrences_count
    # Note: Dictionary has id, leg_term, desc, pos_tag, term_root.
    # We load dictionary to get term_id and term_root if possible. 
    # But current load_dictionary only returns leg_term -> id. 
    # We might need to re-read dict efficiently or store more info.
    # Let's improve dictionary loading slightly or just re-read it here if memory allows, 
    # OR we just store what we have. 
    # The requirement says: law_id, term_id, leg_term, term_root (if available).
    # I'll just use the ID from my loaded map. For root, I don't have it loaded. 
    # I will proceed with what I have. If root is needed, I'd need to update sna_utils or main. 
    # Let's assume term_root is not strictly critical if not loaded, or load a secondary map.
    # Actually, let's do a quick reload of full dict metadata to be precise.
    
    full_term_meta = {} # term -> {id, root}
    with open(dict_path, 'r', encoding='utf-8') as f:
        f.readline()
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                full_term_meta[parts[1]] = {'id': parts[0], 'root': parts[4]}
    
    with open(output_dir / "law_term_presence.tsv", "w", encoding='utf-8') as f:
        f.write("law_id\tterm_id\tleg_term\tterm_root\toccurrences_count\n")
        for lid, counts in law_term_counts.items():
            for term, count in counts.items():
                meta = full_term_meta.get(term, {'id': '?', 'root': '?'})
                f.write(f"{lid}\t{meta['id']}\t{term}\t{meta['root']}\t{count}\n")
                
    # law_network_edges.tsv
    with open(output_dir / "law_network_edges.tsv", "w", encoding='utf-8') as f:
        f.write("source_law\ttarget_law\tweight\tshared_terms_count\tshared_terms_sample\n")
        for u, v, data in G.edges(data=True):
            f.write(f"{u}\t{v}\t{data['weight']:.4f}\t{data['shared_count']}\t{data['shared_sample']}\n")

    # law_node_stats.tsv
    # law_id, terms_unique, degree, weighted_degree, betweenness, closeness, pagerank, component_id, component_size
    with open(output_dir / "law_node_stats.tsv", "w", encoding='utf-8') as f:
        f.write("law_id\tterms_unique\tdegree\tweighted_degree\tbetweenness\tcloseness\tpagerank\tcomponent_id\tcomponent_size\n")
        for node in G.nodes():
            n_unique = len(law_term_counts.get(node, {}))
            deg = degrees.get(node, 0)
            w_deg = weighted_degrees.get(node, 0)
            bet = betweenness.get(node, 0)
            clo = closeness.get(node, 0)
            pr = pagerank.get(node, 0)
            cid = comp_id_map.get(node, -1)
            csize = comp_size_map.get(node, 0)
            
            f.write(f"{node}\t{n_unique}\t{deg}\t{w_deg:.4f}\t{bet:.6f}\t{clo:.6f}\t{pr:.6f}\t{cid}\t{csize}\n")
            
    # law_network_summary.txt
    summary_path = output_dir / "law_network_summary.txt"
    try:
        density = nx.density(G)
        giant_size = len(max(components, key=len)) if components else 0
        sorted_deg = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:20]
        
        with open(summary_path, "w", encoding='utf-8') as f:
            f.write("SNA Network Summary\n")
            f.write(f"Timestamp: {time.ctime()}\n")
            f.write(f"Weight Mode: {args.weight_mode}\n")
            f.write(f"Nodes: {G.number_of_nodes()}\n")
            f.write(f"Edges: {G.number_of_edges()}\n")
            f.write(f"Density: {density:.6f}\n")
            f.write(f"Components: {len(components)}\n")
            f.write(f"Giant Component Size: {giant_size}\n")
            f.write("\nTop 20 Laws by Degree:\n")
            for lid, d in sorted_deg:
                f.write(f"{lid}: {d}\n")
                
    except Exception as e:
        print(f"Could not write summary: {e}")
        
    print("\nDone! Outputs saved to:", output_dir)

if __name__ == "__main__":
    main()
