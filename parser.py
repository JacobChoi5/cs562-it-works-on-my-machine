import sys
import re
from config import VALID_COLUMNS, VALID_AGGS


def error(msg):
    print("Error:", msg)
    sys.exit(1)


def split_input(text, name, sep=","):
    if not text.strip():
        error(f"{name} cannot be empty.")
    parts = [p.strip() for p in text.split(sep)]
    if any(p == "" for p in parts):
        error(f"{name} has an empty value.")
    return parts


# --- Aggregate token helpers ---

def _parse_agg(token):
    """Returns (group_num, agg, attr) or None."""
    parts = token.split("_")
    if len(parts) != 3:
        return None
    if parts[0].isdigit():
        return int(parts[0]), parts[1], parts[2]
    if parts[1].isdigit():
        return int(parts[1]), parts[0], parts[2]
    return None


def _require_agg(token, ctx):
    r = _parse_agg(token)
    if r is None:
        error(f"{ctx} '{token}' is invalid. Use format like 1_sum_quant.")
    return r


def _check_agg(group_num, agg, attr, n, ctx):
    if group_num < 1 or group_num > n:
        error(f"{ctx}: group {group_num} is out of range (n={n}).")
    if agg not in VALID_AGGS:
        error(f"{ctx}: '{agg}' is not a valid aggregate.")
    if attr not in VALID_COLUMNS:
        error(f"{ctx}: '{attr}' is not a valid column.")


def _parse_literal(raw):
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


def _split_and(text):
    parts = [p.strip() for p in text.split("and")]
    if any(p == "" for p in parts):
        error(f"Invalid condition chain '{text}'.")
    return parts


# --- V ---

def _parse_v(V):
    seen = set()
    for attr in V:
        if attr not in VALID_COLUMNS:
            error(f"V contains invalid attribute '{attr}'.")
        if attr in seen:
            error(f"V contains duplicate '{attr}'.")
        seen.add(attr)
    return V


# --- F ---

def _parse_f(F, n):
    seen, result = set(), []
    for item in F:
        group_num, agg, attr = _require_agg(item, "F")
        _check_agg(group_num, agg, attr, n, f"F '{item}'")
        if item in seen:
            error(f"F contains duplicate '{item}'.")
        seen.add(item)
        result.append({"raw": item, "group": group_num, "agg": agg, "attr": attr})
    return result


# --- S ---

def _parse_s(S, n, f_names):
    seen, result = set(), []
    for item in S:
        if item in seen:
            error(f"S contains duplicate '{item}'.")
        seen.add(item)
        if item in VALID_COLUMNS:
            result.append({"raw": item, "kind": "attribute", "attribute": item})
        else:
            group_num, agg, attr = _require_agg(item, "S")
            _check_agg(group_num, agg, attr, n, f"S '{item}'")
            if item not in f_names:
                error(f"S aggregate '{item}' must also appear in F.")
            result.append({"raw": item, "kind": "aggregate",
                           "group": group_num, "agg": agg, "attr": attr})
    return result


# --- Sigma ---

_SIGMA_RE = re.compile(
    r"^\s*(\d+)\.([a-zA-Z_]\w*)\s*(==|!=|>=|<=|=|>|<)\s*(.+?)\s*$"
)


