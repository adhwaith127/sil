import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:5022"
    async with websockets.connect(uri) as ws:
        print("Connected to server!")
        await ws.send(json.dumps({"cmd":"reg","sn":"TEST123"}))
        response = await ws.recv()
        print("Server response:", response)

asyncio.run(test())

