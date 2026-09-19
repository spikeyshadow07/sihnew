from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import random

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

async def telemetry_generator():
    base_vehicles = 120
    while True:
        # Simulate realistic telemetry data
        fluctuation = random.randint(-15, 20)
        current_vehicles = max(0, base_vehicles + fluctuation)
        base_vehicles = current_vehicles
        
        data = {
            "vehicles_detected": current_vehicles,
            "risk_index": round(random.uniform(1.0, 10.0), 1),
            "active_anomalies": random.randint(0, 3),
            "system_health": "Optimal",
            "latency_ms": random.randint(12, 45)
        }
        
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(1.0) # Update every second

@router.get("/telemetry")
async def get_realtime_telemetry():
    return StreamingResponse(telemetry_generator(), media_type="text/event-stream")
