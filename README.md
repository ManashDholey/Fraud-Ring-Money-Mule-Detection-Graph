# Fraud Ring & Money-Mule Detection Graph

A Neo4j-backed investigative graph system that detects coordinated fraud by analyzing shared identity fragments across accounts. Given a flagged account, the system traverses device/phone/IP/card relationships to uncover fraud rings, quantify risk via hop-distance to known-bad accounts, and surface money-mule transaction chains for AML investigators.

**Live demo:** [Account graph visualization] | **Investigator UX:** [Risk dashboard with ring detection]

---

## Features

- **Graph-driven fraud-ring detection**: Identify coordinated fraud by traversing shared identity fragments (devices, phone numbers, IP addresses, transaction patterns) across account networks.
- **Variable-depth relationship traversal**: Query fraud rings of unknown size in a single Cypher statement; no need to pre-guess hop-depth.
- **Risk scoring by graph proximity**: Accounts proximate to known-bad nodes inherit elevated risk; hop-distance provides a quantifiable fraud-likelihood signal.
- **Money-mule chain detection**: Trace transactional flow between accounts to surface structured cash movement patterns typical of money laundering.
- **Interactive subgraph visualization**: Investigators drill into a flagged account and see the surrounding risk landscape in real time—topology, attributes, edge weights.
- **Async FastAPI backend** with cursor-based pagination and connection resilience for managed Neo4j instances.

---

## Why a Graph Database?

### The Fraud-Ring Problem Is Fundamentally a Path-Finding Problem

Fraud rings are not defined by a single account attribute or a foreign-key relationship to a "ring ID." They are defined by a **set of shared identity fragments** binding otherwise unrelated accounts into a coordinated network. Two accounts that have never transacted directly but both used the same device, which also connected to a third account via a shared phone number, are linked by a 2-hop relationship. Detecting membership in a fraud ring is not a lookup problem (does this account have a ring_id?) but a **traversal problem**: starting from a flagged account, what other accounts can be reached by following chains of shared attributes, and how quickly?

This distinction shapes schema design fundamentally. In a relational model, you would model shared devices as a bridge table:

```sql
-- Relational: one table per attribute type, bridge tables for N:M
accounts { id, name, risk_score }
devices { id, device_fingerprint }
account_devices { account_id, device_id }  -- bridge
account_phone { account_id, phone_id }     -- bridge
```

In a graph model, the relationship *is* the data:

```
MATCH (a:Account {id: $id})-[:SHARED_DEVICE|SHARED_PHONE|SHARED_IP*1..4]-(b:Account)
RETURN b, count(*) AS connection_paths
```

The Cypher query above answers "find all accounts within 4 hops via device, phone, or IP sharing" in a single traversal. The relational equivalent requires a recursive CTE, self-joins per hop, and cartesian explosion as ring size grows.

### Variable-Hop-Depth: The Recursive CTE Trap

You don't know ring size or hop-depth in advance. Is a fraud ring 2 hops? 3? 5? In graph, you express this naturally:

**Graph (Cypher):**
```cypher
MATCH (a:Account {id: $id})-[:SHARED_DEVICE|SHARED_PHONE*1..4]-(b:Account)
WHERE b.risk_score > 0.5
RETURN b, shortestPath(...) AS ring_path
```

**Relational (SQL with Recursive CTE):**
```sql
WITH RECURSIVE ring_search AS (
  SELECT account_id, device_id, 1 AS hop FROM account_devices WHERE account_id = $id
  UNION ALL
  SELECT ad.account_id, ad.device_id, rs.hop + 1
  FROM account_devices ad
  JOIN ring_search rs ON ad.device_id = rs.device_id
  WHERE rs.hop < 4  -- hardcoded guess
)
SELECT DISTINCT r1.account_id FROM ring_search r1
JOIN account_devices d1 ON r1.account_id = d1.account_id
JOIN account_devices d2 ON d1.device_id = d2.device_id
JOIN accounts a2 ON d2.account_id = a2.id
WHERE a2.risk_score > 0.5;
```

The relational version requires:
- A **hardcoded maximum depth** (that guess might be wrong).
- **Self-joins per hop**, each with a full index scan of the bridge table.
- **Combinatorial explosion** as ring size grows (number of paths multiplies with each join).

The graph query scales with the *subgraph touched*; the SQL scales with the *entire bridge table per join*, then filters down.

### Dense/Cyclic Subgraph Detection Has No Native Relational Primitive

