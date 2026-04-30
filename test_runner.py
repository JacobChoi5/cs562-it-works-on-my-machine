"""
CS562 MF Query Engine - Test Runner
====================================
Tests all three input modes (CLI args, --file, interactive) across a wide
range of valid queries and invalid inputs that should be caught by the
validator. Run from the project root:

    python3 test_runner.py

Each test prints PASS / FAIL and a short description of what it checks.
"""

import subprocess
import sys
import os
import tempfile

PYTHON = sys.executable
MAIN   = os.path.join(os.path.dirname(__file__), "main.py")

PASS_COUNT = 0
FAIL_COUNT = 0


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def run_cli(S, n, V, F, sigma, G):
    """Run main.py using positional CLI args."""
    return subprocess.run(
        [PYTHON, MAIN, S, n, V, F, sigma, G],
        capture_output=True, text=True
    )


def run_file(file_contents):
    """Write a temp query file and run main.py --file <path>."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(file_contents)
        tmppath = f.name
    result = subprocess.run(
        [PYTHON, MAIN, "--file", tmppath],
        capture_output=True, text=True
    )
    os.unlink(tmppath)
    return result


def run_interactive(S, n, V, F, sigma_lines, G):
    """Run main.py in interactive mode by piping stdin."""
    sigma_input = "\n".join(sigma_lines) + "\n\n"  # blank line ends sigma entry
    stdin_text = f"{S}\n{n}\n{V}\n{F}\n{sigma_input}{G}\n"
    return subprocess.run(
        [PYTHON, MAIN],
        input=stdin_text,
        capture_output=True, text=True
    )


def make_query_file(S, n, V, F, sigma_lines, G):
    """Build a spec-format query file string."""
    sigma_block = "\n".join(sigma_lines)
    return (
        f"SELECT ATTRIBUTE(S):\n{S}\n"
        f"NUMBER OF GROUPING VARIABLES(n):\n{n}\n"
        f"GROUPING ATTRIBUTES(V):\n{V}\n"
        f"F-VECT([F]):\n{F}\n"
        f"SELECT CONDITION-VECT([sigma]):\n{sigma_block}\n"
        f"HAVING_CONDITION(G):\n{G}\n"
    )


def check(label, result, expect_success, expect_in_output=None):
    """Evaluate a test result and print PASS/FAIL."""
    global PASS_COUNT, FAIL_COUNT

    full_output = result.stdout + result.stderr
    succeeded   = "Query accepted." in result.stdout

    ok = (succeeded == expect_success)

    if ok and expect_in_output:
        ok = expect_in_output.lower() in full_output.lower()

    status = "PASS" if ok else "FAIL"
    tag    = "valid  " if expect_success else "invalid"

    if ok:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
        # show output on failures so it's easy to debug
        print(f"  [{status}] [{tag}] {label}")
        print(f"         stdout: {result.stdout[:300].strip()}")
        print(f"         stderr: {result.stderr[:300].strip()}")
        return

    print(f"  [{status}] [{tag}] {label}")


# ============================================================
# SECTION 1 — CLI MODE (positional args)
# ============================================================

print("\n" + "="*60)
print("SECTION 1: CLI MODE")
print("="*60)

# --- Valid queries ---

check(
    "CLI | n=1 | sum | no G",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | count | no G",
    run_cli(
        "cust,1_count_quant", "1", "cust",
        "1_count_quant", "1.state='NJ'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | avg | no G",
    run_cli(
        "cust,1_avg_quant", "1", "cust",
        "1_avg_quant", "1.state='CT'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | min | no G",
    run_cli(
        "cust,1_min_quant", "1", "cust",
        "1_min_quant", "1.state='NY'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | max | no G",
    run_cli(
        "cust,1_max_quant", "1", "cust",
        "1_max_quant", "1.state='NJ'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=2 | sum+sum | no G",
    run_cli(
        "cust,1_sum_quant,2_sum_quant", "2", "cust",
        "1_sum_quant,2_sum_quant",
        "1.state='NY';2.state='NJ'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=3 | sum+sum+sum | no G (spec example)",
    run_cli(
        "cust,1_sum_quant,2_sum_quant,3_sum_quant", "3", "cust",
        "1_sum_quant,2_sum_quant,3_sum_quant",
        "1.state='NY';2.state='NJ';3.state='CT'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=2 | multiple aggs per group | no G",
    run_cli(
        "cust,1_sum_quant,1_avg_quant,2_max_quant", "2", "cust",
        "1_sum_quant,1_avg_quant,2_max_quant",
        "1.state='NY';2.state='NJ'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=2 | group by cust+prod",
    run_cli(
        "cust,prod,1_sum_quant,2_sum_quant", "2", "cust,prod",
        "1_sum_quant,2_sum_quant",
        "1.state='NY';2.state='NJ'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | G filter on sum",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "1.state='NY'", "1_sum_quant>500"
    ),
    expect_success=True
)

check(
    "CLI | n=2 | G compares two aggregates",
    run_cli(
        "cust,1_sum_quant,2_sum_quant", "2", "cust",
        "1_sum_quant,2_sum_quant",
        "1.state='NY';2.state='NJ'", "1_sum_quant>2_sum_quant"
    ),
    expect_success=True
)

check(
    "CLI | n=2 | dependent sigma (group 2 references group 1 avg)",
    run_cli(
        "cust,1_avg_quant,2_sum_quant", "2", "cust",
        "1_avg_quant,2_sum_quant",
        "1.state='NY';2.state='NJ' and 2.quant>1_avg_quant", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | sigma uses != operator",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "1.state!='NY'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | sigma uses >= on numeric column",
    run_cli(
        "cust,1_count_quant", "1", "cust",
        "1_count_quant", "1.year>=2009", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | sigma compound with and",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "1.state='NY' and 1.year=2009", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=3 | all 5 agg types across groups",
    run_cli(
        "cust,1_sum_quant,2_avg_quant,3_min_quant,3_max_quant,3_count_quant", "3", "cust",
        "1_sum_quant,2_avg_quant,3_min_quant,3_max_quant,3_count_quant",
        "1.state='NY';2.state='NJ';3.state='CT'", "none"
    ),
    expect_success=True
)

check(
    "CLI | n=1 | G uses <= operator",
    run_cli(
        "cust,1_avg_quant", "1", "cust",
        "1_avg_quant", "1.state='NY'", "1_avg_quant<=400"
    ),
    expect_success=True
)

# --- Invalid queries ---

check(
    "CLI | wrong number of args (5 instead of 6)",
    subprocess.run(
        [PYTHON, MAIN, "cust", "1", "cust", "1_sum_quant", "1.state='NY'"],
        capture_output=True, text=True
    ),
    expect_success=False
)

check(
    "CLI | n=0 (must be > 0)",
    run_cli(
        "cust,1_sum_quant", "0", "cust",
        "1_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | n is not an integer",
    run_cli(
        "cust,1_sum_quant", "abc", "cust",
        "1_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | V contains invalid column name",
    run_cli(
        "cust,1_sum_quant", "1", "notacolumn",
        "1_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | F references group 2 but n=1",
    run_cli(
        "cust,2_sum_quant", "1", "cust",
        "2_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | F uses invalid aggregate name",
    run_cli(
        "cust,1_median_quant", "1", "cust",
        "1_median_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | F uses invalid attribute name",
    run_cli(
        "cust,1_sum_price", "1", "cust",
        "1_sum_price", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | sigma count doesn't match n (2 sigmas, n=3)",
    run_cli(
        "cust,1_sum_quant,2_sum_quant,3_sum_quant", "3", "cust",
        "1_sum_quant,2_sum_quant,3_sum_quant",
        "1.state='NY';2.state='NJ'", "none"
    ),
    expect_success=False
)

check(
    "CLI | sigma references group number out of range",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "5.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | sigma references invalid column",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "1.badcol='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | dependent sigma references forward group (group 2 refs group 3)",
    run_cli(
        "cust,1_sum_quant,2_sum_quant,3_sum_quant", "3", "cust",
        "1_sum_quant,2_sum_quant,3_sum_quant",
        "1.state='NY';2.quant>3_sum_quant;3.state='CT'", "none"
    ),
    expect_success=False
)

check(
    "CLI | G references aggregate from group out of range",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "1.state='NY'", "9_sum_quant>100"
    ),
    expect_success=False
)

check(
    "CLI | duplicate F entries",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant,1_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | duplicate V entries",
    run_cli(
        "cust,1_sum_quant", "1", "cust,cust",
        "1_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)

check(
    "CLI | G empty string",
    run_cli(
        "cust,1_sum_quant", "1", "cust",
        "1_sum_quant", "1.state='NY'", ""
    ),
    expect_success=False
)

check(
    "CLI | S references aggregate not in F",
    run_cli(
        "cust,1_sum_quant,1_avg_quant", "1", "cust",
        "1_sum_quant", "1.state='NY'", "none"
    ),
    expect_success=False
)


# ============================================================
# SECTION 2 — FILE MODE (--file query.txt)
# ============================================================

print("\n" + "="*60)
print("SECTION 2: FILE MODE (--file)")
print("="*60)

check(
    "FILE | n=1 | basic sum query",
    run_file(make_query_file(
        "cust, 1_sum_quant", "1", "cust",
        "1_sum_quant", ["1.state='NY'"], "none"
    )),
    expect_success=True
)

check(
    "FILE | n=3 | spec example query",
    run_file(make_query_file(
        "cust, 1_sum_quant, 2_sum_quant, 3_sum_quant", "3", "cust",
        "1_sum_quant, 2_sum_quant, 3_sum_quant",
        ["1.state='NY'", "2.state='NJ'", "3.state='CT'"],
        "none"
    )),
    expect_success=True
)

check(
    "FILE | n=2 | G filter on avg",
    run_file(make_query_file(
        "cust, 1_avg_quant, 2_avg_quant", "2", "cust",
        "1_avg_quant, 2_avg_quant",
        ["1.state='NY'", "2.state='NJ'"],
        "1_avg_quant>200"
    )),
    expect_success=True
)

check(
    "FILE | n=2 | group by cust and prod",
    run_file(make_query_file(
        "cust, prod, 1_sum_quant, 2_sum_quant", "2", "cust, prod",
        "1_sum_quant, 2_sum_quant",
        ["1.state='NY'", "2.state='CT'"],
        "none"
    )),
    expect_success=True
)

check(
    "FILE | n=1 | compound sigma with and",
    run_file(make_query_file(
        "cust, 1_sum_quant", "1", "cust",
        "1_sum_quant",
        ["1.state='NY' and 1.year=2009"],
        "none"
    )),
    expect_success=True
)

check(
    "FILE | n=2 | dependent sigma",
    run_file(make_query_file(
        "cust, 1_sum_quant, 2_count_quant", "2", "cust",
        "1_sum_quant, 2_count_quant",
        ["1.state='NY'", "2.state='NJ' and 2.quant>1_sum_quant"],
        "none"
    )),
    expect_success=True
)

check(
    "FILE | n=3 | all 5 agg functions",
    run_file(make_query_file(
        "cust, 1_sum_quant, 2_avg_quant, 3_min_quant, 3_max_quant, 3_count_quant",
        "3", "cust",
        "1_sum_quant, 2_avg_quant, 3_min_quant, 3_max_quant, 3_count_quant",
        ["1.state='NY'", "2.state='NJ'", "3.state='CT'"],
        "none"
    )),
    expect_success=True
)

check(
    "FILE | has comments and blank lines (should be ignored)",
    run_file(
        "# this is a test query\n\n"
        + make_query_file(
            "cust, 1_sum_quant", "1", "cust",
            "1_sum_quant", ["1.state='NY'"], "none"
        )
        + "\n# end of file\n"
    ),
    expect_success=True
)

# invalid file inputs
check(
    "FILE | missing G section entirely",
    run_file(
        "SELECT ATTRIBUTE(S):\ncust, 1_sum_quant\n"
        "NUMBER OF GROUPING VARIABLES(n):\n1\n"
        "GROUPING ATTRIBUTES(V):\ncust\n"
        "F-VECT([F]):\n1_sum_quant\n"
        "SELECT CONDITION-VECT([sigma]):\n1.state='NY'\n"
        # G section deliberately omitted
    ),
    expect_success=False
)

check(
    "FILE | n=2 but only one sigma line",
    run_file(make_query_file(
        "cust, 1_sum_quant, 2_sum_quant", "2", "cust",
        "1_sum_quant, 2_sum_quant",
        ["1.state='NY'"],   # missing second sigma
        "none"
    )),
    expect_success=False
)

check(
    "FILE | invalid aggregate in F",
    run_file(make_query_file(
        "cust, 1_mode_quant", "1", "cust",
        "1_mode_quant", ["1.state='NY'"], "none"
    )),
    expect_success=False
)

check(
    "FILE | V has invalid column",
    run_file(make_query_file(
        "revenue, 1_sum_quant", "1", "revenue",
        "1_sum_quant", ["1.state='NY'"], "none"
    )),
    expect_success=False
)


# ============================================================
# SECTION 3 — INTERACTIVE MODE (piped stdin)
# ============================================================

print("\n" + "="*60)
print("SECTION 3: INTERACTIVE MODE (stdin)")
print("="*60)

check(
    "INTERACTIVE | n=1 | basic sum",
    run_interactive(
        "cust, 1_sum_quant", "1", "cust", "1_sum_quant",
        ["1.state='NY'"], "none"
    ),
    expect_success=True
)

check(
    "INTERACTIVE | n=3 | spec example",
    run_interactive(
        "cust, 1_sum_quant, 2_sum_quant, 3_sum_quant", "3", "cust",
        "1_sum_quant, 2_sum_quant, 3_sum_quant",
        ["1.state='NY'", "2.state='NJ'", "3.state='CT'"],
        "none"
    ),
    expect_success=True
)

check(
    "INTERACTIVE | n=2 | G filter",
    run_interactive(
        "cust, 1_sum_quant, 2_sum_quant", "2", "cust",
        "1_sum_quant, 2_sum_quant",
        ["1.state='NY'", "2.state='NJ'"],
        "1_sum_quant>300"
    ),
    expect_success=True
)

check(
    "INTERACTIVE | n=2 | group by cust+prod",
    run_interactive(
        "cust, prod, 1_max_quant, 2_min_quant", "2", "cust, prod",
        "1_max_quant, 2_min_quant",
        ["1.state='NY'", "2.state='CT'"],
        "none"
    ),
    expect_success=True
)

check(
    "INTERACTIVE | n=1 | compound sigma",
    run_interactive(
        "cust, 1_count_quant", "1", "cust", "1_count_quant",
        ["1.state='NY' and 1.year=2009"],
        "none"
    ),
    expect_success=True
)

check(
    "INTERACTIVE | invalid: n=0",
    run_interactive(
        "cust, 1_sum_quant", "0", "cust", "1_sum_quant",
        ["1.state='NY'"], "none"
    ),
    expect_success=False
)

check(
    "INTERACTIVE | invalid: bad aggregate",
    run_interactive(
        "cust, 1_variance_quant", "1", "cust", "1_variance_quant",
        ["1.state='NY'"], "none"
    ),
    expect_success=False
)

check(
    "INTERACTIVE | invalid: sigma count mismatch",
    run_interactive(
        "cust, 1_sum_quant, 2_sum_quant", "2", "cust",
        "1_sum_quant, 2_sum_quant",
        ["1.state='NY'"],  # only 1 sigma for n=2
        "none"
    ),
    expect_success=False
)


# ============================================================
# SUMMARY
# ============================================================

total = PASS_COUNT + FAIL_COUNT
print("\n" + "="*60)
print(f"RESULTS: {PASS_COUNT}/{total} passed  |  {FAIL_COUNT} failed")
print("="*60)

if FAIL_COUNT > 0:
    sys.exit(1)
