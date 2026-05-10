import os
import copy
import operator as op
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

COLUMN_TYPES = {
    "cust": "str",
    "prod": "str",
    "day": "int",
    "month": "int",
    "year": "int",
    "state": "str",
    "quant": "float",
    "date": "str",
}


def get_attribute_type(attr): # lookup data type for column
    return COLUMN_TYPES[attr]


def get_aggregate_result_type(agg, attr): # returns type of aggregate function
    if agg == "count": return "int"
    if agg == "avg": return "float"
    return get_attribute_type(attr)


def build_mf_structure_fields(query_data): # builds schema for mf table
    # duplication checks are purely defensive, should be gone by parser finish
    seen, fields = set(), [] # prevents duplicates, returns fields
    for attr in query_data["V"]: # processes grouping attributes
        if attr not in seen:
            fields.append({"name": attr, "kind": "group_attr", "source": attr,
                           "type": get_attribute_type(attr)})
            seen.add(attr)
    for item in query_data["F"]: # processes aggregate functions
        if item["raw"] not in seen: # prevents duplicate
            fields.append({"name": item["raw"], "kind": "aggregate",
                           "group": item.get("group"), "agg": item["agg"], "attr": item["attr"],
                           "type": get_aggregate_result_type(item["agg"], item["attr"])})
            seen.add(item["raw"])
    return fields


def build_empty_aggregate_value(field): # returns initial value for aggregate
    agg = field["agg"]
    if agg in ("sum", "count"): return 0
    if agg == "avg": return {"sum": 0, "count": 0, "value": 0}
    return None


def build_empty_mf_entry(mf_fields): # blank mf entry dict from field schema
    return {f["name"]: (None if f["kind"] == "group_attr" else build_empty_aggregate_value(f))
            for f in mf_fields}


def build_group_key(row, attrs): # pulls data from mf entry or row given grouping attributes
    return tuple(row[a] for a in attrs)


def lookup_mf_entry(table, row, attrs): # linear search for entry whose grouping attribute value matches given row
    key = build_group_key(row, attrs)
    return next((i for i, e in enumerate(table) if build_group_key(e, attrs) == key), -1) # returns index if found, -1 otherwise


def add_mf_entry(table, row, attrs, mf_fields): # creates new mf entry and appends to table
    entry = copy.deepcopy(build_empty_mf_entry(mf_fields)) # blank entry with 0'd aggregates
    for a in attrs: # fill in grouping attribute values
        entry[a] = row[a]
    table.append(entry)
    return len(table) - 1 # returns new entry index


CMP = {"==": op.eq, "!=": op.ne, ">": op.gt, "<": op.lt, ">=": op.ge, "<=": op.le} # translation of operators


def compare_values(left, operator, right): # checks if op in supported comparison ops and resolves
    if left is None or right is None: # NULL in any comparison = unknown = false, same as SQL
        return False
    if operator not in CMP:
        raise ValueError(f"Unsupported comparison operator: {operator}")
    return CMP[operator](left, right)


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
            pos = lookup_mf_entry(table, row, mf_query["V"]) # matches grouping attribute
            if pos != -1 and row_matches_sigma(row, table[pos], sigma): # checks filter, updates if passes
                for item in aggs:
                    update_agg(table[pos], item, row)

    filtered = [e for e in table if entry_matches_g(e, mf_query["G"])] # drops entries based on HAVING
    results = [{k: resolve(e, k) for k in mf_query["S"]} for e in filtered] # builds with only S columns and flattens aggregates
    results.sort(key=lambda r: tuple(r[a] for a in mf_query["V"])) # sorts by grouping aggregate

    return mf_fields, table, filtered, results # field schema, full table, filtered table, and projected results


def get_db_connection(): # establishes PostgreSQL database connection
    # keep connection setup simple and driven by env vars
    # way cleaner than hardcoding creds into the project
    load_dotenv()
    try:
        return psycopg2.connect( # uses local environment to establish connection
            host=os.getenv("PGHOST", "localhost"),
            port=os.getenv("PGPORT", "5432"),
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
        )
    except Exception as exc:
        raise RuntimeError(f"Could not connect to PostgreSQL: {exc}")


def scan_sales_rows():
    # generator that yields one row at a time from the sales table
    # this keeps us in the cursor/scan mindset the project wants
    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor: # turns result into python dict
            cursor.execute( # full scan query of sales table to dictionary form
                """
                SELECT cust, prod, day, month, year, state, quant, date
                FROM sales
                """
            )
            for row in cursor:
                yield dict(row) # produces over time
    finally:
        connection.close()


MF_QUERY = {'F': [{'agg': 'sum', 'attr': 'quant', 'group': 1, 'raw': '1_sum_quant'},
       {'agg': 'avg', 'attr': 'quant', 'group': 1, 'raw': '1_avg_quant'},
       {'agg': 'sum', 'attr': 'quant', 'group': 2, 'raw': '2_sum_quant'},
       {'agg': 'avg', 'attr': 'quant', 'group': 2, 'raw': '2_avg_quant'},
       {'agg': 'sum', 'attr': 'quant', 'group': 3, 'raw': '3_sum_quant'},
       {'agg': 'min', 'attr': 'quant', 'group': 3, 'raw': '3_min_quant'}],
 'G': {'kind': 'and_chain',
       'predicates': [{'left_type': 'field',
                       'left_value': '1_sum_quant',
                       'op': '>',
                       'raw': '1_sum_quant > 2_sum_quant',
                       'right_type': 'field',
                       'right_value': '2_sum_quant'}],
       'raw': '1_sum_quant > 2_sum_quant'},
 'S': ['cust',
       'prod',
       '1_sum_quant',
       '1_avg_quant',
       '2_sum_quant',
       '2_avg_quant',
       '3_sum_quant',
       '3_min_quant'],
 'V': ['cust', 'prod'],
 'n': 3,
 'sigma': [{'group': 1,
            'predicates': [{'aggregate_ref': None,
                            'group': 1,
                            'left_attr': 'state',
                            'op': '==',
                            'raw': "1.state='NY'",
                            'right_type': 'literal',
                            'right_value': 'NY'}],
            'raw': "1.state='NY'"},
           {'group': 2,
            'predicates': [{'aggregate_ref': None,
                            'group': 2,
                            'left_attr': 'state',
                            'op': '==',
                            'raw': "2.state='NJ'",
                            'right_type': 'literal',
                            'right_value': 'NJ'}],
            'raw': "2.state='NJ'"},
           {'group': 3,
            'predicates': [{'aggregate_ref': None,
                            'group': 3,
                            'left_attr': 'state',
                            'op': '==',
                            'raw': "3.state='CT'",
                            'right_type': 'literal',
                            'right_value': 'CT'}],
            'raw': "3.state='CT'"}]}


def main():
    rows = list(scan_sales_rows())
    _, _, _, results = execute_mf_query(rows, MF_QUERY)

    print('Generated MF query results:')
    if not results:
        print('  No rows matched.')
    else:
        for row in results:
            print(' ', row)


if __name__ == '__main__':
    main()
