
# ------------------------------------------------------------
# Generated simple query program
# Run from project root with:
# python3 -m generated.generated_simple_query
# ------------------------------------------------------------
 
import copy
from sql import scan_sales_rows
 
SIMPLE_QUERY = {
    'S': [
        'cust',
        'prod',
        'avg_quant',
        'max_quant'
    ],
    'V': [
        'cust',
        'prod'
    ],
    'F': [
        {
            'raw': 'avg_quant',
            'agg': 'avg',
            'attr': 'quant'
        },
        {
            'raw': 'max_quant',
            'agg': 'max',
            'attr': 'quant'
        }
    ],
    'where': [
        {
            'attribute': 'year',
            'op': '==',
            'value': 2009
        }
    ]
}
 
MF_FIELDS = [
    {
        'name': 'cust',
        'kind': 'group_attr',
        'source': 'cust',
        'type': 'str'
    },
    {
        'name': 'prod',
        'kind': 'group_attr',
        'source': 'prod',
        'type': 'str'
    },
    {
        'name': 'avg_quant',
        'kind': 'aggregate',
        'agg': 'avg',
        'attr': 'quant',
        'type': 'float'
    },
    {
        'name': 'max_quant',
        'kind': 'aggregate',
        'agg': 'max',
        'attr': 'quant',
        'type': 'float'
    }
]
 
MF_ENTRY_TEMPLATE = {
    'cust': None,
    'prod': None,
    'avg_quant': {
        'sum': 0,
        'count': 0,
        'value': 0
    },
    'max_quant': None
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
            raise ValueError(f'Unsupported filter operator: {op}')
 
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
        result_row = {}
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
