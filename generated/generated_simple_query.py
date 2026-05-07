
# ------------------------------------------------------------
# Generated simple query program
# Run from project root with:
# python3 -m generated.generated_simple_query
# ------------------------------------------------------------

import sys
import os
import copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql import scan_sales_rows
from mf_structure import lookup_mf_entry, add_mf_entry

SIMPLE_QUERY = {'F': [{'agg': 'avg', 'attr': 'quant', 'raw': 'avg_quant'},
       {'agg': 'max', 'attr': 'quant', 'raw': 'max_quant'}],
 'S': ['cust', 'prod', 'avg_quant', 'max_quant'],
 'V': ['cust', 'prod'],
 'where': [{'attribute': 'year', 'op': '==', 'value': 2009}]}
MF_FIELDS = [{'kind': 'group_attr', 'name': 'cust', 'source': 'cust', 'type': 'str'},
 {'kind': 'group_attr', 'name': 'prod', 'source': 'prod', 'type': 'str'},
 {'agg': 'avg',
  'attr': 'quant',
  'kind': 'aggregate',
  'name': 'avg_quant',
  'type': 'float'},
 {'agg': 'max',
  'attr': 'quant',
  'kind': 'aggregate',
  'name': 'max_quant',
  'type': 'float'}]
MF_ENTRY_TEMPLATE = {'avg_quant': {'count': 0, 'sum': 0, 'value': 0},
 'cust': None,
 'max_quant': None,
 'prod': None}

import operator as _op
_CMP = {'==': _op.eq, '!=': _op.ne, '>': _op.gt, '<': _op.lt, '>=': _op.ge, '<=': _op.le}


def matches_filters(row, filters):
    return all(_CMP[f['op']](row[f['attribute']], f['value']) for f in filters)


def update_aggs(entry, row):
    for f in MF_FIELDS:
        if f['kind'] != 'aggregate':
            continue
        v, n, a = row[f['attr']], f['name'], f['agg']
        if a == 'sum':
            entry[n] += v
        elif a == 'count':
            entry[n] += 1
        elif a == 'avg':
            entry[n]['sum'] += v
            entry[n]['count'] += 1
            entry[n]['value'] = entry[n]['sum'] / entry[n]['count']
        elif a == 'max':
            if entry[n] is None or v > entry[n]: entry[n] = v
        elif a == 'min':
            if entry[n] is None or v < entry[n]: entry[n] = v


def resolve(v):
    return v['value'] if isinstance(v, dict) and 'value' in v else v


def main():
    table = []
    for row in scan_sales_rows():
        if not matches_filters(row, SIMPLE_QUERY['where']):
            continue
        pos = lookup_mf_entry(table, row, SIMPLE_QUERY['V'])
        if pos == -1:
            pos = add_mf_entry(table, row, SIMPLE_QUERY['V'], MF_FIELDS)
        update_aggs(table[pos], row)

    results = [{k: resolve(e[k]) for k in SIMPLE_QUERY['S']} for e in table]
    print('Generated simple query results:')
    for row in results:
        print(' ', row)


if __name__ == '__main__':
    main()
