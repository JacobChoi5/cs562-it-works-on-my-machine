import subprocess
from pprint import pformat

from mf_structure import build_empty_mf_entry, build_mf_structure_fields, get_attribute_type, get_aggregate_result_type


# builds the mf_fields list for the hardcoded warmup simple query
# only used for the handout demo — not for real MF queries
def build_simple_mf_fields(simple_query):
    fields = []
    seen = set()
    for attr in simple_query["V"]:
        if attr not in seen:
            fields.append({"name": attr, "kind": "group_attr", "source": attr,
                           "type": get_attribute_type(attr)})
            seen.add(attr)
    for item in simple_query["F"]:
        if item["raw"] not in seen:
            fields.append({"name": item["raw"], "kind": "aggregate",
                           "agg": item["agg"], "attr": item["attr"],
                           "type": get_aggregate_result_type(item["agg"], item["attr"])})
            seen.add(item["raw"])
    return fields


# generates python code that sets up the MF structure (entry template, empty table, row count)
# writes it to _generated.py and runs it to make sure it's valid
def generate_python_mf_structure_code(mf_fields):
    empty_entry = build_empty_mf_entry(mf_fields)

    tmp = f"""
# Generated mf-structure setup

MF_ENTRY_TEMPLATE = {pformat(empty_entry)}

mf_table = []

NUM_OF_ENTRIES = 0
"""

    open("_generated.py", "w").write(tmp)
    subprocess.run(["python", "_generated.py"])
    return tmp


# generates a standalone python program for the warmup simple query from the handout
# this is hardcoded on purpose — it's specifically the required demo, not meant to be general
# scans sales rows, filters them, builds mf entries, updates aggregates, prints results
def generate_python_simple_query_code(simple_query):
    mf_fields = build_simple_mf_fields(simple_query)
    empty_entry = build_empty_mf_entry(mf_fields)

    tmp = f"""
# Generated simple query program
# Run from project root with:
# python3 -m generated.generated_simple_query

import sys
import os
import copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql import scan_sales_rows
from mf_structure import lookup_mf_entry, add_mf_entry

SIMPLE_QUERY = {pformat(simple_query)}
MF_FIELDS = {pformat(mf_fields)}
MF_ENTRY_TEMPLATE = {pformat(empty_entry)}

import operator as _op
_CMP = {{'==': _op.eq, '!=': _op.ne, '>': _op.gt, '<': _op.lt, '>=': _op.ge, '<=': _op.le}}


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

    results = [{{k: resolve(e[k]) for k in SIMPLE_QUERY['S']}} for e in table]
    print('Generated simple query results:')
    for row in results:
        print(' ', row)


if __name__ == '__main__':
    main()
"""

    open("_generated.py", "w").write(tmp)
    subprocess.run(["python", "_generated.py"])
    return tmp


# generates a standalone python program for running a full MF query
# takes the parsed mf_query dict and writes a complete runnable script that loads sales rows and prints results
def generate_python_mf_query_code(mf_query):
    tmp = f"""
# Generated MF query program
# Run from project root with:
# python3 -m generated.generated_mf_query

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql import scan_sales_rows
from mf_query import execute_mf_query

MF_QUERY = {pformat(mf_query)}


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
"""

    open("_generated.py", "w").write(tmp)
    subprocess.run(["python", "_generated.py"])
    return tmp


# saves a generated code string to a file
def save_generated_code(filename, code_text):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code_text)
