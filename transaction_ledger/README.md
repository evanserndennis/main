# Concurrent E-Commerce Transaction Ledger & Auditing System

An enterprise-grade, memory-optimized transaction ingestion and auditing pipeline built natively in Python using SQLite. This system models a high-throughput financial ecosystem, demonstrating strict memory constraints, defensive relational schema configurations, and automated statistical anomaly tracking layers.

## System Architecture & Design Pillars

The repository is built around a decoupling methodology separating data generation, storage mechanics, and analysis processing across three distinct modules:

1. **`db_manager.py` (Shared Data Access Object Layer):** Serves as the localized configuration map and centralized database connection provider. Implements absolute workspace anchoring via `pathlib` to avoid working directory drift.
2. **`initialize_ledger.py` (Ingestion & Storage Engine):** Initializes database structures defensively using a "Check-Then-Act" schema validation pattern. Streams raw transactional fields sequentially to avoid high memory overhead and implements bulk transaction processing blocks.
3. **`audit_ledger.py` (Statistical Fraud & Reporting Engine):** Executes zero-allocation data operations over streaming database cursors. Computes rolling aggregate balances and implements standard deviation threshold parsing to track statistical outliers.

---

## Technical Core Competencies

### 1. Memory Optimization & Generative Streaming
To prevent out-of-memory crashes when managing thousands of items simultaneously, data ingestion relies strictly on non-allocating memory generators (`yield`). Raw metrics are parsed sequentially as iterable objects, flattening peak RAM consumption to a strict `O(1)` constant runtime footprint.

### 2. Atomic Database Ingestion
Ingestion integrity is protected using context-managed transaction blocks (`with conn:`). Data batches are mapped to single SQL queries via `executemany`. If any component throws an error midway through execution, the engine triggers an automatic transaction rollback, preventing data fragmentation or corrupted database states.

### 3. Statistical 3-Sigma Outlier Detection
Because SQLite leaves out advanced scientific functions to preserve its minimal system footprint, the auditing engine pulls raw numeric sequences into a flat data collection. It leverages the native `statistics` module to resolve the mean ($\mu$) and standard deviation ($\sigma$), safely routing parameterized thresholds back into a SQL filter:

$$\text{Outlier Boundary} = \mu \pm (3 \times \sigma)$$

---

## Directory Structure

```text
transaction-ledger/
│
├── .gitignore               # Quarantines local state assets (.env, venv/, *.db)
├── README.md                # System documentation and architecture breakdown
├── db_manager.py            # Centralized database connection pool module
├── initialize_ledger.py     # Schema creator and streaming ingestion engine
├── audit_ledger.py          # Aggregate metrics compiler and 3-Sigma detector
└── ledger.db                # Target relational SQLite storage file (Local Only)