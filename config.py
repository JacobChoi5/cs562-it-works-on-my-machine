# fixed project schema from the sales table in the handout
VALID_COLUMNS = ["cust", "prod", "day", "month", "year", "state", "quant", "date"]

# aggregate functions we support for now
VALID_AGGS = ["sum", "count", "avg", "min", "max"]

# simple type map for the sales table
COLUMN_TYPES = {
    "cust": "str",
    "prod": "str",
    "day": "int",
    "month": "int",
    "year": "int",
    "state": "str",
    "quant": "float",
    "date": "str"
}