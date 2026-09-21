import asyncio
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import httpx

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

# Default routing priority
ROUTING_PRIORITY = ["paystack", "flutterwave", "interswitch"]

@app.post("/smart-router/charge")
async def smart_route_payment(request: RouteRequest):
    routing_history = []

    async with httpx.AsyncClient() as client:
        for gateway_name in ROUTING_PRIORITY:
            url = GATEWAYS[gateway_name]
            start_time = time.time()

            try:
                # Set a strict 1.5-second timeout. 
                # If a gateway takes longer than this, abandon it to save the customer's experience.
                response = await client.post(url, json=request.model_dump(), timeout=1.5)
                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    routing_history.append({
                        "gateway": gateway_name,
                        "status": "success",
                        "latency_ms": round(latency_ms, 2),
                    })

                    return {
                        "message": "Payment successful",
                        "final_gateway": gateway_name,
                        "routing_history": routing_history,
                    }
                else:
                    # Handle the 503 Service Unavailable errors simulated
                    routing_history.append({
                        "gateway": gateway_name,
                        "status": "failed",
                        "latency_ms": round(latency_ms, 2),
                        "error": "Gateway Error"
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
