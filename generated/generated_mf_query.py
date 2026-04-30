
# ------------------------------------------------------------
# Generated MF query program
# Run from project root with:
# python3 -m generated.generated_mf_query
# ------------------------------------------------------------
 
import copy
from sql import scan_sales_rows
 
MF_QUERY = {
    'n': 1,
    'S': [
        'cust',
        '1_count_quant'
    ],
    'V': [
        'cust'
    ],
    'F': [
        {
            'raw': '1_count_quant',
            'group': 1,
            'agg': 'count',
            'attr': 'quant'
        }
    ],
    'sigma': [
        {
            'raw': "1.state='NY' and 1.year=2009",
            'group': 1,
            'predicates': [
                {
                    'raw': "1.state='NY'",
                    'group': 1,
                    'left_attr': 'state',
                    'op': '==',
                    'right_type': 'literal',
                    'right_value': 'NY',
                    'aggregate_ref': None
                },
                {
                    'raw': '1.year=2009',
                    'group': 1,
                    'left_attr': 'year',
                    'op': '==',
                    'right_type': 'literal',
                    'right_value': 2009,
                    'aggregate_ref': None
                }
            ]
        }
    ],
    'G': {
        'raw': 'none',
        'kind': 'none',
        'predicates': []
    }
}
 
MF_FIELDS = [
    {
        'name': 'cust',
        'kind': 'group_attr',
        'source': 'cust',
        'type': 'str'
    },
    {
        'name': '1_count_quant',
        'kind': 'aggregate',
        'group': 1,
        'agg': 'count',
        'attr': 'quant',
        'type': 'int'
    }
]
 
MF_ENTRY_TEMPLATE = {
    'cust': None,
    '1_count_quant': 0
}
 
 
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
    raise ValueError(f'Unsupported comparison operator: {op}')
 
 
def get_entry_value(entry, value_type, value_name):
    if value_type == 'field':
        value = entry[value_name]
        if isinstance(value, dict) and 'value' in value:
            return value['value']
        return value
    raise ValueError(f'Unsupported entry value type: {value_type}')
 
 
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
        result_row = {}
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
