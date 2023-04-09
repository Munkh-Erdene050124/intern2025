import functions
txt_lt_list = []
for i in range(1, 3):
    f_name = 'MNCLW' + '{:05d}'.format(i)
    f_path = 'C:\\bachelor\\law_txt_files\\' + f_name + '.txt'
    tl_list = functions.get_lt_list(functions.read_tsv(f_path), f_name)
    txt_lt_list.extend(tl_list)

if len(txt_lt_list) > 0:
    functions.create_df(txt_lt_list, 'C:\\bachelor\\tsv-data\\txt_lt_dict.tsv', [
        'leg_term',	'desc', 'pos_tag',	'term_root'], ['leg_term'])
