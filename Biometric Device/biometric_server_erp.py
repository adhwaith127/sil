#!/usr/bin/env python3
import asyncio
import websockets
import json
import requests
import logging
import os
import csv
import configparser
import time
from datetime import datetime
from typing import Dict, Optional
from logging.handlers import TimedRotatingFileHandler

# --- Global Configuration ---
config = configparser.ConfigParser()
# Check for config file next to the script, then in /etc/
config_paths = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'),
    '/etc/attendance-system/config.ini'
]
config.read(config_paths)

# --- Logging Configuration ---
log_dir = config.get('Logging', 'LogDirectory', fallback='logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'biometric_server.log')

# Use a rotating file handler to prevent log files from growing indefinitely
handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(config.get('Logging', 'LogLevel', fallback='INFO'))
logger.addHandler(handler)
# Also log to console if needed (useful for debugging with systemd's journalctl)
logger.addHandler(logging.StreamHandler())


class BiometricServer:
    def __init__(self):
        # Load settings from config
        self.host = config.get('Server', 'Host', fallback='0.0.0.0')
        self.port = config.getint('Server', 'Port', fallback=8080)
        self.erp_url = config.get('ERP', 'URL')
        self.erp_api = config.get('ERP', 'APIEndpoint')
        self.auth_token = config.get('Security', 'AuthToken', fallback=None)

        self.connected_devices: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.device_info: Dict[str, str] = {}
        self.session = requests.Session()
        
        logger.info("Biometric Server class initialized.")

    def send_to_erp_with_retry(self, punchingcode: str, name: str, timestamp_str: str, device_id: str) -> bool:
        """
        Sends data to ERPNext with a retry mechanism for network-related failures.
        """
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            payload = {
                "punchingcode": punchingcode,
                "employee_name": name,
                "time": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
                "device_id": device_id,
            }
        except ValueError:
            logger.error(f"Invalid timestamp format received: {timestamp_str} for user {name} ({punchingcode})")
            return False

        max_retries = config.getint('ERP', 'MaxRetries', fallback=3)
        retry_delay = config.getint('ERP', 'RetryDelaySec', fallback=5)
        
        for attempt in range(max_retries):
            try:
                res = self.session.post(f"{self.erp_url}{self.erp_api}", data=payload, timeout=10)
                
                if res.status_code == 200:
                    logger.info(f"SUCCESS: ERP check-in for {name} ({punchingcode}) from device {device_id}.")
                    return True
                else:
                    logger.warning(f"ATTEMPT {attempt + 1}/{max_retries}: ERP API Error ({res.status_code}) for {name}. Response: {res.text}")
            
            except requests.exceptions.RequestException as e:
                logger.warning(f"ATTEMPT {attempt + 1}/{max_retries}: ERP connection error for {name}: {e}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1)) # Exponential backoff
        
        logger.error(f"FAILURE: All {max_retries} attempts to send data for {name} to ERP failed.")
        return False

    async def store_attendance_and_log(self, records: list, device_id: str) -> dict:
        """
        Processes attendance records, sends them to ERP, and logs the outcome to a local CSV file as a fallback.
        """
        if not records:
            return {"ret": "sendlog", "result": False, "reason": "No records provided"}

        logger.info(f"Received {len(records)} attendance records from device {device_id}.")

        for record in records:
            # Input validation
            name = record.get("name")
            enroll_id = record.get("enrollid")
            timestamp = record.get("time")

            if not all([enroll_id, timestamp, name]):
                logger.warning(f"Skipping malformed record from device {device_id}: {record}")
                continue

            # Send to ERP and get success status
            success = self.send_to_erp_with_retry(enroll_id, name, timestamp, device_id)
            status = "Success" if success else "ERP_Failed"
            
            # Log every attempt to a local CSV for audit/backup
            self.log_attendance_to_csv(enroll_id, name, device_id, status, timestamp)

        return {"ret": "sendlog", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    def log_attendance_to_csv(self, enroll_id: str, name: str, device_id: str, status: str, timestamp_str: str):
        """Logs a single attendance record to a monthly CSV file."""
        try:
            punch_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            filename = punch_time.strftime("%Y-%m") + "-attendance.csv"
            filepath = os.path.join(log_dir, filename)
            file_exists = os.path.isfile(filepath)

            with open(filepath, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Enroll ID", "Name", "Device ID", "ERP Status"])
                writer.writerow([
                    punch_time.strftime("%Y-%m-%d %H:%M:%S"),
                    enroll_id, name, device_id, status
                ])
        except Exception as e:
            logger.error(f"Failed to write to CSV log: {e}")

    async def register_device(self, websocket, data: dict) -> dict:
        """Registers a new device connection."""
        serial_number = data.get('sn')
        if not serial_number:
            logger.warning(f"Registration failed: Missing serial number from {websocket.remote_address}")
            return {"ret": "reg", "result": False, "reason": "Missing serial number"}
        
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.connected_devices[websocket] = serial_number
        self.device_info[serial_number] = client_addr
        logger.info(f"Device registered: {serial_number} from {client_addr}")
        return {"ret": "reg", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    async def process_message(self, websocket, message: str) -> Optional[dict]:
        """Parses incoming JSON messages and routes them to the correct handler."""
        try:
            data = json.loads(message)
            device_id = self.connected_devices.get(websocket, "unknown")
            cmd = data.get('cmd')

            if cmd == 'reg':
                return await self.register_device(websocket, data)
            elif cmd in ('sendlog', 'getalllog'):
                return await self.store_attendance_and_log(data.get('record', []), device_id)
            elif cmd is not None:
                # Acknowledge other known commands if necessary
                return {"ret": cmd, "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            else:
                logger.warning(f"Received message with no 'cmd' from {device_id}: {data}")
                return None

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from {self.connected_devices.get(websocket, 'unknown')}")
            return {"ret": "error", "result": False, "reason": "Invalid JSON format"}
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            return {"ret": "error", "result": False, "reason": str(e)}

    async def handle_http_request(self, path: str, headers) -> Optional[tuple]:
        """Handles non-WebSocket HTTP requests, like health checks."""
        if path == "/health":
            logger.info("Health check endpoint was hit.")
            # Basic health check: server is running. Could be expanded to check ERP connection.
            response_headers = [('Content-Type', 'application/json')]
            response_body = json.dumps({"status": "ok", "connected_devices": len(self.connected_devices)}).encode('utf-8')
            return (200, response_headers, response_body)
        return None # Let websockets handle it as a failed WS connection

    async def authenticate_connection(self, path: str, headers) -> Optional[tuple]:
        """
        Authenticates incoming connections using a bearer token if one is configured.
        """
        if not self.auth_token:
            return None # No token configured, allow connection

        auth_header = headers.get('Authorization')
        if not auth_header or f"Bearer {self.auth_token}" != auth_header:
            logger.warning(f"Failed authentication attempt from {headers.get('Host')}. Missing or incorrect token.")
            return (401, [], b"Unauthorized") # Reject connection
        
        logger.info("A device passed authentication.")
        return None # Authentication successful

    async def handler(self, websocket, path: str):
        """Main connection handler for each connected device."""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New connection attempt from: {client_addr}")
        
        try:
            async for message in websocket:
                response_data = await self.process_message(websocket, message)
                if response_data:
                    await websocket.send(json.dumps(response_data))
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Connection from {client_addr} closed unexpectedly: {e.code} {e.reason}")
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"Connection closed gracefully from {client_addr}")
        finally:
            if websocket in self.connected_devices:
                serial = self.connected_devices.pop(websocket)
                self.device_info.pop(serial, None)
                logger.info(f"Device disconnected and unregistered: {serial}")

    async def start(self):
        """Starts the WebSocket server."""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        # The `process_request` handles HTTP requests, `extra_headers` can do auth checks.
        server = websockets.serve(
            self.handler,
            self.host,
            self.port,
            process_request=self.handle_http_request,
            process_response=self.authenticate_connection
        )
        
        async with server:
            logger.info("Server is now listening for connections.")
            await asyncio.Future()  # Run forever


def main():
    logger.info("======================================================")
    logger.info("        Biometric Face Scanner Service STARTING       ")
    logger.info("======================================================")
    
    server = BiometricServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"A fatal error occurred, shutting down server: {e}", exc_info=True)
    finally:
        logger.info("======================================================")
        logger.info("        Biometric Face Scanner Service STOPPED        ")
        logger.info("======================================================")

if __name__ == "__main__":
    main()
