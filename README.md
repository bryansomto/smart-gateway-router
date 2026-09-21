# Smart Payment Gateway Router (High-Availability Switch)

An intelligent, asynchronous payment routing middleware designed to solve infrastructure latency and gateway downtime in the Nigerian fintech ecosystem.

## The Problem

No single payment gateway maintains 100% uptime. Merchants lose revenue when the underlying banking infrastructure experiences temporary latency or 503 Service Unavailable errors.

## The Solution

This project acts as a high-availability middleware. It intercepts checkout requests and dynamically routes them to the most stable gateway (e.g., Paystack, Flutterwave, Interswitch). It features a built-in "Chaos Monkey" simulation to mimic real-world Nigerian network volatility, including random latency spikes and hard failures.

## Current Features (Phases 1 & 2)

* **Chaos Monkey Environment:** Mock endpoints simulating real-world gateway unreliability (80% success, 15% latency spikes, 5% hard failures).
* **Smart Failover Routing:** Asynchronous HTTP routing using `httpx`. If the primary gateway fails or exceeds a strict 1.5-second timeout, the transaction is gracefully and instantly routed to a backup gateway.

## Tech Stack

* **Backend:** Python 3, FastAPI, Uvicorn
* **Async HTTP:** HTTPX

## How to Run Locally

1. **Clone the repository and navigate to the directory:**

   ```bash
   git clone <your-repo-url>
   cd smart-gateway-router
   ```
2. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. **Install dependencies:**

   ```bash
   pip install fastapi "uvicorn[standard]" httpx
   ```
4. **Run the server:**

   ```bash
   uvicorn main:app --reload
   ```
5. **Test the API:**

   ```
   Navigate to http://127.0.0.1:8000/docs to use the interactive Swagger UI. Test the /smart-router/charge endpoint to see the failover logic in action.
   ```

## Upcoming Roadmap

* **Phase 3 (Data Science & Redis):** Implementing an anomaly detection engine. By storing millisecond latency metrics in Redis, the system will calculate moving averages and Z-scores to predict and penalize degrading gateways before they trigger a hard timeout.
* **Phase 4 (Next.js Dashboard):** A React-based merchant analytics dashboard visualizing real-time traffic flow and revenue saved from failovers.