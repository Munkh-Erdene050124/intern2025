import functions

data_path = 'C:\\bachelor\\tsv-data\\merge_lt_dict_v3.tsv'
df = functions.read_tsv(data_path)
tries = functions.create_trie(data_path)

ccur_list = []
for i in range(1, 845):
    f_name = 'MNCLW' + '{:05d}'.format(i)
    f_path = 'C:\\bachelor\\law_txt_files\\' + f_name + '.txt'
    ret = functions.search_mwe_impl(
        f_name, f_path, df, tries[0], tries[1], i*1000)
    ccur_list.extend(ret)
    print(i+1)

if len(ccur_list) > 0:
    functions.create_df(ccur_list, 'C:\\bachelor\\tsv-data\\coocur_v2.tsv', [
        'doc_id', 'term_id', 'line_id'], ['doc_id'])
