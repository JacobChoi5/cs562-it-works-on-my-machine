import re
from parser import (
    parse_aggregate_token,
    try_parse_aggregate_token,
    split_sigma_condition_parts,
    split_on_and,
    split_g_condition_parts,
)

def error(message):
    print("Error:", message)
    sys.exit(1)

# fixed project schema from the sales table in the handout
VALID_COLUMNS = ["cust", "prod", "day", "month", "year", "state", "quant", "date"]

# aggregate functions we support for now
VALID_AGGS = ["sum", "count", "avg", "min", "max"]


def split_input(text, name, separator=","):
    text = text.strip()

    if text == "":
        error(f"{name} cannot be empty.")

    parts = text.split(separator)
    cleaned_parts = []

    for part in parts:
        part = part.strip()
        if part == "":
            error(f"{name} has an empty value.")
        cleaned_parts.append(part)

    return cleaned_parts


def validate_columns(items, name):
    for item in items:
        if item not in VALID_COLUMNS:
            error(f"{name} contains invalid attribute '{item}'.")


def validate_no_duplicates(items, name):
    seen = set()

    for item in items:
        if item in seen:
            error(f"{name} contains duplicate value '{item}'.")
        seen.add(item)


def validate_projected_item(item, field_name, n):
    if item in VALID_COLUMNS:
        return

    group_num, agg_name, attr_name = parse_aggregate_token(item, field_name)

    if group_num < 1 or group_num > n:
        error(
            f"{field_name} item '{item}' uses grouping variable {group_num}, but n = {n}."
        )

    if agg_name not in VALID_AGGS:
        error(
            f"{field_name} item '{item}' uses invalid aggregate '{agg_name}'."
        )

    if attr_name not in VALID_COLUMNS:
        error(
            f"{field_name} item '{item}' uses invalid attribute '{attr_name}'."
        )


def validate_s_list(S, n):
    seen = set()

    for item in S:
        validate_projected_item(item, "S", n)

        if item in seen:
            error(f"S contains duplicate value '{item}'.")
        seen.add(item)


def validate_f_list(F, n):
    seen = set()

    for item in F:
        group_num, agg_name, attr_name = parse_aggregate_token(item, "F")

        if group_num < 1 or group_num > n:
            error(
                f"F item '{item}' uses grouping variable {group_num}, but n = {n}."
            )

        if agg_name not in VALID_AGGS:
            error(
                f"F item '{item}' uses invalid aggregate '{agg_name}'."
            )

        if attr_name not in VALID_COLUMNS:
            error(
                f"F item '{item}' uses invalid attribute '{attr_name}'."
            )

        if item in seen:
            error(f"F contains duplicate value '{item}'.")
        seen.add(item)


def validate_sigma_single_predicate(condition, n, current_group_num):
    group_num, left_attr, op, right_raw = split_sigma_condition_parts(condition)

    if group_num < 1 or group_num > n:
        error(
            f"sigma condition '{condition}' uses grouping variable {group_num}, but n = {n}."
        )

    if left_attr not in VALID_COLUMNS:
        error(
            f"sigma condition '{condition}' uses invalid attribute '{left_attr}'."
        )

    if op not in ["==", "!=", ">", "<", ">=", "<="]:
        error(
            f"sigma condition '{condition}' uses unsupported operator '{op}'."
        )

    if right_raw in VALID_COLUMNS:
        return

    if re.fullmatch(r"'[^']*'", right_raw):
        return

    if re.fullmatch(r'"[^"]*"', right_raw):
        return

    if re.fullmatch(r"-?\d+(\.\d+)?", right_raw):
        return

    aggregate_parts = try_parse_aggregate_token(right_raw)

    if aggregate_parts is None:
        error(
            f"sigma condition '{condition}' has invalid right side '{right_raw}'. "
            f"Use a quoted literal, number, grouping attribute, or earlier aggregate field."
        )

    ref_group, ref_agg, ref_attr = aggregate_parts

    if ref_group >= current_group_num:
        error(
            f"sigma condition '{condition}' references aggregate '{right_raw}' "
            f"from grouping variable {ref_group}. Only earlier grouping variables are allowed."
        )

    if ref_group < 1 or ref_group > n:
        error(
            f"sigma condition '{condition}' references grouping variable {ref_group}, but n = {n}."
        )

    if ref_agg not in VALID_AGGS:
        error(
            f"sigma condition '{condition}' uses invalid aggregate '{ref_agg}'."
        )

    if ref_attr not in VALID_COLUMNS:
        error(
            f"sigma condition '{condition}' uses invalid attribute '{ref_attr}'."
        )