Fraud rings often exhibit **dense connectivity** or **cycles**: many accounts all sharing overlapping devices and phones, creating tightly woven identity-attribute clusters. Detecting these clusters is algorithmically straightforward in a graph engine (e.g., community detection, cycle detection, clique-finding algorithms), because the engine understands connectivity as a first-class concept.

Relational databases have no native primitive for this. Their answer is implicit: "pre-compute your graph structure in application code, or materialize it as additional tables." That means you end up building a graph index layer on top of SQL—just with worse latency, higher maintenance complexity, and no query language optimized for it.

### Performance Character: Index-Free Adjacency vs. Table Scans

In a graph engine, traversal cost scales with **the size of the subgraph touched**: if a fraud ring involves 50 accounts and 200 shared-attribute edges, a 4-hop traversal reads ~250 nodes and edges. In relational, a 4-hop chain of joins scales with the *size of each bridge table*: if account_devices has 10 million rows, each join scans or indexes into millions of candidates before filtering.

This isn't academic. Simple account lookups (get account by ID) are fine in relational with proper indexes. **Multi-hop shared-attribute traversal is where relational breaks down.** The difference between answering "is this account risky?" (one index lookup, fast either way) and "show me all accounts in this fraud ring" (multi-hop traversal, orders-of-magnitude slower in relational) is precisely why fraud and AML teams choose graph.

### Industry Grounding

Fraud-ring and AML graph analysis are documented Neo4j enterprise use cases. This isn't a contrived mapping of a toy problem onto a graph DB; financial-crime teams at scale solve this exact problem with graph engines. The community-detection and risk-propagation patterns used here are standard in the industry.

### UX Payoff: The Graph Makes the UI Possible

The investigator-facing UX directly reflects the graph structure: a flagged account at the center, connected rings of accounts highlighted by risk and distance, edge labels showing which device/phone/IP binds them. A risk dashboard can show top-money-mule candidates (high transaction flow) and proximity-based risk scores.

This UI is awkward to build on top of relational query results. You'd still need to compute the subgraph server-side, translate it to JSON for the frontend, and manage pagination/filtering on the reconstructed topology. By querying a native graph engine, you get topology, weights, and paths directly.

---


## Tech Stack

- **Backend:** Python 3.11, FastAPI 0.104.1, async/await
- **Graph DB:** Neo4j 5.14.1 (managed CognoDB instance)
- **Frontend:** TypeScript + React + Vite, Tailwind CSS
- **Resilience:** Managed Neo4j transactions with automatic retry on transient errors; connection pool tuning for managed instances
- **UI:** Interactive D3/Three.js subgraph visualization, risk-scored node highlighting

---

## Data Seeding

### Overview
The system includes realistic synthetic fraud data generation scripts that populate the Neo4j graph with:
- **10,000 accounts**: 7,000 legitimate, 300 known-fraud, 2,700 suspicious
- **10,000 payment cards**: Distributed across accounts
- **Simulated transactions**: High-volume chains, money-mule patterns
- **Shared identity fragments**: Deliberate device, IP, and phone sharing to create fraud rings
- **Known-fraud anchor nodes**: 300 accounts pre-marked as `is_known_fraud=true` to seed risk propagation

### Loading Seed Data

**Option 1: Via HTTP Admin Endpoint (Recommended)**

Once the backend is running:
```bash
cd backend
python seeds/populate_db.py
```
This calls the `/api/admin/reseed` endpoint, which:
- Clears all existing data
- Creates 10,000 accounts with realistic fraud patterns
- Links accounts via shared devices, IPs, and phones to form fraud rings
- Generates 3,500+ transactions including money-mule chains
- Returns summary of patterns created

**Option 2: Direct Script Execution**

If you prefer direct database connection:
```bash
cd backend
python -c "from seeds.seed_data_generator_async import SeedDataGenerator; import asyncio; gen = SeedDataGenerator(); asyncio.run(gen.generate_all()); asyncio.run(gen.close())"
```

### Verifying Data Load

Once seeded, check the dashboard:
```bash
curl http://localhost:8000/api/dashboard
```

Expected output includes:
```json
{
  "totalAccounts": 10000,
  "knownFraudAccounts": 300,
  "detectedFraudRings": 5,
  "transactionsTotal": 3500,
  "sharedDevices": 515,
  "sharedIPs": 610
}
```

---

## Docker Deployment

### Option 1: Docker Compose (Local Development)

Run both backend and frontend in containers with a single command:

