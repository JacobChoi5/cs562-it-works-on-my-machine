import copy
from config import COLUMN_TYPES


def get_attribute_type(attr): # lookup data type for column
    return COLUMN_TYPES[attr]


def get_aggregate_result_type(agg, attr): # returns type of aggregate function
    if agg == "count": return "int"
    if agg == "avg": return "float" # average always float even if input (quant) is int
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
    return None  # min, max


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