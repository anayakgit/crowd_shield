from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json

app = FastAPI()

# Store connected clients
connected_clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


# 🔔 Function to send alert to all apps
async def broadcast_alert(data):
    for client in connected_clients:
        try:
            await client.send_text(json.dumps(data))
        except:
            pass


# 🧪 TEST API (your website button will call this)
@app.post("/trigger-alert")
async def trigger_alert():
    alert_data = {
        "risk_level": "HIGH",
        "message": "🚨 Stampede risk detected!",
        "duration": "5 seconds"
    }

    await broadcast_alert(alert_data)

    return {"status": "alert sent"}