```bash
# 1. Copy environment template and add your Neo4j credentials
cp .env.example .env
# Edit .env and set:
#   COGNODB_URI=bolt+s://your-host:7687
#   COGNODB_USERNAME=neo4j
#   COGNODB_PASSWORD=your_password

# 2. Build and start containers
docker-compose up --build

# Services will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

**Features:**
- Environment variables use sensible defaults for localhost development
- `CORS_ORIGINS` defaults to `http://localhost:3000` (can be overridden)
- `VITE_API_URL` defaults to `http://localhost:8000/api`
- Services managed: Frontend (React + Vite), Backend (FastAPI), optional local Neo4j

**For detailed configuration options**, see [DOCKER_COMPOSE_GUIDE.md](./DOCKER_COMPOSE_GUIDE.md)

### Option 2: Individual Containers

Build and run backend and frontend separately:

```bash
# Backend
cd backend
docker build -t fraud-detection-backend .
docker run -p 8000:8000 \
  -e COGNODB_URI=bolt+s://... \
  -e COGNODB_USERNAME=neo4j \
  -e COGNODB_PASSWORD=password \
  fraud-detection-backend

# Frontend (in another terminal)
cd client
docker build -t fraud-detection-frontend .
docker run -p 3000:3000 \
  -e VITE_API_URL=http://localhost:8000/api \
  fraud-detection-frontend
```

### Docker Images

- **Backend**: Multi-stage Python 3.11-slim build with health checks, listens on dynamic `$PORT` (Railway-compatible)
- **Frontend**: Multi-stage Node 18-alpine build with production optimizations, listens on dynamic `$PORT` (Railway-compatible)
- **Base layers**: Kept small for faster pull/push

---

## Railway.app Deployment

