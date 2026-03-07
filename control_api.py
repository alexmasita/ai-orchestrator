from fastapi import FastAPI
from datetime import datetime, timezone
import json, os

app = FastAPI(title="Vast Instance Control API - High-Reasoning 80GB Duo")

STATE_FILE = "./state.json"
ACTIVITY_FILE = "/tmp/.last_request"

SERVICE_PORTS = {
    "architect": 8080,
    "developer": 8081,
    "stt": 9000,
    "tts": 9001,
}

@app.get("/status")
async def status():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"status": "unknown", "error": "state file not found"}

@app.get("/health")
async def health():
    import httpx
    results = {}
    for name, port in SERVICE_PORTS.items():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"http://localhost:{port}/health")
                results[name] = {"status": "up", "code": r.status_code}
        except Exception:
            results[name] = {"status": "down"}
    results["control"] = {"status": "up"}
    open(ACTIVITY_FILE, "w").close()
    return {"services": results, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/ping")
async def ping():
    open(ACTIVITY_FILE, "w").close()
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/stop")
async def stop():
    api_key = os.environ.get("VAST_API_KEY", "") or os.environ.get("CONTAINER_API_KEY", "")
    instance_id = os.environ.get("VAST_CONTAINERLABEL", "")
    if not api_key or not instance_id:
        return {"error": "API key or instance ID not available"}
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"state": "stopped"}
        )
        return {"action": "stop", "response": r.json()}

@app.post("/destroy")
async def destroy():
    api_key = os.environ.get("VAST_API_KEY", "") or os.environ.get("CONTAINER_API_KEY", "")
    instance_id = os.environ.get("VAST_CONTAINERLABEL", "")
    if not api_key or not instance_id:
        return {"error": "API key or instance ID not available"}
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return {"action": "destroy", "response": r.json()}
