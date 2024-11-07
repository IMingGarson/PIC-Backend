import difflib

def fuzzy_match(query, word_list):
    res = difflib.get_close_matches(query, word_list, n=1, cutoff=0.0)
    return res[0] if res else ""