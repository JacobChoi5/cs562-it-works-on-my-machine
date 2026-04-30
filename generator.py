import subprocess
 
from mf_structure import build_empty_mf_entry, build_mf_structure_fields, get_attribute_type, get_aggregate_result_type


def build_simple_mf_fields(simple_query):
    # builds the mf field list for a simple (non-MF) grouping query
    # same structure as the full mf fields, just without grouping-variable numbering
    fields = []
    seen_names = set()

    for attribute in simple_query["V"]:
        if attribute not in seen_names:
            fields.append({
                "name": attribute,
                "kind": "group_attr",
                "source": attribute,
                "type": get_attribute_type(attribute)
            })
            seen_names.add(attribute)

    for agg_item in simple_query["F"]:
        field_name = agg_item["raw"]

        if field_name not in seen_names:
            fields.append({
                "name": field_name,
                "kind": "aggregate",
                "agg": agg_item["agg"],
                "attr": agg_item["attr"],
                "type": get_aggregate_result_type(agg_item["agg"], agg_item["attr"])
            })
            seen_names.add(field_name)

    return fields
 
 
def python_literal(value, indent_level=0):
    indent = " " * indent_level
 
    if isinstance(value, dict):
        if len(value) == 0:
            return "{}"
 
        lines = ["{"]
        items = list(value.items())
 
        for index, (key, val) in enumerate(items):
            comma = "," if index < len(items) - 1 else ""
            val_text = python_literal(val, indent_level + 4)
            lines.append(f'{" " * (indent_level + 4)}{repr(key)}: {val_text}{comma}')
 
        lines.append(f"{indent}}}")
        return "\n".join(lines)
 
    if isinstance(value, list):
        if len(value) == 0:
            return "[]"
 
        lines = ["["]
        for index, item in enumerate(value):
            comma = "," if index < len(value) - 1 else ""
            item_text = python_literal(item, indent_level + 4)
            lines.append(f'{" " * (indent_level + 4)}{item_text}{comma}')
        lines.append(f"{indent}]")
        return "\n".join(lines)
 
    return repr(value)
 
 
def generate_python_mf_structure_code(mf_fields):
    empty_entry = build_empty_mf_entry(mf_fields)
 
    tmp = f"""
# ------------------------------------------------------------
# Generated mf-structure setup
# ------------------------------------------------------------
 
MF_ENTRY_TEMPLATE = {python_literal(empty_entry)}
 
mf_table = []
 
NUM_OF_ENTRIES = 0
"""
 
    open("_generated.py", "w").write(tmp)
    subprocess.run(["python", "_generated.py"])
    return tmp
 
 
