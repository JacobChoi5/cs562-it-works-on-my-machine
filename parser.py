import sys
import re
from config import VALID_COLUMNS, VALID_AGGS


def error(msg): # formatting for error messages and exiting program
    print("Error:", msg)
    sys.exit(1)


def split_input(text, name, sep=","): # preprocessing on comma separated string
    if not text.strip(): # removes whitespace, check if nothing between commas
        error(f"{name} cannot be empty.")
    parts = [p.strip() for p in text.split(sep)]
    if any(p == "" for p in parts):
        error(f"{name} has an empty value.")
    return parts


def _parse_agg(token, ctx=None): # ie 1_sum_quant or sum_1_quant; errors if ctx is given and token is invalid
    parts = token.split("_")
    if len(parts) == 3:
        if parts[0].isdigit():
            return int(parts[0]), parts[1], parts[2]
        if parts[1].isdigit():
            return int(parts[1]), parts[0], parts[2]
    if ctx is not None:
        error(f"{ctx} '{token}' is invalid. Use format like 1_sum_quant.")
    return None


def _check_agg(group_num, agg, attr, n, ctx): # checks if fields in agg function name are correct
    if group_num < 1 or group_num > n:
        error(f"{ctx}: group {group_num} is out of range (n={n}).")
    if agg not in VALID_AGGS:
        error(f"{ctx}: '{agg}' is not a valid aggregate.")
    if attr not in VALID_COLUMNS:
        error(f"{ctx}: '{attr}' is not a valid column.")


def _parse_literal(raw): # converts string value into appropriate type
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    lo = text.lower()
    if lo == "true": return True
    if lo == "false": return False
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        return text


def _split_and(text): # handler for "and"
    parts = [p.strip() for p in text.split("and")]
    if any(p == "" for p in parts): # errors for invalid usage of "and"
        error(f"Invalid condition chain '{text}'.")
    return parts


def _parse_v(V): # checks if all grouping attributes exist and no duplicates
    seen = set()
    for attr in V:
        if attr not in VALID_COLUMNS:
            error(f"V contains invalid attribute '{attr}'.")
        if attr in seen:
            error(f"V contains duplicate '{attr}'.")
        seen.add(attr)
    return V


def _parse_f(F, n): # parses full aggregate function f vector
    seen, result = set(), []
    for item in F:
        group_num, agg, attr = _parse_agg(item, "F") # parses actual agg "1_sum_quant"
        _check_agg(group_num, agg, attr, n, f"F '{item}'") # check all fields valid
        if item in seen:
            error(f"F contains duplicate '{item}'.") # rejects if duplicate
        seen.add(item)
        result.append({"raw": item, "group": group_num, "agg": agg, "attr": attr})
    return result


def _parse_s(S, n, f_names): # checks all fields in select
    seen, result = set(), []
    for item in S:
        if item in seen:
            error(f"S contains duplicate '{item}'.")
        seen.add(item)
        if item in VALID_COLUMNS:
            result.append({"raw": item, "kind": "attribute", "attribute": item}) # full column
        else:
            group_num, agg, attr = _parse_agg(item, "S") # checks for aggregate and also checks any aggregates appear in f vector
            _check_agg(group_num, agg, attr, n, f"S '{item}'")
            if item not in f_names:
                error(f"S aggregate '{item}' must also appear in F.")
            result.append({"raw": item, "kind": "aggregate",
                           "group": group_num, "agg": agg, "attr": attr})
    return result


_SIGMA_RE = re.compile( # gets group number, attribute name, operator, and right hand side
    r"^\s*(\d+)\.([a-zA-Z_]\w*)\s*(==|!=|>=|<=|=|>|<)\s*(.+?)\s*$" # CLAUDE DID THIS ONE
)


def _parse_sigma_pred(condition, n, current_group, f_names): # parses single predicate from sigma
    m = _SIGMA_RE.match(condition)
    if not m:
        error(f"sigma condition '{condition}' is invalid. Use format like 1.state='NY'.")
    group_num = int(m.group(1))
    left_attr = m.group(2)
    op = "==" if m.group(3) == "=" else m.group(3) # = --> ==
    right_raw = m.group(4).strip()

    if group_num < 1 or group_num > n:
        error(f"sigma condition '{condition}' uses group {group_num}, but n={n}.")
    if left_attr not in VALID_COLUMNS:
        error(f"sigma condition '{condition}' uses invalid attribute '{left_attr}'.")
    if right_raw in VALID_COLUMNS: # if right side is another column
        right_type, right_value, agg_ref = "group_attr", right_raw, None
    else:
        agg = _parse_agg(right_raw) # check if right side is aggregate
        if agg is not None:
            ref_group, ref_agg, ref_attr = agg
            if ref_group >= current_group:
                error(f"sigma '{condition}' references forward group {ref_group}.") # aggregate has to be from prior group
            _check_agg(ref_group, ref_agg, ref_attr, n, f"sigma '{condition}' right-side")
            if right_raw not in f_names: # check if aggregate in f vector
                error(f"sigma '{condition}' references undefined aggregate '{right_raw}'.")
            right_type = "aggregate_field"
            right_value = right_raw
            agg_ref = {"group": ref_group, "agg": ref_agg, "attr": ref_attr}
        else:
            right_type, right_value, agg_ref = "literal", _parse_literal(right_raw), None

    return {"raw": condition, "group": group_num, "left_attr": left_attr,
            "op": op, "right_type": right_type, "right_value": right_value,
            "aggregate_ref": agg_ref}


