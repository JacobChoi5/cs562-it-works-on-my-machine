import sys

def error(message):
    print("Error:", message)
    sys.exit(1)

def parse_aggregate_token(token, field_name):
    parts = token.split("_")

    if len(parts) != 3:
        error(
            f"{field_name} item '{token}' is invalid. "
            f"Use format like 1_sum_quant or sum_1_quant."
        )

    # style 1: 1_sum_quant
    if parts[0].isdigit():
        group_num = int(parts[0])
        agg_name = parts[1]
        attr_name = parts[2]
        return group_num, agg_name, attr_name

    # style 2: sum_1_quant
    if parts[1].isdigit():
        agg_name = parts[0]
        group_num = int(parts[1])
        attr_name = parts[2]
        return group_num, agg_name, attr_name

    error(
        f"{field_name} item '{token}' is invalid. "
        f"Use format like 1_sum_quant or sum_1_quant."
    )


def try_parse_aggregate_token(token):
    parts = token.split("_")

    if len(parts) != 3:
        return None

    if parts[0].isdigit():
        return int(parts[0]), parts[1], parts[2]

    if parts[1].isdigit():
        return int(parts[1]), parts[0], parts[2]

    return None


def build_aggregate_object(token, field_name):
    group_num, agg_name, attr_name = parse_aggregate_token(token, field_name)

    return {
        "raw": token,
        "group": group_num,
        "agg": agg_name,
        "attr": attr_name
    }


def build_projected_item_object(item, valid_columns):
    if item in valid_columns:
        return {
            "raw": item,
            "kind": "attribute",
            "attribute": item
        }

    group_num, agg_name, attr_name = parse_aggregate_token(item, "S")

    return {
        "raw": item,
        "kind": "aggregate",
        "group": group_num,
        "agg": agg_name,
        "attr": attr_name
    }


def parse_literal_value(raw_value):
    text = raw_value.strip()

    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1]

    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]

    lowered = text.lower()
    if lowered == "true":
        return True

    if lowered == "false":
        return False

    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def split_sigma_condition_parts(condition):
    import re

    pattern = re.compile(
        r"^\s*(\d+)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*(==|!=|>=|<=|=|>|<)\s*(.+?)\s*$"
    )

    match = pattern.match(condition)

    if not match:
        error(
            f"sigma condition '{condition}' is invalid. "
            f"Use something like 1.state='NY' or 2.quant>1_avg_quant."
        )

    group_num = int(match.group(1))
    left_attr = match.group(2)
    op = match.group(3)
    right_raw = match.group(4).strip()

    if op == "=":
        op = "=="

    return group_num, left_attr, op, right_raw


def split_on_and(text):
    parts = text.split("and")
    cleaned_parts = []

    for part in parts:
        piece = part.strip()
        if piece == "":
            error(f"Invalid condition chain '{text}'.")
        cleaned_parts.append(piece)

    return cleaned_parts


def build_single_sigma_predicate(condition, valid_columns):
    group_num, left_attr, op, right_raw = split_sigma_condition_parts(condition)

    if right_raw in valid_columns:
        right_type = "group_attr"
        right_value = right_raw
        aggregate_ref = None
    else:
        aggregate_parts = try_parse_aggregate_token(right_raw)

        if aggregate_parts is not None:
            ref_group, ref_agg, ref_attr = aggregate_parts
            right_type = "aggregate_field"
            right_value = right_raw
            aggregate_ref = {
                "group": ref_group,
                "agg": ref_agg,
                "attr": ref_attr
            }
        else:
            right_type = "literal"
            right_value = parse_literal_value(right_raw)
            aggregate_ref = None

    return {
        "raw": condition,
        "group": group_num,
        "left_attr": left_attr,
        "op": op,
        "right_type": right_type,
        "right_value": right_value,
        "aggregate_ref": aggregate_ref
    }


def build_sigma_object(condition_text, valid_columns):
    predicate_texts = split_on_and(condition_text)
    predicates = []

    for predicate_text in predicate_texts:
        predicates.append(build_single_sigma_predicate(predicate_text, valid_columns))

    if len(predicates) == 0:
        error(f"sigma condition '{condition_text}' is invalid.")

    group_num = predicates[0]["group"]

    for predicate in predicates:
        if predicate["group"] != group_num:
            error(
                f"sigma condition '{condition_text}' mixes grouping variables. "
                f"Keep one grouping variable per sigma entry."
            )

    return {
        "raw": condition_text,
        "group": group_num,
        "predicates": predicates
    }