def generate_python_simple_query_code(simple_query):
    mf_fields = build_simple_mf_fields(simple_query)
    empty_entry = build_empty_mf_entry(mf_fields)
 
    tmp = f"""
# ------------------------------------------------------------
# Generated simple query program
# Run from project root with:
# python3 -m generated.generated_simple_query
# ------------------------------------------------------------
 
import copy
from sql import scan_sales_rows
 
SIMPLE_QUERY = {python_literal(simple_query)}
 
MF_FIELDS = {python_literal(mf_fields)}
 
MF_ENTRY_TEMPLATE = {python_literal(empty_entry)}
 
 
def build_group_key(row, grouping_attributes):
    key_values = []
    for attribute in grouping_attributes:
        key_values.append(row[attribute])
    return tuple(key_values)
 
 
def lookup_mf_entry(mf_table, row, grouping_attributes):
    target_key = build_group_key(row, grouping_attributes)
    for index, entry in enumerate(mf_table):
        entry_key = build_group_key(entry, grouping_attributes)
        if entry_key == target_key:
            return index
    return -1
 
 
def add_mf_entry(mf_table, row, grouping_attributes):
    new_entry = copy.deepcopy(MF_ENTRY_TEMPLATE)
    for attribute in grouping_attributes:
        new_entry[attribute] = row[attribute]
    mf_table.append(new_entry)
    return len(mf_table) - 1
 
 
def row_matches_filters(row, filters):
    for rule in filters:
        left = row[rule['attribute']]
        right = rule['value']
        op = rule['op']
 
        if op == '==':
            if left != right:
                return False
        elif op == '!=':
            if left == right:
                return False
        elif op == '>':
            if left <= right:
                return False
        elif op == '<':
            if left >= right:
                return False
        elif op == '>=':
            if left < right:
                return False
        elif op == '<=':
            if left > right:
                return False
        else:
            raise ValueError(f'Unsupported filter operator: {{op}}')
 
    return True
 
 
def update_one_simple_aggregate(entry, field, row):
    field_name = field['name']
    agg_name = field['agg']
    attr_name = field['attr']
    value = row[attr_name]
 
    if agg_name == 'sum':
        entry[field_name] += value
        return
 
    if agg_name == 'count':
        entry[field_name] += 1
        return
 
    if agg_name == 'avg':
        entry[field_name]['sum'] += value
        entry[field_name]['count'] += 1
        if entry[field_name]['count'] > 0:
            entry[field_name]['value'] = (
                entry[field_name]['sum'] / entry[field_name]['count']
            )
        return
 
    if agg_name == 'max':
        if entry[field_name] is None or value > entry[field_name]:
            entry[field_name] = value
        return
 
    if agg_name == 'min':
        if entry[field_name] is None or value < entry[field_name]:
            entry[field_name] = value
        return
 
 
def update_simple_aggregates(entry, row, mf_fields):
    for field in mf_fields:
        if field['kind'] == 'aggregate':
            update_one_simple_aggregate(entry, field, row)
 
 
def project_simple_results(mf_table, select_list):
    results = []
    for entry in mf_table:
        result_row = {{}}
        for item in select_list:
            value = entry[item]
            if isinstance(value, dict) and 'value' in value:
                result_row[item] = value['value']
            else:
                result_row[item] = value
        results.append(result_row)
    return results
 
 
def main():
    mf_table = []
 
    for row in scan_sales_rows():
        if not row_matches_filters(row, SIMPLE_QUERY['where']):
            continue
 
        pos = lookup_mf_entry(mf_table, row, SIMPLE_QUERY['V'])
 
        if pos == -1:
            pos = add_mf_entry(mf_table, row, SIMPLE_QUERY['V'])
 
        update_simple_aggregates(mf_table[pos], row, MF_FIELDS)
 
    results = project_simple_results(mf_table, SIMPLE_QUERY['S'])
 
    print('Generated simple query results:')
    for row in results:
        print(' ', row)
 
 
if __name__ == '__main__':
    main()
"""
 
    open("_generated.py", "w").write(tmp)
    subprocess.run(["python", "_generated.py"])
    return tmp
 
 