def _parse_sigma_pred(condition, n, current_group, f_names):
    m = _SIGMA_RE.match(condition)
    if not m:
        error(f"sigma condition '{condition}' is invalid. Use format like 1.state='NY'.")
    group_num = int(m.group(1))
    left_attr = m.group(2)
    op = "==" if m.group(3) == "=" else m.group(3)
    right_raw = m.group(4).strip()

    if group_num < 1 or group_num > n:
        error(f"sigma condition '{condition}' uses group {group_num}, but n={n}.")
    if left_attr not in VALID_COLUMNS:
        error(f"sigma condition '{condition}' uses invalid attribute '{left_attr}'.")
    if op not in ("==", "!=", ">", "<", ">=", "<="):
        error(f"sigma condition '{condition}' uses unsupported operator.")

    if right_raw in VALID_COLUMNS:
        right_type, right_value, agg_ref = "group_attr", right_raw, None
    else:
        agg = _parse_agg(right_raw)
        if agg is not None:
            ref_group, ref_agg, ref_attr = agg
            if ref_group >= current_group:
                error(f"sigma '{condition}' references forward group {ref_group}.")
            _check_agg(ref_group, ref_agg, ref_attr, n, f"sigma '{condition}' right-side")
            if right_raw not in f_names:
                error(f"sigma '{condition}' references undefined aggregate '{right_raw}'.")
            right_type = "aggregate_field"
            right_value = right_raw
            agg_ref = {"group": ref_group, "agg": ref_agg, "attr": ref_attr}
        else:
            right_type, right_value, agg_ref = "literal", _parse_literal(right_raw), None

    return {"raw": condition, "group": group_num, "left_attr": left_attr,
            "op": op, "right_type": right_type, "right_value": right_value,
            "aggregate_ref": agg_ref}


def _parse_sigma(sigma, n, f_names):
    seen_groups, result = set(), []
    for condition_text in sigma:
        parts = _split_and(condition_text)
        matches = [_SIGMA_RE.match(p) for p in parts]
        if any(m is None for m in matches):
            error(f"sigma condition '{condition_text}' is invalid.")
        groups = {int(m.group(1)) for m in matches}
        if len(groups) != 1:
            error(f"sigma condition '{condition_text}' mixes grouping variables.")
        g = groups.pop()
        if g in seen_groups:
            error(f"sigma has two entries for group {g}.")
        seen_groups.add(g)
        predicates = [_parse_sigma_pred(p, n, g, f_names) for p in parts]
        result.append({"raw": condition_text, "group": g, "predicates": predicates})
    if len(seen_groups) != n:
        error("sigma must have exactly one condition per grouping variable.")
    return result


# --- G ---

_G_RE = re.compile(
    r"^\s*([a-zA-Z_]\w*|\d+_[a-zA-Z_]\w*_[a-zA-Z_]\w*)\s*(==|!=|>=|<=|=|>|<)\s*(.+?)\s*$"
)


def _parse_g_pred(condition, n, f_names):
    m = _G_RE.match(condition)
    if not m:
        error(f"G condition '{condition}' is invalid.")
    left_name = m.group(1)
    op = "==" if m.group(2) == "=" else m.group(2)
    right_raw = m.group(3).strip()

    if op not in ("==", "!=", ">", "<", ">=", "<="):
        error(f"G condition '{condition}' uses unsupported operator.")

    if left_name not in VALID_COLUMNS:
        group_num, agg_name, attr_name = _require_agg(left_name, "G condition left side")
        _check_agg(group_num, agg_name, attr_name, n, f"G '{condition}' left")
        if left_name not in f_names:
            error(f"G condition references undefined aggregate '{left_name}'.")

    if right_raw in VALID_COLUMNS:
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


def _parse_g(G_text, n, f_names):
    G_text = G_text.strip()
    if G_text.upper() == "NONE":
        return {"raw": G_text, "kind": "none", "predicates": []}
    predicate_texts = _split_and(G_text)
    return {"raw": G_text, "kind": "and_chain",
            "predicates": [_parse_g_pred(p, n, f_names) for p in predicate_texts]}


# --- Public entry point ---

def build_query_data(S, n, V, F, sigma, G):
    V = _parse_v(V)
    parsed_F = _parse_f(F, n)
    f_names = {item["raw"] for item in parsed_F}
    parsed_S = _parse_s(S, n, f_names)
    parsed_sigma = _parse_sigma(sigma, n, f_names)
    parsed_G = _parse_g(G, n, f_names)

    return {
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