def split_g_condition_parts(condition):
    import re

    pattern = re.compile(
        r"^\s*([a-zA-Z_][a-zA-Z0-9_]*|\d+_[a-zA-Z_][a-zA-Z0-9_]*_[a-zA-Z_][a-zA-Z0-9_]*)\s*(==|!=|>=|<=|=|>|<)\s*(.+?)\s*$"
    )

    match = pattern.match(condition)

    if not match:
        error(
            f"G condition '{condition}' is invalid. "
            f"Use something like 1_sum_quant>10 or cust='Owen'."
        )

    left_name = match.group(1)
    op = match.group(2)
    right_raw = match.group(3).strip()

    if op == "=":
        op = "=="

    return left_name, op, right_raw


def build_single_g_predicate(condition, valid_columns):
    left_name, op, right_raw = split_g_condition_parts(condition)

    if right_raw in valid_columns:
        right_type = "field"
        right_value = right_raw
    else:
        aggregate_parts = try_parse_aggregate_token(right_raw)

        if aggregate_parts is not None:
            right_type = "field"
            right_value = right_raw
        else:
            right_type = "literal"
            right_value = parse_literal_value(right_raw)

    return {
        "raw": condition,
        "left_type": "field",
        "left_value": left_name,
        "op": op,
        "right_type": right_type,
        "right_value": right_value
    }


def build_g_object(G_text, valid_columns):
    G_text = G_text.strip()

    if G_text.upper() == "NONE":
        return {
            "raw": G_text,
            "kind": "none",
            "predicates": []
        }

    predicate_texts = split_on_and(G_text)
    predicates = []

    for predicate_text in predicate_texts:
        predicates.append(build_single_g_predicate(predicate_text, valid_columns))

    return {
        "raw": G_text,
        "kind": "and_chain",
        "predicates": predicates
    }


def validate_s_aggregates_exist_in_f(parsed_S, parsed_F):
    allowed_aggregates = set()

    for agg_item in parsed_F:
        allowed_aggregates.add(agg_item["raw"])

    for item in parsed_S:
        if item["kind"] == "aggregate" and item["raw"] not in allowed_aggregates:
            error(
                f"S aggregate '{item['raw']}' must also appear in F."
            )


def validate_sigma_aggregate_references(parsed_sigma, parsed_F):
    allowed_aggregates = set()

    for agg_item in parsed_F:
        allowed_aggregates.add(agg_item["raw"])

    for sigma_object in parsed_sigma:
        for predicate in sigma_object["predicates"]:
            if predicate["right_type"] == "aggregate_field":
                ref_name = predicate["right_value"]

                if ref_name not in allowed_aggregates:
                    error(
                        f"sigma condition '{predicate['raw']}' references undefined aggregate '{ref_name}'."
                    )


def validate_g_aggregate_references(parsed_G, parsed_F, valid_columns):
    if parsed_G["kind"] == "none":
        return

    allowed_aggregates = set()

    for agg_item in parsed_F:
        allowed_aggregates.add(agg_item["raw"])

    for predicate in parsed_G["predicates"]:
        left_name = predicate["left_value"]

        if left_name not in valid_columns and left_name not in allowed_aggregates:
            error(
                f"G condition '{predicate['raw']}' references undefined aggregate '{left_name}'."
            )

        if predicate["right_type"] == "field":
            right_name = predicate["right_value"]

            if right_name not in valid_columns and right_name not in allowed_aggregates:
                error(
                    f"G condition '{predicate['raw']}' references undefined aggregate '{right_name}'."
                )


def build_query_data(S, n, V, F, sigma, G):
    from config import VALID_COLUMNS

    parsed_S = []
    parsed_F = []
    parsed_sigma = []

    for item in S:
        parsed_S.append(build_projected_item_object(item, VALID_COLUMNS))

    for item in F:
        parsed_F.append(build_aggregate_object(item, "F"))

    for condition in sigma:
        parsed_sigma.append(build_sigma_object(condition, VALID_COLUMNS))

    parsed_G = build_g_object(G, VALID_COLUMNS)

    validate_s_aggregates_exist_in_f(parsed_S, parsed_F)
    validate_sigma_aggregate_references(parsed_sigma, parsed_F)
    validate_g_aggregate_references(parsed_G, parsed_F, VALID_COLUMNS)

    query_data = {
        "S_raw": S,
        "n": n,
        "V": V,
        "F_raw": F,
        "sigma_raw": sigma,
        "G": parsed_G,
        "S": parsed_S,
        "F": parsed_F,
        "sigma": parsed_sigma
    }

    return query_data