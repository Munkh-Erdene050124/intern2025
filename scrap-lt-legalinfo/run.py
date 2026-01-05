import functions

lt_list = functions.get_legal_term()
if len(lt_list) > 0:
    functions.create_df(lt_list, 'c:\\Visual_studio\\intern\\v2\\tsv-data\\web_lt_dict.tsv', [
        'leg_term',	'desc', 'pos_tag',	'term_root'], ['leg_term'])
