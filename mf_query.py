import operator as op
from mf_structure import lookup_mf_entry, add_mf_entry, build_mf_structure_fields

CMP = {"==": op.eq, "!=": op.ne, ">": op.gt, "<": op.lt, ">=": op.ge, "<=": op.le} # translation of operators


def build_mf_query(query_data): # reshapes the raw parsed query dict into mf query structure
    return {
        "n": query_data["n"], # number grouping vars
        "S": query_data["S_raw"], # SELECT attributes (actual column names)
        "V": query_data["V"], # grouping attributes
        "F": query_data["F"], # aggregate functions
        "sigma": query_data["sigma"], # filter predicates
        "G": query_data["G"], # HAVING predicate
    }


def compare_values(left, op, right): # checks if op in supported comparison ops and resolves
    if left is None or right is None: # NULL in any comparison = unknown = false, same as SQL
        return False
    if op not in CMP:
        raise ValueError(f"Unsupported comparison operator: {op}")
    return CMP[op](left, right)


def resolve(entry, name): # helper for aggregates: avg stored with sum count and value, returns just value
    v = entry[name]
    return v["value"] if isinstance(v, dict) and "value" in v else v # only avg holds "value"

# checks whether raw database row satisfies sigma for one grouping variable
def row_matches_sigma(row, entry, sigma):
    if sigma is None: # no predicate: always passes
        return True
    for p in sigma.get("predicates", []):
        left = row[p["left_attr"]] # quality from row
        rt = p["right_type"]
        if rt == "literal":
            right = p["right_value"]
        elif rt in ("group_attr", "aggregate_field"): # aggregate_field precomputed
            right = resolve(entry, p["right_value"]) # only necessary for avg
        else:
            return False
        if not compare_values(left, p["op"], right):
            return False
    return True


def entry_matches_g(entry, G): # applies HAVING clause
    if G["kind"] == "none":
        return True
    for p in G["predicates"]:
        left = resolve(entry, p["left_value"])
        right = p["right_value"] if p["right_type"] == "literal" else resolve(entry, p["right_value"]) # either literal or aggregate to be resolved
        if not compare_values(left, p["op"], right): # checks comparison
            return False
    return True


def update_agg(entry, item, row): # updates all aggregates
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


def sigma_has_cross_entry_predicates(sigma):
    if sigma is None:
        return False
    return any(p["right_type"] == "group_attr" for p in sigma.get("predicates", []))


def execute_mf_query(rows, mf_query):
    # builds structure
    mf_fields = build_mf_structure_fields({"V": mf_query["V"], "F": mf_query["F"]})
    table = []

    # scan 0: populate mf-table with distinct grouping attribute combinations
    for row in rows:
        if lookup_mf_entry(table, row, mf_query["V"]) == -1: # existence check
            add_mf_entry(table, row, mf_query["V"], mf_fields)

    # scans 1..n: one pass per grouping variable
    for g in range(1, mf_query["n"] + 1):
        sigma = next((s for s in mf_query["sigma"] if s["group"] == g), None)
        aggs = [a for a in mf_query["F"] if a["group"] == g]
        if not aggs:
            continue
        for row in rows:
            if sigma_has_cross_entry_predicates(sigma):
                # group_attr predicates compare row columns against other entries' attributes,
                # so we must test the row against every entry, not just the one matching the row's key
                for i, entry in enumerate(table):
                    if row_matches_sigma(row, entry, sigma):
                        for item in aggs:
                            update_agg(table[i], item, row)
            else:
                pos = lookup_mf_entry(table, row, mf_query["V"]) # matches grouping attribute
                if pos != -1 and row_matches_sigma(row, table[pos], sigma): # checks filter, updates if passes
                    for item in aggs:
                        update_agg(table[pos], item, row)

    filtered = [e for e in table if entry_matches_g(e, mf_query["G"])] # drops entries based on HAVING
    results = [{k: resolve(e, k) for k in mf_query["S"]} for e in filtered] # builds with only S columns and flattens aggregates
    results.sort(key=lambda r: tuple(r[a] for a in mf_query["V"])) # sorts by grouping aggregate

    return mf_fields, table, filtered, results # field schema, full table, filtered table, and projected results
