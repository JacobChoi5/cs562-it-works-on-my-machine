import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from parser import error


def get_db_connection(): # establishes PostgreSQL database connection
    # keep connection setup simple and driven by env vars
    # way cleaner than hardcoding creds into the project
    load_dotenv()
    try:
        connection = psycopg2.connect( # uses local enviornment to establish connection
            host=os.getenv("PGHOST", "localhost"),
            port=os.getenv("PGPORT", "5432"),
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
        )
        return connection
    except Exception as exc:
        error(f"Could not connect to PostgreSQL: {exc}")


def scan_sales_rows():
    # generator that yields one row at a time from the sales table
    # this keeps us in the cursor/scan mindset the project wants
    connection = get_db_connection()

    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor: # turns result into python dict
            cursor.execute( # full scan query of sales table to dictionary form
                """
                SELECT cust, prod, day, month, year, state, quant, date
                FROM sales
                """
            )

            for row in cursor:
                yield dict(row) # produces over time
    finally:
        connection.close()
