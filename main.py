import sys
from parser import build_query_data, error, split_input
from mf_structure import build_mf_structure_fields
from generator import (
    generate_python_mf_structure_code,
    generate_python_simple_query_code,
    generate_python_mf_query_code,
    save_generated_code,
)
from mf_query import build_mf_query, execute_mf_query
from sql import scan_sales_rows


# prints a summary of the query after its been accepted
def print_query_summary(query_data):
    print("\nQuery accepted.")
    print(f"n = {query_data['n']}")
    print(f"V = {query_data['V']}")
    print(f"S = {query_data['S_raw']}")
    print(f"F = {query_data['F_raw']}")
    print(f"sigma = {query_data['sigma_raw']}")
    print(f"G = {query_data['G']['raw']}")


# prints the final rows produced by the (e)mf query
def print_final_results(results):
    print("\nFinal results:")
    if not results:
        print("No rows matched.")
        return
    for row in results:
        print(" ", row)

# generates and saves intermediate Python files used by the project.
# it creats the generated MF structure file and generated simple query file and returns their filenames
def save_step_outputs(query_data):
    mf_fields = build_mf_structure_fields(query_data)
    mf_struct_file = "generated/generated_mf_struct.py"
    save_generated_code(mf_struct_file, generate_python_mf_structure_code(mf_fields))

    simple_query_file = "generated/generated_simple_query.py"
    save_generated_code(simple_query_file, generate_python_simple_query_code(_sample_simple_query()))

    return mf_struct_file, simple_query_file


def _sample_simple_query():
    # hardcoded warmup query from the project handout:
    # select cust, prod, avg(quant), max(quant) from sales where year=2009 group by cust, prod
    return {
        "S": ["cust", "prod", "avg_quant", "max_quant"],
        "V": ["cust", "prod"],
        "F": [
            {"raw": "avg_quant", "agg": "avg", "attr": "quant"},
            {"raw": "max_quant", "agg": "max", "attr": "quant"},
        ],
        "where": [{"attribute": "year", "op": "==", "value": 2009}]
    }


# Section header keywords for file-mode input parsing
_SECTIONS = [
    ("select attribute", "S"),
    ("number of grouping", "n"),
    ("grouping attributes", "V"),
    ("f-vect", "F"),
    ("condition-vect", "sigma"),
    ("select condition", "sigma"),
    ("having", "G"),
]


# Use case 1: Reads query inputs from a txt, and scans for SELECT, ATTR, GROUPING VARS, etc (validates all)
def read_inputs_from_file(filepath):
    with open(filepath) as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

    sections, cur, cur_lines = {}, None, []
    for line in lines:
        lo = line.lower()
        new_sec = next((v for k, v in _SECTIONS if k in lo), None)
        if new_sec:
            if cur: sections[cur] = cur_lines
            cur, cur_lines = new_sec, []
        else:
            cur_lines.append(line)
    if cur:
        sections[cur] = cur_lines

    for key in ("S", "n", "V", "F", "sigma", "G"):
        if key not in sections or not sections[key]:
            error(f"Input file is missing required section: {key}")

    return (sections["S"][0], sections["n"][0], sections["V"][0], sections["F"][0],
            ";".join(sections["sigma"]), sections["G"][0])


# Use case 2: Prompts user to enter each query component in the terminal
def read_inputs_interactively():
    print("Enter query inputs (press Enter after each):")
    S_input = input("SELECT ATTRIBUTE(S): ").strip()
    n_input = input("NUMBER OF GROUPING VARIABLES(n): ").strip()
    V_input = input("GROUPING ATTRIBUTES(V): ").strip()
    F_input = input("F-VECT([F]): ").strip()
    print("SELECT CONDITION-VECT([sigma]) - one condition per line, blank line when done:")
    sigma_lines = []
    while True:
        line = input("sigma: ").strip()
        if not line:
            break
        sigma_lines.append(line)
    G_input = input("HAVING_CONDITION(G): ").strip()
    return S_input, n_input, V_input, F_input, ";".join(sigma_lines), G_input

# MAIN EXECUTION PIPELINE
def parse_and_run(S_input, n_input, V_input, F_input, sigma_input, G_input):
    # validates N
    try:
        n = int(n_input)
    except ValueError:
        error("n must be an integer.")
    if n <= 0:
        error("n must be greater than 0.")

    # splits and validates all user inputs
    S = split_input(S_input, "S")
    V = split_input(V_input, "V")
    F = split_input(F_input, "F")
    sigma = split_input(sigma_input, "sigma", ";")

    # checks that sigma count matches number of grouping vars (n)
    if len(sigma) != n:
        error("The number of sigma conditions must match n.")

    G = G_input.strip()
    if not G:
        error("G cannot be empty.")

    # builds parsed query structure
    query_data = build_query_data(S, n, V, F, sigma, G)

    # prints out parsed query summ
    print_query_summary(query_data)

    # builds mf query object
    mf_struct_file, simple_query_file = save_step_outputs(query_data)

    # scans rows from the sales table
    mf_query = build_mf_query(query_data)
    rows = list(scan_sales_rows())
    # executes the query
    _, _, _, results = execute_mf_query(rows, mf_query)
    print_final_results(results)

    # saves theh generated query PY program
    mf_output_filename = "generated/generated_mf_query.py"
    save_generated_code(mf_output_filename, generate_python_mf_query_code(mf_query))

    print("\nGenerated files:")
    print(f"{mf_struct_file}")
    print(f"{simple_query_file}")
    print(f"{mf_output_filename}")
    print("Run generated MF query with: python3 generated/generated_mf_query.py")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--file":
        inputs = read_inputs_from_file(sys.argv[2])
    elif len(sys.argv) == 1:
        inputs = read_inputs_interactively()
    elif len(sys.argv) == 7:
        inputs = tuple(sys.argv[1:7])
    else:
        error(
            "Usage:\n"
            "File mode: python3 main.py --file query.txt\n"
            "Interactive mode: python3 main.py\n"
            "CLI mode: python3 main.py S n V F sigma G"
        )

    parse_and_run(*inputs)


if __name__ == "__main__":
    main()
