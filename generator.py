import subprocess
from pprint import pformat

from mf_structure import build_empty_mf_entry, build_mf_structure_fields


# generates python code that sets up the MF structure (entry template, empty table, row count)
# writes it to _generated.py and runs it to make sure it's valid
def generate_python_mf_structure_code(mf_fields):
    empty_entry = build_empty_mf_entry(mf_fields)

    tmp = f"""
# Generated mf-structure setup

MF_ENTRY_TEMPLATE = {pformat(empty_entry)}

NUM_OF_ENTRIES = 0
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
