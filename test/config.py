# fixed project schema from the sales table
VALID_COLUMNS = ["cust", "prod", "day", "month", "year", "state", "quant", "date"]

# supported aggregate functions for now
VALID_AGGS = ["sum", "count", "avg", "min", "max"]

# type map for sales table
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