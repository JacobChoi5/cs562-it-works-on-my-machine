from validator import (
    split_input,
    validate_columns,
    validate_no_duplicates,
    validate_s_list,
    validate_f_list,
    validate_sigma_list,
    validate_g_condition,
)
from parser import (
    build_query_data,
    error,
)
from mf_structure import (
    build_mf_structure_fields,
)
from generator import (
    generate_python_mf_structure_code,
    generate_python_simple_query_code,
    generate_python_mf_query_code,
    save_generated_code,
)
from mf_query import (
    build_mf_query,
    execute_mf_query,
)
from sql import scan_sales_rows


def print_query_summary(query_data):
    print("\nQuery accepted.")
    print(f"n = {query_data['n']}")
    print(f"V = {query_data['V']}")
    print(f"S = {query_data['S_raw']}")
    print(f"F = {query_data['F_raw']}")
    print(f"sigma = {query_data['sigma_raw']}")
    print(f"G = {query_data['G']['raw']}")


def print_final_results(results):
    print("\nFinal results:")

    if len(results) == 0:
        print("  No rows matched.")
        return

    for row in results:
        print(" ", row)


def save_step_outputs(query_data):
    mf_fields = build_mf_structure_fields(query_data)
    generated_code = generate_python_mf_structure_code(mf_fields)

    output_filename = "generated/generated_mf_struct.py"
    save_generated_code(output_filename, generated_code)

    simple_query = build_sample_simple_query()
    simple_program_code = generate_python_simple_query_code(simple_query)

    simple_output_filename = "generated/generated_simple_query.py"
    save_generated_code(simple_output_filename, simple_program_code)

    return output_filename, simple_output_filename


def run_requested_mf_query(query_data):
    mf_query = build_mf_query(query_data)
    rows = list(scan_sales_rows())
    _, _, _, results = execute_mf_query(rows, mf_query)
    return mf_query, results


def build_sample_simple_query():
    # hardcoded warmup query from the project handout:
    # select cust, prod, avg(quant), max(quant) from sales where year=2009 group by cust, prod
    return {
        "S": ["cust", "prod", "avg_quant", "max_quant"],
        "V": ["cust", "prod"],
        "F": [
            {"raw": "avg_quant", "agg": "avg", "attr": "quant"},
            {"raw": "max_quant", "agg": "max", "attr": "quant"},
        ],
        "where": [
            {"attribute": "year", "op": "==", "value": 2009}
        ]
    }


def read_inputs_from_file(filepath):
    # parse the spec-format input file into the 6 raw query strings.
    # expected format (label lines are detected by keywords, sigma has one condition per line):
    #
    #   SELECT ATTRIBUTE(S):
    #   cust, 1_sum_quant, 2_sum_quant
    #   NUMBER OF GROUPING VARIABLES(n):
    #   2
    #   GROUPING ATTRIBUTES(V):
    #   cust
    #   F-VECT([F]):
    #   1_sum_quant, 2_sum_quant
    #   SELECT CONDITION-VECT([sigma]):
    #   1.state='NY'
    #   2.state='NJ'
    #   HAVING_CONDITION(G):
    #   none

    with open(filepath, "r") as f:
        lines = [line.strip() for line in f.readlines()]

    # drop blank lines and comment lines so we only walk meaningful content
    lines = [l for l in lines if l and not l.startswith("#")]

    sections = {}
    current_label = None
    current_lines = []

    for line in lines:
        lower = line.lower()

        if "select attribute" in lower:
            if current_label:
                sections[current_label] = current_lines
            current_label = "S"
            current_lines = []
        elif "number of grouping" in lower:
            if current_label:
                sections[current_label] = current_lines
            current_label = "n"
            current_lines = []
        elif "grouping attributes" in lower:
            if current_label:
                sections[current_label] = current_lines
            current_label = "V"
            current_lines = []
        elif "f-vect" in lower:
            if current_label:
                sections[current_label] = current_lines
            current_label = "F"
            current_lines = []
        elif "condition-vect" in lower or "select condition" in lower:
            if current_label:
                sections[current_label] = current_lines
            current_label = "sigma"
            current_lines = []
        elif "having" in lower:
            if current_label:
                sections[current_label] = current_lines
            current_label = "G"
            current_lines = []
        else:
            current_lines.append(line)

    # flush the last section
    if current_label:
        sections[current_label] = current_lines

    for key in ["S", "n", "V", "F", "sigma", "G"]:
        if key not in sections or len(sections[key]) == 0:
            error(f"Input file is missing required section: {key}")

    S_input     = sections["S"][0]
    n_input     = sections["n"][0]
    V_input     = sections["V"][0]
    F_input     = sections["F"][0]
    sigma_input = ";".join(sections["sigma"])  # one condition per line -> semicolon-separated
    G_input     = sections["G"][0]

    return S_input, n_input, V_input, F_input, sigma_input, G_input


