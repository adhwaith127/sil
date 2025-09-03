#!/usr/bin/env python3
import asyncio
import websockets
import json
import requests
from datetime import datetime
import logging
import os
from typing import Dict
import csv
import threading
import tkinter as tk

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ERPNext Configuration
ERP_URL = "http://erpgulf.softlandindia.net/"
ERP_API = "/api/method/clean_plus.services.biometric_server_erp2.add_checkin"

HOST = "0.0.0.0"
PORT = 8080


class BiometricServer:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.connected_devices: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.device_info: Dict[str, str] = {}
        self.session = requests.Session()

        os.makedirs('commands', exist_ok=True)
        os.makedirs('logs', exist_ok=True)  # Create logs directory if not exists

    async def register_device(self, websocket, data):
        serial_number = data.get('sn')
        if not serial_number:
            return {"ret": "reg", "result": False, "reason": "Missing serial number"}
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.connected_devices[websocket] = serial_number
        self.device_info[serial_number] = client_addr
        logger.info(f"Device registered: {serial_number} from {client_addr}")
        return {"ret": "reg", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    def send_to_erp(self, punchingcode, name, timestamp_str, device_id):
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger.error(f"Invalid timestamp format: {timestamp_str}")
            return False

        payload = {
            "punchingcode": punchingcode,
            "employee_name": name,
            "time": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
            "device_id": device_id,
        }

        try:
            res = self.session.post(f"{ERP_URL}/{ERP_API}", data=payload, timeout=5)
            if res.status_code != 200:
                logger.error(f"ERP API error: {res.status_code} - {res.text}")
                return False
            logger.info(f"ERP Checkin log added for {name} at {payload['time']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send to ERP: {e}")
            return False

    async def store_attendance(self, records, device_id):
        if not records:
            return {"ret": "sendlog", "result": False, "reason": "No records provided"}

        for record in records:
            name = record.get("name")
            enroll_id = record.get("enrollid")
            timestamp = record.get("time")
            if not enroll_id or not timestamp or not name:
                continue

            success = self.send_to_erp(enroll_id, name, timestamp, device_id)
            status = "Success" if success else "ERP Failed"
            # log_attendance_to_csv(enroll_id, name, device_id, status, timestamp)

        return {"ret": "sendlog", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    async def process_message(self, websocket, message):
        try:
            data = json.loads(message)
            device_id = self.connected_devices.get(websocket, "unknown")

            if 'cmd' in data:
                cmd = data['cmd']
                if cmd == 'reg':
                    return await self.register_device(websocket, data)
                elif cmd in ('sendlog', 'getalllog'):
                    return await self.store_attendance(data.get('record', []), device_id)

            return {"ret": data.get('cmd', 'unknown'), "result": True,
                    "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        except Exception as e:
            logger.error(f"Message processing error: {e}")
            return {"ret": "error", "result": False, "reason": str(e)}

    async def handle_device(self, websocket, path=None):
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Device connected: {client_addr}")
        try:
            async for message in websocket:
                response = await self.process_message(websocket, message)
                if response:
                    await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {client_addr}")
        finally:
            if websocket in self.connected_devices:
                serial = self.connected_devices[websocket]
                del self.connected_devices[websocket]
                logger.info(f"Device disconnected: {serial}")

    async def start_server(self):
        logger.info(f"WebSocket server starting on {self.host}:{self.port}")
        async with websockets.serve(self.handle_device, self.host, self.port):
            logger.info(f"Server listening on {self.host}:{self.port}")
            await asyncio.Future()  # Keeps running


def log_attendance_to_csv(enroll_id, name, device_id, status, timestamp_str):
    try:
        punch_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        punch_time = datetime.now()

    filename = punch_time.strftime("%Y-%m") + ".csv"
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    filepath = os.path.join(log_dir, filename)

    file_exists = os.path.isfile(filepath)

    with open(filepath, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Enroll ID", "Name", "Device ID", "ERP Status"])
        writer.writerow([
            punch_time.strftime("%Y-%m-%d %H:%M:%S"),
            enroll_id,
            name,
            device_id,
            status
        ])


# ---------------------------
# Tkinter GUI for Start/Stop/Restart
# ---------------------------
class ServerController:
    def __init__(self, status_callback=None):
        self.server = BiometricServer(HOST, PORT)
        self.loop = None
        self.thread = None
        self.ws_server = None   # store the running websocket server
        self.status_callback = status_callback  # callback to update UI

    def start(self):
        if self.thread and self.thread.is_alive():
            logger.info("Server already running")
            return
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Server started")
        if self.status_callback:
            self.status_callback("🟢 Running")

    def _run(self):
        asyncio.set_event_loop(self.loop)

        async def runner():
            self.ws_server = await websockets.serve(
                self.server.handle_device,
                self.server.host,
                self.server.port
            )
            logger.info(f"Server listening on {self.server.host}:{self.server.port}")

        self.loop.run_until_complete(runner())
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self._shutdown())

    async def _shutdown(self):
        if self.ws_server:
            self.ws_server.close()
            await self.ws_server.wait_closed()
            logger.info("WebSocket server closed")

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join()
            self.loop = None
            self.thread = None
            self.ws_server = None
            logger.info("Server stopped")
            if self.status_callback:
                self.status_callback("🔴 Stopped")

    def restart(self):
        logger.info("Restarting server...")
        self.stop()
        self.start()


def run_ui():
    root = tk.Tk()
    root.title("Biometric Server Control")

    status_label = tk.Label(root, text="🔴 Stopped", font=("Arial", 12, "bold"))
    status_label.pack(pady=10)

    def update_status(text):
        status_label.config(text=text)
        print(f"STATUS: {text}")  # also log in terminal

    controller = ServerController(status_callback=update_status)

    start_btn = tk.Button(root, text="Start", command=controller.start, width=20)
    start_btn.pack(pady=5)

    stop_btn = tk.Button(root, text="Stop", command=controller.stop, width=20)
    stop_btn.pack(pady=5)

    restart_btn = tk.Button(root, text="Restart", command=controller.restart, width=20)
    restart_btn.pack(pady=5)

    # 🔹 Ensure server stops when window is closed
    def on_close():
        if controller.thread and controller.thread.is_alive():
            controller.stop()  # ensure server thread is stopped
            logger.info("Server stopped due to window close")
            print("Server stopped due to window close")  # visible in terminal
        root.destroy()


    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()


def run_ui():
    controller = ServerController()

    root = tk.Tk()
    root.title("Biometric Server Control")

    start_btn = tk.Button(root, text="Start", command=controller.start, width=20)
    start_btn.pack(pady=5)

    stop_btn = tk.Button(root, text="Stop", command=controller.stop, width=20)
    stop_btn.pack(pady=5)

    restart_btn = tk.Button(root, text="Restart", command=controller.restart, width=20)
    restart_btn.pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    run_ui()