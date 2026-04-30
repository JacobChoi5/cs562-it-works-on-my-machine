import copy

from config import COLUMN_TYPES


def get_attribute_type(attribute_name):
    return COLUMN_TYPES[attribute_name]


def get_aggregate_result_type(agg_name, attribute_name):
    if agg_name == "count":
        return "int"

    if agg_name == "avg":
        return "float"

    return get_attribute_type(attribute_name)


def build_mf_structure_fields(query_data):
    fields = []
    seen_names = set()

    # grouping attributes first
    for attribute in query_data["V"]:
        if attribute not in seen_names:
            fields.append({
                "name": attribute,
                "kind": "group_attr",
                "source": attribute,
                "type": get_attribute_type(attribute)
            })
            seen_names.add(attribute)

    # aggregate outputs second
    for agg_item in query_data["F"]:
        field_name = agg_item["raw"]

        if field_name not in seen_names:
            fields.append({
                "name": field_name,
                "kind": "aggregate",
                "group": agg_item["group"],
                "agg": agg_item["agg"],
                "attr": agg_item["attr"],
                "type": get_aggregate_result_type(agg_item["agg"], agg_item["attr"])
            })
            seen_names.add(field_name)

    return fields


def build_empty_aggregate_value(field):
    agg_name = field["agg"]

    if agg_name == "sum":
        return 0

    if agg_name == "count":
        return 0

    if agg_name == "avg":
        return {
            "sum": 0,
            "count": 0,
            "value": 0
        }

    if agg_name == "min":
        return None

    if agg_name == "max":
        return None

    return None


def build_empty_mf_entry(mf_fields):
    # one blank mf row
    entry = {}

    for field in mf_fields:
        if field["kind"] == "group_attr":
            entry[field["name"]] = None
        elif field["kind"] == "aggregate":
            entry[field["name"]] = build_empty_aggregate_value(field)

    return entry


def build_group_key(row, grouping_attributes):
    key_values = []

    for attribute in grouping_attributes:
        key_values.append(row[attribute])

    return tuple(key_values)


def lookup_mf_entry(mf_table, row, grouping_attributes):
    # plain linear search for now
    target_key = build_group_key(row, grouping_attributes)

    for index, entry in enumerate(mf_table):
        entry_key = build_group_key(entry, grouping_attributes)

        if entry_key == target_key:
            return index

    return -1


def add_mf_entry(mf_table, row, grouping_attributes, mf_fields):
    new_entry = copy.deepcopy(build_empty_mf_entry(mf_fields))

    for attribute in grouping_attributes:
        new_entry[attribute] = row[attribute]

    mf_table.append(new_entry)
    return len(mf_table) - 1