def _parse_sigma(sigma, n, f_names): # parses list of sigma entries
    seen_groups, result = set(), []
    for condition_text in sigma:
        parts = _split_and(condition_text)
        matches = [_SIGMA_RE.match(p) for p in parts]
        if any(m is None for m in matches): # anything is empty in and chain for predicate
            error(f"sigma condition '{condition_text}' is invalid.")
        groups = {int(m.group(1)) for m in matches} # all in one and chain has to be same grouping variables
        if len(groups) != 1:
            error(f"sigma condition '{condition_text}' mixes grouping variables.")
        g = groups.pop()
        if g in seen_groups:
            error(f"sigma has two entries for group {g}.")
        seen_groups.add(g)
        predicates = [_parse_sigma_pred(p, n, g, f_names) for p in parts]
        result.append({"raw": condition_text, "group": g, "predicates": predicates})
    if len(seen_groups) != n: # one condition per grouping variable
        error("sigma must have exactly one condition per grouping variable.")
    return result


_G_RE = re.compile( # left side is either plain identifier or aggregate token
    r"^\s*([a-zA-Z_]\w*|\d+_[a-zA-Z_]\w*_[a-zA-Z_]\w*)\s*(==|!=|>=|<=|=|>|<)\s*(.+?)\s*$" # claude also did this one
)



def _parse_g_pred(condition, n, f_names): # parses g having predicate
    m = _G_RE.match(condition)
    if not m:
        error(f"G condition '{condition}' is invalid.")
    left_name = m.group(1) # aggregate token or column name
    op = "==" if m.group(2) == "=" else m.group(2)
    right_raw = m.group(3).strip()

    if left_name not in VALID_COLUMNS: # if aggregate token, parses aggregate and checks
        group_num, agg_name, attr_name = _parse_agg(left_name, "G condition left side")
        _check_agg(group_num, agg_name, attr_name, n, f"G '{condition}' left")
        if left_name not in f_names:
            error(f"G condition references undefined aggregate '{left_name}'.")

    if right_raw in VALID_COLUMNS: # classifies as column field
        right_type, right_value = "field", right_raw
    else:
        agg = _parse_agg(right_raw)
        if agg is not None:
            group_num, agg_name, attr_name = agg
            _check_agg(group_num, agg_name, attr_name, n, f"G '{condition}' right") 
            if right_raw not in f_names:
                error(f"G condition references undefined aggregate '{right_raw}'.")
            right_type, right_value = "field", right_raw
        else:
            right_type, right_value = "literal", _parse_literal(right_raw)

    return {"raw": condition, "left_type": "field", "left_value": left_name,
            "op": op, "right_type": right_type, "right_value": right_value}


def _parse_g(G_text, n, f_names): # loops through all g predicates
    G_text = G_text.strip()
    if G_text.upper() == "NONE": # if none, return empty g
        return {"raw": G_text, "kind": "none", "predicates": []}
    predicate_texts = _split_and(G_text)
    return {"raw": G_text, "kind": "and_chain",
            "predicates": [_parse_g_pred(p, n, f_names) for p in predicate_texts]}


def build_query_data(S, n, V, F, sigma, G): # takes in all unprocessed fields
    # calls in dependency order
    V = _parse_v(V)
    parsed_F = _parse_f(F, n)
    f_names = {item["raw"] for item in parsed_F}
    parsed_S = _parse_s(S, n, f_names)
    parsed_sigma = _parse_sigma(sigma, n, f_names)
    parsed_G = _parse_g(G, n, f_names)

    return { # returns all together
        "S_raw": [item["raw"] for item in parsed_S],
        "n": n,
        "V": V,
        "F_raw": F,
        "sigma_raw": sigma,
        "G": parsed_G,
        "S": parsed_S,
        "F": parsed_F,
        "sigma": parsed_sigma,
    }
