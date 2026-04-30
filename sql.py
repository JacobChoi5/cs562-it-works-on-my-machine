import os
import psycopg2
import psycopg2.extras
import tabulate
from dotenv import load_dotenv
from parser import error


def query():
    """
    Used for testing standard queries in SQL.
    """
    load_dotenv()

    user = os.getenv('USER')
    password = os.getenv('PASSWORD')
    dbname = os.getenv('DBNAME')

    conn = psycopg2.connect("dbname="+dbname+" user="+user+" password="+password,
                            cursor_factory=psycopg2.extras.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sales WHERE quant > 10")

    return tabulate.tabulate(cur.fetchall(),
                             headers="keys", tablefmt="psql")

def get_db_connection():
    # keep connection setup simple and driven by env vars
    # way cleaner than hardcoding creds into the project
    load_dotenv()
    
    if psycopg2 is None:
        error(
            "psycopg2 is not installed. Run: pip install psycopg2-binary"
        )

    try:
        connection = psycopg2.connect(
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
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT cust, prod, day, month, year, state, quant, date
                FROM sales
                """
            )

            for row in cursor:
                yield dict(row)
    finally:
        connection.close()

def main():
    print(query())


if "__main__" == __name__:
    main()