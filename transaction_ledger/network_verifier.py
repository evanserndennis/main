import asyncio
import httpx
import time


VERIFICATION_ENDPOINTS = {
    "Visa Gateway": "https://httpbin.org/delay/1",
    "Stripe Fraud Engine": "https://httpbin.org/delay/2",
    "Internal Ledger Audit": "https://httpbin.org/delay/1"
}

async def fetch_verification_telemetry(client: httpx.AsyncClient, ledger: str, endpoint: str) -> dict:
    print(f'[FETCH] Querying verification from {ledger}...')
    response = await client.get(endpoint)
    print(f'[RECEIVE] Packets arrived from {ledger}')
    return {'ledger': ledger, 'status_code': response.status_code, 'data': response.json()}

async def main():
    start_time = time.perf_counter()

    async with httpx.AsyncClient() as shared_client:
        tasks = [
            fetch_verification_telemetry(shared_client, ledger, endpoint)
            for ledger, endpoint in VERIFICATION_ENDPOINTS.items()
        ]
        print(f'Launching {len(tasks)} network operations simultaneously over the event loop...\n')
        results = await asyncio.gather(*tasks)
        print('\n========================= VERIFICATION REPORT =========================\n')
        for record in results:
            print(f"Center: {record['ledger']:21} | Response: {record['status_code']}")
        
    end_time = time.perf_counter()
    print('\n============================ END OF  REPORT ============================\n')
    print(f"Total concurrent execution time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())