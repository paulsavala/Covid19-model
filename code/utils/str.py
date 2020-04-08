

def pretty_var(v, upper_only_first=False):
    v_clean = v.replace('_', ' ').title()
    if upper_only_first:
        v_split = v_clean.split(' ')
        if len(v_split) > 1:
            v_initial = v_split[0]
            v_remaining = v_split[1:]
            v_remaining = [v.lower() for v in v_remaining]
            v_clean = ' '.join([v_initial] + v_remaining)
    return v_clean
