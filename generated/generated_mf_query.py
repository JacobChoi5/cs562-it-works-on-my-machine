
# Generated MF query program
# Run from project root with:
# python3 -m generated.generated_mf_query

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql import scan_sales_rows
from mf_query import execute_mf_query

MF_QUERY = {'F': [{'agg': 'sum', 'attr': 'quant', 'group': 1, 'raw': '1_sum_quant'},
       {'agg': 'avg', 'attr': 'quant', 'group': 1, 'raw': '1_avg_quant'},
       {'agg': 'count', 'attr': 'quant', 'group': 2, 'raw': '2_count_quant'},
       {'agg': 'avg', 'attr': 'quant', 'group': 2, 'raw': '2_avg_quant'},
       {'agg': 'min', 'attr': 'quant', 'group': 3, 'raw': '3_min_quant'},
       {'agg': 'max', 'attr': 'quant', 'group': 3, 'raw': '3_max_quant'}],
 'G': {'kind': 'and_chain',
       'predicates': [{'left_type': 'field',
                       'left_value': '3_max_quant',
                       'op': '>',
                       'raw': '3_max_quant > 1_avg_quant',
                       'right_type': 'field',
                       'right_value': '1_avg_quant'}],
       'raw': '3_max_quant > 1_avg_quant'},
 'S': ['cust',
       'prod',
       '1_sum_quant',
       '1_avg_quant',
       '2_count_quant',
       '2_avg_quant',
       '3_min_quant',
       '3_max_quant'],
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
                            'right_value': 'NJ'},
                           {'aggregate_ref': {'agg': 'avg',
                                              'attr': 'quant',
                                              'group': 1},
                            'group': 2,
                            'left_attr': 'quant',
                            'op': '>',
                            'raw': '2.quant>1_avg_quant',
                            'right_type': 'aggregate_field',
                            'right_value': '1_avg_quant'}],
            'raw': "2.state='NJ' and 2.quant>1_avg_quant"},
           {'group': 3,
            'predicates': [{'aggregate_ref': None,
                            'group': 3,
                            'left_attr': 'state',
                            'op': '==',
                            'raw': "3.state='CT'",
                            'right_type': 'literal',
                            'right_value': 'CT'},
                           {'aggregate_ref': {'agg': 'avg',
                                              'attr': 'quant',
                                              'group': 2},
                            'group': 3,
                            'left_attr': 'quant',
                            'op': '>',
                            'raw': '3.quant>2_avg_quant',
                            'right_type': 'aggregate_field',
                            'right_value': '2_avg_quant'}],
            'raw': "3.state='CT' and 3.quant>2_avg_quant"}]}


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
