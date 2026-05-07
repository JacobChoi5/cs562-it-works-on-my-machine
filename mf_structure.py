import copy
from config import COLUMN_TYPES


def get_attribute_type(attr):
    return COLUMN_TYPES[attr]


def get_aggregate_result_type(agg, attr):
    if agg == "count": return "int"
    if agg == "avg": return "float"
    return get_attribute_type(attr)


def build_mf_structure_fields(query_data):
    seen, fields = set(), []
    for attr in query_data["V"]:
        if attr not in seen:
            fields.append({"name": attr, "kind": "group_attr", "source": attr,
                           "type": get_attribute_type(attr)})
            seen.add(attr)
    for item in query_data["F"]:
        if item["raw"] not in seen:
            fields.append({"name": item["raw"], "kind": "aggregate",
                           "group": item.get("group"), "agg": item["agg"], "attr": item["attr"],
                           "type": get_aggregate_result_type(item["agg"], item["attr"])})
            seen.add(item["raw"])
    return fields


def build_empty_aggregate_value(field):
    agg = field["agg"]
    if agg in ("sum", "count"): return 0
    if agg == "avg": return {"sum": 0, "count": 0, "value": 0}
    return None  # min, max


def build_empty_mf_entry(mf_fields):
    return {f["name"]: (None if f["kind"] == "group_attr" else build_empty_aggregate_value(f))
            for f in mf_fields}


def build_group_key(row, attrs):
    return tuple(row[a] for a in attrs)


def lookup_mf_entry(table, row, attrs):
    key = build_group_key(row, attrs)
    return next((i for i, e in enumerate(table) if build_group_key(e, attrs) == key), -1)


def add_mf_entry(table, row, attrs, mf_fields):
    entry = copy.deepcopy(build_empty_mf_entry(mf_fields))
    for a in attrs:
        entry[a] = row[a]
    table.append(entry)
    return len(table) - 1