def generate_python_mf_query_code(mf_query):
    mf_fields = build_mf_structure_fields({
        "V": mf_query["V"],
        "F": mf_query["F"]
    })
    empty_entry = build_empty_mf_entry(mf_fields)
 
    tmp = f"""
# ------------------------------------------------------------
# Generated MF query program
# Run from project root with:
# python3 -m generated.generated_mf_query
# ------------------------------------------------------------
 
import copy
from sql import scan_sales_rows
 
MF_QUERY = {python_literal(mf_query)}
 
MF_FIELDS = {python_literal(mf_fields)}
 
MF_ENTRY_TEMPLATE = {python_literal(empty_entry)}
 
 
def build_group_key(row, grouping_attributes):
    key_values = []
    for attribute in grouping_attributes:
        key_values.append(row[attribute])
    return tuple(key_values)
 
 
def lookup_mf_entry(mf_table, row, grouping_attributes):
    target_key = build_group_key(row, grouping_attributes)
    for index, entry in enumerate(mf_table):
        entry_key = build_group_key(entry, grouping_attributes)
        if entry_key == target_key:
            return index
    return -1
 
 
def add_mf_entry(mf_table, row, grouping_attributes):
    new_entry = copy.deepcopy(MF_ENTRY_TEMPLATE)
    for attribute in grouping_attributes:
        new_entry[attribute] = row[attribute]
    mf_table.append(new_entry)
    return len(mf_table) - 1
 
 
def compare_values(left, op, right):
    if op == '==':
        return left == right
    if op == '!=':
        return left != right
    if op == '>':
        return left > right
    if op == '<':
        return left < right
    if op == '>=':
        return left >= right
    if op == '<=':
        return left <= right
    raise ValueError(f'Unsupported comparison operator: {{op}}')
 
 
def get_entry_value(entry, value_type, value_name):
    if value_type == 'field':
        value = entry[value_name]
        if isinstance(value, dict) and 'value' in value:
            return value['value']
        return value
    raise ValueError(f'Unsupported entry value type: {{value_type}}')
 
 
def get_sigma_object_for_group(sigma_objects, group_num):
    for sigma_object in sigma_objects:
        if sigma_object['group'] == group_num:
            return sigma_object
    return None
 
 
def get_aggregates_for_group(aggregate_objects, group_num):
    group_aggs = []
    for agg_item in aggregate_objects:
        if agg_item['group'] == group_num:
            group_aggs.append(agg_item)
    return group_aggs
 
 
def row_matches_sigma_object(row, entry, sigma_object):
    if sigma_object is None:
        return True
 
    predicates = sigma_object.get('predicates', [])
 
    for predicate in predicates:
        left_value = row[predicate['left_attr']]
 
        if predicate['right_type'] == 'literal':
            right_value = predicate['right_value']
        elif predicate['right_type'] == 'group_attr':
            right_value = entry[predicate['right_value']]
        elif predicate['right_type'] == 'aggregate_field':
            right_value = entry[predicate['right_value']]
            if isinstance(right_value, dict) and 'value' in right_value:
                right_value = right_value['value']
        else:
            return False
 
        if not compare_values(left_value, predicate['op'], right_value):
            return False
 
    return True
 
 
def entry_matches_g(entry, G_object):
    if G_object['kind'] == 'none':
        return True
 
    for predicate in G_object['predicates']:
        left_value = get_entry_value(entry, predicate['left_type'], predicate['left_value'])
 
        if predicate['right_type'] == 'literal':
            right_value = predicate['right_value']
        elif predicate['right_type'] == 'field':
            right_value = get_entry_value(entry, 'field', predicate['right_value'])
        else:
            return False
 
        if not compare_values(left_value, predicate['op'], right_value):
            return False
 
    return True
 
 
def update_one_mf_aggregate(entry, agg_item, row):
    field_name = agg_item['raw']
    agg_name = agg_item['agg']
    attr_name = agg_item['attr']
    value = row[attr_name]
 
    if agg_name == 'sum':
        entry[field_name] += value
        return
 
    if agg_name == 'count':
        entry[field_name] += 1
        return
 
    if agg_name == 'avg':
        entry[field_name]['sum'] += value
        entry[field_name]['count'] += 1
        if entry[field_name]['count'] > 0:
            entry[field_name]['value'] = (
                entry[field_name]['sum'] / entry[field_name]['count']
            )
        return
 
    if agg_name == 'max':
        if entry[field_name] is None or value > entry[field_name]:
            entry[field_name] = value
        return
 
    if agg_name == 'min':
        if entry[field_name] is None or value < entry[field_name]:
            entry[field_name] = value
        return
 
 
def update_mf_aggregates(entry, aggregate_objects, row):
    for agg_item in aggregate_objects:
        update_one_mf_aggregate(entry, agg_item, row)
 
 
def apply_g_filter(mf_table, G_object):
    filtered_entries = []
    for entry in mf_table:
        if entry_matches_g(entry, G_object):
            filtered_entries.append(entry)
    return filtered_entries
 
 
def project_mf_results(mf_table, select_list, grouping_attributes):
    results = []
    for entry in mf_table:
        result_row = {{}}
        for item in select_list:
            value = entry[item]
            if isinstance(value, dict) and 'value' in value:
                result_row[item] = value['value']
            else:
                result_row[item] = value
        results.append(result_row)
    results.sort(key=lambda row: tuple(row[attr] for attr in grouping_attributes))
    return results
 
 
def main():
    rows = list(scan_sales_rows())
    mf_table = []
 
    for row in rows:
        pos = lookup_mf_entry(mf_table, row, MF_QUERY['V'])
        if pos == -1:
            add_mf_entry(mf_table, row, MF_QUERY['V'])
 
    for group_num in range(1, MF_QUERY['n'] + 1):
        sigma_object = get_sigma_object_for_group(MF_QUERY['sigma'], group_num)
        aggregate_objects = get_aggregates_for_group(MF_QUERY['F'], group_num)
 
        if len(aggregate_objects) == 0:
            continue
 
        for row in rows:
            pos = lookup_mf_entry(mf_table, row, MF_QUERY['V'])
            if pos == -1:
                continue
 
            entry = mf_table[pos]
 
            if row_matches_sigma_object(row, entry, sigma_object):
                update_mf_aggregates(entry, aggregate_objects, row)
 
    filtered_table = apply_g_filter(mf_table, MF_QUERY['G'])
    results = project_mf_results(filtered_table, MF_QUERY['S'], MF_QUERY['V'])
 
    print('Generated MF query results:')
    if len(results) == 0:
        print('  No rows matched.')
    else:
        for row in results:
            print(' ', row)
 
 
if __name__ == '__main__':
    main()
"""
 
    open("_generated.py", "w").write(tmp)
    subprocess.run(["python", "_generated.py"])
    return tmp

def save_generated_code(filename, code_text):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(code_text)