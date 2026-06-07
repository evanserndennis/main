import sqlite3
import statistics
from db_manager import get_db_connection


def ledger_audit():
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()

            #  Begin ledger audit
            print('\n==================== LEDGER AUDIT =====================\n')

            #  Obtaining all flagged transactions
            cursor.execute('SELECT transaction_id FROM transactions WHERE status = "FLAGGED" ORDER BY amount DESC')
            flagged = cursor.fetchall()
            print(f'There are currently {len(flagged)} flagged transactions in the\nsystem ready for review\n')

            #  Obtaining all transactions outside three sigma
            cursor.execute('SELECT amount FROM transactions')
            amounts = [row[0] for row in cursor.fetchall()]
            amounts_mean = statistics.mean(amounts)
            amounts_sigma = statistics.stdev(amounts)
            upper_bound = amounts_mean + amounts_sigma * 3
            lower_bound = amounts_mean - amounts_sigma * 3
            cursor.execute('''
                SELECT transaction_id
                FROM transactions
                WHERE amount > ? OR amount < ?
                ORDER BY amount DESC
            ''', (upper_bound, lower_bound))
            outliers = cursor.fetchall()
            print(f'There are currently {len(outliers)} transactions in the system, with\namounts outside of normal deviances\n')

            print('==================== END OF REPORT ====================\n')
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    ledger_audit()