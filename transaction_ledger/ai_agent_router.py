import sqlite3
from db_manager import get_db_connection
from dotenv import load_dotenv

def fetch_flagged_transactions():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT transaction_id, amount, category
                FROM transactions
                WHERE status = "FLAGGED"
                LIMIT 20
            ''')
            return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

flagged_transactions = fetch_flagged_transactions()

print(flagged_transactions)