def validate_sigma_list(sigma, n):
    seen_groups = set()

    for condition_text in sigma:
        predicate_texts = split_on_and(condition_text)

        if len(predicate_texts) == 0:
            error(f"sigma condition '{condition_text}' is invalid.")

        seen_group = None

        for predicate_text in predicate_texts:
            group_num, _, _, _ = split_sigma_condition_parts(predicate_text)

            if seen_group is None:
                seen_group = group_num
            elif group_num != seen_group:
                error(
                    f"sigma condition '{condition_text}' mixes grouping variables. "
                    f"Keep one grouping variable per sigma entry."
                )

        for predicate_text in predicate_texts:
            validate_sigma_single_predicate(predicate_text, n, seen_group)

        if seen_group in seen_groups:
            error(
                f"sigma contains more than one entry for grouping variable {seen_group}."
            )
        seen_groups.add(seen_group)

    if len(seen_groups) != n:
        error("sigma must contain exactly one condition entry for each grouping variable.")


def validate_g_single_predicate(condition, n):
    left_name, op, right_raw = split_g_condition_parts(condition)

    if left_name not in VALID_COLUMNS:
        group_num, agg_name, attr_name = parse_aggregate_token(left_name, "G")

        if group_num < 1 or group_num > n:
            error(
                f"G condition '{condition}' uses grouping variable {group_num}, but n = {n}."
            )

        if agg_name not in VALID_AGGS:
            error(
                f"G condition '{condition}' uses invalid aggregate '{agg_name}'."
            )

        if attr_name not in VALID_COLUMNS:
            error(
                f"G condition '{condition}' uses invalid attribute '{attr_name}'."
            )

    if op not in ["==", "!=", ">", "<", ">=", "<="]:
        error(
            f"G condition '{condition}' uses unsupported operator '{op}'."
        )

    if right_raw in VALID_COLUMNS:
        return

    aggregate_parts = try_parse_aggregate_token(right_raw)

    if aggregate_parts is not None:
        group_num, agg_name, attr_name = aggregate_parts

        if group_num < 1 or group_num > n:
            error(
                f"G condition '{condition}' uses grouping variable {group_num}, but n = {n}."
            )

        if agg_name not in VALID_AGGS:
            error(
                f"G condition '{condition}' uses invalid aggregate '{agg_name}'."
            )

        if attr_name not in VALID_COLUMNS:
            error(
                f"G condition '{condition}' uses invalid attribute '{attr_name}'."
            )
        return

    if re.fullmatch(r"'[^']*'", right_raw):
        return

    if re.fullmatch(r'"[^"]*"', right_raw):
        return

    if re.fullmatch(r"-?\d+(\.\d+)?", right_raw):
        return

    error(
        f"G condition '{condition}' has invalid right side '{right_raw}'."
    )


def validate_g_condition(G, n):
    G = G.strip()

    if G == "":
        error("G cannot be empty.")

    if G.upper() == "NONE":
        return

    predicate_texts = split_on_and(G)

    if len(predicate_texts) == 0:
        error("G is invalid.")

    for predicate_text in predicate_texts:
        validate_g_single_predicate(predicate_text, n)