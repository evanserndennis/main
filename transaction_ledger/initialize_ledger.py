import sqlite3
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from db_manager import get_db_connection

def initialize_database(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            amount REAL,
            category TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')

def stream_transaction_data(record_count):
    categories = ['electronics', 'apparel', 'home', 'travel', 'software']
    transaction_time = datetime.now()
    for i in range(0, record_count):
        transaction_id = f'tx_{uuid.uuid4().hex[:8]}'
        transaction_time += timedelta(minutes=(random.randint(0,10)))
        transaction_user = f'u_{uuid.uuid4().hex[:6]}'
        transaction_amount = round(random.uniform(5.00, 1500.00),2)
        transaction_category = random.choice(categories)
        transaction_status = 'FLAGGED' if transaction_amount > 1000.00 else 'APPROVED' if random.uniform(0, 100) < 95 else 'REJECTED'
        yield (
            transaction_id,
            transaction_time.isoformat(),
            transaction_user,
            transaction_amount,
            transaction_category,
            transaction_status
        )

def inject_transaction_data(record_count=500):
    #  Injecting test data into the database
    conn = get_db_connection()
    with conn:
        initialize_database(conn)
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO transactions (transaction_id, timestamp, user_id, amount, category, status)
            VALUES(?, ?, ?, ?, ?, ?)
        ''', stream_transaction_data(record_count))

        #  Pulling data aggregate data from the injection
        injection_summary = cursor.execute('''
            SELECT 
                status,
                COUNT(*) as total_count,
                ROUND(SUM(amount), 2) as total_volume,
                ROUND(AVG(amount), 2) as average_amount
            FROM transactions
            GROUP BY status
            ORDER BY total_volume DESC;   
        ''').fetchall()

    conn.close()

    #  Generating an injection summary to print in the terminal
    injection_aggregation = ''
    for status_summary in injection_summary:
        injection_aggregation += f'{status_summary[0]} transactions:\n\t└─ Count: {status_summary[1]}\n\t└─ Total amount: {status_summary[2]}\n\t└─ Average amount: {status_summary[3]}\n'
    print(injection_aggregation)

if __name__ == '__main__':
    inject_transaction_data()
