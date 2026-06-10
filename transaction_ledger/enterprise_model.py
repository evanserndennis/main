import asyncio
import httpx
import logging
import time
from db_manager import get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler('ledger_audit.log'),
        logging.StreamHandler()
    ]
)

VERIFICATION_ENDPOINTS = {
    "Visa Gateway": "https://httpbin.org/status/200",
    "Stripe Fraud Engine": "https://httpbin.org/status/500",
    "Internal Ledger Audit": "https://httpbin.org/status/200"
}

def get_ledger_flagged(conn):
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute('SELECT transaction_id FROM transactions WHERE status = "FLAGGED" ORDER BY amount DESC')
            return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

async def verify_ledger_flagged(transaction: str, network: str, endpoint: str) -> dict:
    logging.info(f'Pinging audit network channel: {network}')
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        if response.status_code != 200:
            raise ValueError(f'Audit network channel returned critical status code: {response.status_code}')
        return {'transaction_id': transaction, 'network': network, 'status_code': response.status_code}

async def main():
    start_time = time.perf_counter()
    logging.info('Initializing ledger network sweep')
    db_connection = get_db_connection()
    flagged_records = get_ledger_flagged(db_connection)
    tasks = [
        verify_ledger_flagged(record[0], network, endpoint)
        for record in flagged_records
        for network, endpoint in VERIFICATION_ENDPOINTS.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failures = [item for item in results if isinstance(item, Exception)]
    for err in failures:
        logging.error(f'External clearance gateway failed: {err}')
    successes = [item for item in results if not isinstance(item, Exception)]
    print(f'\n{"=" * 20} NETWORK VERIFICATION LOG {"=" * 20}\n')
    print(f'Gross evaluated: {len(results)}')
    print(f'Passed network validation: {len(successes)}')
    print(f'Failed network validation: {len(failures)}')
    print(f'\n{"=" * 66}')
    elapsed = time.perf_counter() - start_time
    logging.info(f"Sweep complete in {elapsed:.2f}s. Metrics -> Operational: {len(successes)} | Offline: {len(failures)}\n")

if __name__ == '__main__':
    asyncio.run(main())