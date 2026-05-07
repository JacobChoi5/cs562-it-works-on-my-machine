import operator as _op
from mf_structure import lookup_mf_entry, add_mf_entry, build_mf_structure_fields

_CMP = {"==": _op.eq, "!=": _op.ne, ">": _op.gt, "<": _op.lt, ">=": _op.ge, "<=": _op.le}


def build_mf_query(query_data):
    return {
        "n": query_data["n"],
        "S": query_data["S_raw"],
        "V": query_data["V"],
        "F": query_data["F"],
        "sigma": query_data["sigma"],
        "G": query_data["G"],
    }


def compare_values(left, op, right):
    if op not in _CMP:
        raise ValueError(f"Unsupported comparison operator: {op}")
    return _CMP[op](left, right)


def _resolve(entry, name):
    v = entry[name]
    return v["value"] if isinstance(v, dict) and "value" in v else v


def row_matches_sigma(row, entry, sigma):
    if sigma is None:
        return True
    for p in sigma.get("predicates", []):
        left = row[p["left_attr"]]
        rt = p["right_type"]
        if rt == "literal":
            right = p["right_value"]
        elif rt in ("group_attr", "aggregate_field"):
            right = _resolve(entry, p["right_value"])
        else:
            return False
        if not compare_values(left, p["op"], right):
            return False
    return True


def entry_matches_g(entry, G):
    if G["kind"] == "none":
        return True
    for p in G["predicates"]:
        left = _resolve(entry, p["left_value"])
        right = p["right_value"] if p["right_type"] == "literal" else _resolve(entry, p["right_value"])
        if not compare_values(left, p["op"], right):
            return False
    return True


def _update_agg(entry, item, row):
    n, a, v = item["raw"], item["agg"], row[item["attr"]]
    if a == "sum":
        entry[n] += v
    elif a == "count":
        entry[n] += 1
    elif a == "avg":
        entry[n]["sum"] += v
        entry[n]["count"] += 1
        entry[n]["value"] = entry[n]["sum"] / entry[n]["count"]
    elif a == "max":
        if entry[n] is None or v > entry[n]:
            entry[n] = v
    elif a == "min":
        if entry[n] is None or v < entry[n]:
            entry[n] = v


def execute_mf_query(rows, mf_query):
    mf_fields = build_mf_structure_fields({"V": mf_query["V"], "F": mf_query["F"]})
    table = []

    # scan 0: populate mf-table with distinct grouping attribute combinations
    for row in rows:
        if lookup_mf_entry(table, row, mf_query["V"]) == -1:
            add_mf_entry(table, row, mf_query["V"], mf_fields)

    # scans 1..n: one pass per grouping variable
    for g in range(1, mf_query["n"] + 1):
        sigma = next((s for s in mf_query["sigma"] if s["group"] == g), None)
        aggs = [a for a in mf_query["F"] if a["group"] == g]
        if not aggs:
            continue
        for row in rows:
            pos = lookup_mf_entry(table, row, mf_query["V"])
            if pos != -1 and row_matches_sigma(row, table[pos], sigma):
                for item in aggs:
                    _update_agg(table[pos], item, row)

    filtered = [e for e in table if entry_matches_g(e, mf_query["G"])]
    results = [{k: _resolve(e, k) for k in mf_query["S"]} for e in filtered]
    results.sort(key=lambda r: tuple(r[a] for a in mf_query["V"]))

    return mf_fields, table, filtered, results