def read_inputs_interactively():
    # prompt the user for each of the 6 Phi operands one at a time
    print("Enter query inputs (press Enter after each):")
    S_input = input("SELECT ATTRIBUTE(S): ").strip()
    n_input = input("NUMBER OF GROUPING VARIABLES(n): ").strip()
    V_input = input("GROUPING ATTRIBUTES(V): ").strip()
    F_input = input("F-VECT([F]): ").strip()
    print("SELECT CONDITION-VECT([sigma]) - enter one condition per line, blank line when done:")
    sigma_lines = []
    while True:
        line = input("  sigma: ").strip()
        if line == "":
            break
        sigma_lines.append(line)
    sigma_input = ";".join(sigma_lines)
    G_input = input("HAVING_CONDITION(G): ").strip()
    return S_input, n_input, V_input, F_input, sigma_input, G_input


def parse_and_run(S_input, n_input, V_input, F_input, sigma_input, G_input):
    # shared validation + execution path regardless of where the inputs came from
    try:
        n = int(n_input)
    except ValueError:
        error("n must be an integer.")

    if n <= 0:
        error("n must be greater than 0.")

    S     = split_input(S_input, "S")
    V     = split_input(V_input, "V")
    F     = split_input(F_input, "F")
    sigma = split_input(sigma_input, "sigma", ";")

    if len(sigma) != n:
        error("The number of sigma conditions must match n.")

    G = G_input.strip()
    if G == "":
        error("G cannot be empty.")

    validate_columns(V, "V")
    validate_no_duplicates(V, "V")
    validate_s_list(S, n)
    validate_f_list(F, n)
    validate_sigma_list(sigma, n)
    validate_g_condition(G, n)

    query_data = build_query_data(S, n, V, F, sigma, G)

    print_query_summary(query_data)

    mf_struct_file, simple_query_file = save_step_outputs(query_data)

    mf_query, results = run_requested_mf_query(query_data)
    print_final_results(results)

    mf_program_code = generate_python_mf_query_code(mf_query)
    mf_output_filename = "generated/generated_mf_query.py"
    save_generated_code(mf_output_filename, mf_program_code)

    print("\nGenerated files:")
    print(f"  {mf_struct_file}")
    print(f"  {simple_query_file}")
    print(f"  {mf_output_filename}")
    print("Run generated MF query with: python3 generated/generated_mf_query.py")


def main():
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--file":
        # file mode: python3 main.py --file query.txt
        inputs = read_inputs_from_file(sys.argv[2])

    elif len(sys.argv) == 1:
        # interactive mode: python3 main.py
        inputs = read_inputs_interactively()

    elif len(sys.argv) == 7:
        # original CLI mode: python3 main.py S n V F sigma G
        inputs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]

    else:
        error(
            "Usage:\n"
            "  File mode:        python3 main.py --file query.txt\n"
            "  Interactive mode: python3 main.py\n"
            "  CLI mode:         python3 main.py S n V F sigma G"
        )

    parse_and_run(*inputs)


if __name__ == "__main__":
    main()