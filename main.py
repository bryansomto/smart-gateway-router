import asyncio
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import httpx
import statistics
import redis.asyncio as redis

app = FastAPI(title="Mock Payment Gateways")

class PaymentRequest(BaseModel):
    amount: float
    currency: str = "NGN"

async def simulate_network_conditions(gateway_name: str):
    """Simulates realistic Nigerian network latency and random provider failures."""
    chance = random.random()

    # 5% chance of a hard failure (503 Service Unavailable)
    if chance < 0.05:
        raise HTTPException(status_code=503, detail=f"{gateway_name} Timeout or Core Banking Error")

    # 15% chance of a severe latency spike (1 to 3 seconds)
    elif chance < 0.20:
        delay = random.uniform(1.0, 3.0)
        await asyncio.sleep(delay)
        return {"status": "success", "processing_time_sec": round(delay, 2), "note": "High latency"}

    # 80% chance of normal operation (50ms to 200ms)
    else:
        delay = random.uniform(0.05, 0.2)
        await asyncio.sleep(delay)
        return {"status": "success", "processing_time_sec": round(delay, 2), "note": "Normal"}

@app.post("/paystack/charge")
async def mock_paystack(request: PaymentRequest):
    condition = await simulate_network_conditions("Paystack")
    return {"gateway": "Paystack", "amount": request.amount, **condition}

@app.post("/flutterwave/charge")
async def mock_flutterwave(request: PaymentRequest):
    condition = await simulate_network_conditions("Flutterwave")
    return {"gateway": "Flutterwave", "amount_charged": request.amount, **condition}

@app.post("/interswitch/charge")
async def mock_interswitch(request: PaymentRequest):
    condition = await simulate_network_conditions("Interswitch")
    return {"gateway": "Interswitch", "amount_charged": request.amount, **condition}


class RouteRequest(BaseModel):
    amount: float
    currency: str = "NGN"

GATEWAYS = {
    "paystack": "http://127.0.0.1:8000/paystack/charge",
    "flutterwave": "http://127.0.0.1:8000/flutterwave/charge",
    "interswitch": "http://127.0.0.1:8000/interswitch/charge"
}

# Connect to local Redis
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

async def record_latency(gateway: str, latency_ms: float):
    """Stores the latest latency in Redis and keeps only the last 20 requests."""
    key = f"gateway:{gateway}:latencies"
    await redis_client.lpush(key, latency_ms)
    await redis_client.ltrim(key, 0, 19)    # Keep a sliding window of size 20

async def get_gateway_health(gateway: str) -> float:
    """
    Calculates a health score using Moving Average and Standard Deviation.
    Lower score = Faster, more stable gateway.
    """
    key = f"gateway:{gateway}:latencies"
    latencies =  await redis_client.lrange(key, 0, -1)

    if not latencies:
        return 0.0  # Perfect score if we have no data yet

    latencies = [float(l) for l in latencies]
    avg_latency = statistics.mean(latencies)

    # Calculate volatility (Standard Deviation)
    if len(latencies) > 1:
        volatility_penalty =  statistics.stdev(latencies)
    else:
        volatility_penalty = 0.0

    # The ultimate Data Science health score: Average Latency + Volatility
    return avg_latency + volatility_penalty

# Default routing priority
ROUTING_PRIORITY = ["paystack", "flutterwave", "interswitch"]

@app.post("/smart-router/charge")
async def smart_route_payment(request: RouteRequest):
    routing_history = []
    base_gateways = ["paystack", "flutterwave", "interswitch"]

    # Rank gateways based on their health score
    health_scores = {gw: await get_gateway_health(gw) for gw in base_gateways}

    # Sort gateways dynamically: Lowest score (healthiest) goes first!
    dynamic_priority = sorted(health_scores, key=health_scores.get)

    async with httpx.AsyncClient() as client:
        for gateway_name in dynamic_priority:
            url = GATEWAYS[gateway_name]
            start_time = time.time()

            try:
                # Set a strict 1.5-second timeout. 
                # If a gateway takes longer than this, abandon it to save the customer's experience.
                response = await client.post(url, json=request.model_dump(), timeout=1.5)
                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    # Log healthy latency
                    await record_latency(gateway_name, latency_ms)

                    routing_history.append({
                        "gateway": gateway_name,
                        "status": "success",
                        "latency_ms": round(latency_ms, 2),
                        "health_score_at_request": round(health_scores[gateway_name], 2)
                    })

                    return {
                        "message": "Payment successful",
                        "final_gateway": gateway_name,
                        "routing_order": dynamic_priority,
                        "routing_history": routing_history,
                    }
                else:
                    # Handle the 503 Service Unavailable errors and apply a massive penalty!
                    await record_latency(gateway_name, 3000)  # 3 seconds penalty for failed requests
                    routing_history.append({
                        "gateway": gateway_name,
                        "status": "failed",
                    })

            except httpx.TimeoutException:
                latency_ms = (time.time() - start_time) * 1000
                routing_history.append({
                    "gateway": gateway_name,
                    "status": "timeout",
                    "latency_ms": round(latency_ms, 2),
                })

        # If the loop finishes and no success is returned, ALL gateways failed.
        raise HTTPException(
            status_code=500, 
            detail={"message": "All payment gateways failed.", "routing_history": routing_history}
        )  