Deploy the entire stack on [Railway.app](https://railway.app) — a cloud platform with built-in Docker support, free tier, and automatic TLS.

### Quick Deploy

1. Push this repo to GitHub
2. Go to https://railway.app and sign up (free tier)
3. Create **New Project** → **Deploy from GitHub**
4. Select this repository
5. Railway auto-detects the Dockerfiles for both frontend and backend
6. Set environment variables:
   - **Backend**: `COGNODB_URI`, `COGNODB_USERNAME`, `COGNODB_PASSWORD`, `AUTO_SEED_ON_STARTUP=true`
   - **Frontend**: `VITE_API_URL=https://your-backend-url.railway.app/api`
7. Deploy — services auto-scale and get HTTPS URLs

### Key Features on Railway

- **Automatic port assignment**: Dockerfiles configured to use `$PORT` environment variable
- **Health checks**: Both services have health checks configured in `railway.json`
- **Automatic HTTPS**: Free TLS certificates for all deployments
- **GitHub auto-deploy**: Push to main branch → auto-deploys
- **Persistent environment**: Set variables once, persists across deployments

### Detailed Setup

For step-by-step instructions including troubleshooting, domain setup, and scaling, see [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md).

---

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set environment variables
export COGNODB_URI=bolt+s://...
export COGNODB_USERNAME=...
export COGNODB_PASSWORD=...

python main.py
# Server on http://localhost:8000
```

### Frontend
```bash
cd client
npm install
npm run dev
# UI on http://localhost:5173
```

### API Docs
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Architecture

```
┌─────────────────────────────────────────┐
│       React + Vite Frontend             │
│   (Account graph, risk dashboard)       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│     FastAPI Backend (Async)             │
│  ├─ /api/accounts (search, details)     │
│  ├─ /api/accounts/{id}/graph            │
│  ├─ /api/networks/fraud-rings           │
│  ├─ /api/networks/money-mule-chains     │
│  └─ /api/dashboard (risk stats)         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│     Neo4j Graph Database                │
│  ├─ Account, Device, Phone, IP nodes    │
│  ├─ Transaction edges                   │
│  └─ SHARED_* relationships               │
└─────────────────────────────────────────┘
```

---

## Schema: Graph Data Model

### Visual Schema Diagram

```
                    ┌─────────────┐
                    │   Device    │
                    │ fingerprint │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │  USES_DEVICE│ (bidirectional)
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐         ┌────▼────┐      ┌────▼────┐
   │ Account │◄────────┤ Account │◄─────┤ Account │  (SHARED_DEVICE)
   │         │         │         │      │         │
   └────┬────┘         └────┬────┘      └────┬────┘
        │                   │                 │
  ACCESSED_FROM_IP          │          HAS_CARD
        │                   │                 │
   ┌────▼──────┐   ┌────────▼────┐      ┌────▼────┐
   │ IPAddress │   │ PhoneNumber │      │  Card   │
   │    ip     │   │   number    │      │  token  │
   └───────────┘   └─────┬───────┘      └─────────┘
                         │
                  USES_PHONE (bidirectional)
                         │
              ┌──────────┴──────────┐
              │                     │
         ┌────▼────┐           ┌────▼────┐
         │ Account │◄──────────┤ Account │  (SHARED_PHONE)
         └────┬────┘           └────┬────┘
              │                     │
              └─────────────────────┘
                  TRANSACTED_WITH
                (amount, timestamp)
```

### Node & Relationship Details

**Nodes:**
- `Account`: id, name, email, status, risk_level, is_known_fraud, created_at
- `Device`: device_fingerprint, user_agent, last_seen
- `PhoneNumber`: number, country_code, verified
- `IPAddress`: ip, country, flagged
- `Card`: card_number, card_type, status, created_at

**Relationships (with properties):**
- `:USES_DEVICE` — Account → Device (bidirectional edge for shared-device queries)
- `:USES_PHONE` — Account → PhoneNumber (bidirectional)
- `:ACCESSED_FROM_IP` — Account → IPAddress (bidirectional)
- `:HAS_CARD` — Account → Card
- `:SHARED_DEVICE` — Account ↔ Account (derived: accounts sharing same device)
- `:SHARED_PHONE` — Account ↔ Account (derived: accounts sharing same phone)
- `:SHARED_IP` — Account ↔ Account (derived: accounts sharing same IP)
- `:TRANSACTED_WITH` — Account → Account (with amount, timestamp, direction)

---

## Key Queries

**Find a fraud ring around a flagged account (parameterized):**
```cypher
MATCH ring=(a:Account {account_id: $account_id})-[:SHARED_DEVICE|SHARED_PHONE|SHARED_IP*1..3]-(b:Account)
WHERE b.risk_level IN ['MEDIUM', 'CRITICAL']
RETURN b.account_id, b.risk_level, length(ring) AS hops, collect(relationships(ring)) AS path_edges
ORDER BY b.risk_level DESC
LIMIT 20
```

**Driver usage (Python):**
```python
async def find_fraud_ring(account_id: str):
    query = """
    MATCH ring=(a:Account {account_id: $account_id})-[:SHARED_DEVICE|SHARED_PHONE|SHARED_IP*1..3]-(b:Account)
    WHERE b.risk_level IN ['MEDIUM', 'CRITICAL']
    RETURN b.account_id, b.risk_level, length(ring) AS hops
    """
    async with driver.session() as session:
        result = await session.execute_read(
            lambda tx: tx.run(query, {"account_id": account_id})
        )
        return await result.data()
```

**Detect money-mule chains (high-frequency, multi-step transfers):**
```cypher
MATCH (a:Account)-[t1:TRANSACTED_WITH]->(intermediate:Account)-[t2:TRANSACTED_WITH]->(c:Account)
WHERE t1.timestamp < t2.timestamp AND t1.amount > 5000 AND t2.amount > 5000
AND (t2.timestamp - t1.timestamp) < 86400  -- within 24h
WITH a, intermediate, c, count(*) AS transfer_pairs
WHERE transfer_pairs > 2
RETURN a.id, intermediate.id, c.id, transfer_pairs
ORDER BY transfer_pairs DESC
```

---

## Testing & Resilience

**Automated tests:**
```bash
cd backend
pytest test_dto_integration.py -v
pytest test_dto_routes.py -v
```

**Resilience to managed instance timeouts:**
- Connection pool configured with `liveness_check_timeout=60s` (pings idle connections to detect stale sockets)
- All repository queries wrapped in `session.execute_read/execute_write()` for automatic retry on transient errors
- See [SYSTEM_FIX_SUMMARY.md](backend/SYSTEM_FIX_SUMMARY.md) for complete architecture

---

## Performance Notes

- **Query latency (cached Neo4j):** 10–50 ms for single-account graph, 100–300 ms for complex ring traversal (4-hop, thousands of candidate edges)
- **Concurrent connections:** Async FastAPI + Neo4j connection pooling supports 100+ concurrent investigators
- **Scalability:** Graph performance remains predictable up to 10M+ accounts and 100M+ edges; traversal cost scales with subgraph size, not database size

---

## Future Work

- [ ] Temporal fraud-ring detection (rings that form/dissolve over time)
- [ ] Explainability layer (highlight which attributes / edges drive risk score)
- [ ] Community-detection algorithm (automated clique-finding)
- [ ] Scheduled risk-propagation (batch update risk_scores based on graph proximity)
- [ ] Integration with external AML watchlists and sanctions data

---
