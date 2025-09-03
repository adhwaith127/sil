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

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ERPNext Configuration
ERP_URL = "http://192.168.0.68:8001"
ERP_API = "/api/method/clean_plus.services.biometric_server_erp.add_checkin"

HOST = "0.0.0.0"
PORT = 8190


class BiometricServer:
    def __init__(self, host='0.0.0.0', port=8190):
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
        # Parse the timestamp string first
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            logger.info(f"Processing ERP request for {name} ({punchingcode}) at {timestamp}")
        except ValueError:
            logger.error(f"Invalid timestamp format: {timestamp_str}")
            return {"success": False, "error_type": "invalid_timestamp", 
                "message": f"Invalid timestamp format: {timestamp_str}"}
        
        # Create payload with properly formatted timestamp
        payload = {
            "punchingcode": punchingcode,
            "employee_name": name,
            "time": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
            "device_id": device_id,
        }

        try:
            logger.info(f"Sending to ERP: {payload}")
            res = self.session.post(f"{ERP_URL}/{ERP_API}", data=payload, timeout=5)
            
            # Check different response scenarios
            if res.status_code == 200:
                logger.info(f"ERP Success for {name} ({punchingcode})")
                return {"success": True, "message": "Attendance recorded"}
            
            elif res.status_code == 404:
                logger.warning(f"Employee not found in ERP: {name} ({punchingcode})")
                return {"success": False, "error_type": "employee_not_found", 
                    "message": f"Employee {name} not registered in ERP"}
            
            elif res.status_code == 400:
                logger.error(f"Bad request to ERP: {res.text}")
                return {"success": False, "error_type": "bad_request", 
                    "message": "Invalid data format"}
            
            else:
                logger.error(f"ERP server error: {res.status_code} - {res.text}")
                return {"success": False, "error_type": "server_error", 
                    "message": f"ERP server error: {res.status_code}"}
                    
        except requests.exceptions.Timeout:
            logger.error(f"ERP timeout for {name}")
            return {"success": False, "error_type": "timeout", 
                "message": "ERP server timeout"}
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to ERP server")
            return {"success": False, "error_type": "connection_error", 
                "message": "Cannot reach ERP server"}
            
        except Exception as e:
            logger.error(f"Unexpected ERP error: {e}")
            return {"success": False, "error_type": "unknown", 
                "message": f"Unexpected error: {str(e)}"}

    async def store_attendance(self, records, device_id):
        if not records:
            return {"ret": "sendlog", "result": False, "reason": "No records provided"}

        processed_records = []
        employee_not_found_count = 0
        server_error_count = 0
        success_count = 0

        for record in records:
            name = record.get("name")
            enroll_id = record.get("enrollid")
            timestamp = record.get("time")
            
            # Validate required fields
            if not enroll_id or not timestamp or not name:
                processed_records.append({
                    "employee": name or "Unknown",
                    "status": "failed",
                    "reason": "Missing required data"
                })
                continue

            # Send to ERP and get detailed result
            erp_result = self.send_to_erp(enroll_id, name, timestamp, device_id)
            
            if erp_result["success"]:
                success_count += 1
                processed_records.append({
                    "employee": name,
                    "status": "success",
                    "reason": "Attendance recorded"
                })
            else:
                # Handle specific error types
                error_type = erp_result.get("error_type", "unknown")
                
                if error_type == "employee_not_found":
                    employee_not_found_count += 1
                    processed_records.append({
                        "employee": name,
                        "status": "employee_not_found",
                        "reason": f"Employee {name} not registered in ERP"
                    })
                else:
                    server_error_count += 1
                    processed_records.append({
                        "employee": name,
                        "status": "failed",
                        "reason": erp_result["message"]
                    })

        # Create detailed response
        total_records = len(records)
        overall_success = (success_count == total_records)
        
        # Create meaningful message for device
        if employee_not_found_count > 0 and server_error_count == 0:
            main_message = f"{employee_not_found_count} employee(s) not registered in ERP"
        elif server_error_count > 0 and employee_not_found_count == 0:
            main_message = f"{server_error_count} record(s) failed due to server issues"
        elif employee_not_found_count > 0 and server_error_count > 0:
            main_message = f"{employee_not_found_count} not registered, {server_error_count} server errors"
        else:
            main_message = f"Processed {success_count}/{total_records} successfully"

        return {
            "ret": "sendlog", 
            "result": overall_success,
            "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": main_message,
            "details": processed_records
        }
    
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

    # Write header if file doesn't exist
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


def main():
    server = BiometricServer(HOST, PORT)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        loop.close()


if __name__ == "__main__":
    main()



