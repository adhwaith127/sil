#!/usr/bin/env python3
import asyncio
import websockets
import json
import requests
from datetime import datetime
import logging
import os
import platform
from typing import Dict
import csv

# Operating System Detection and Path Setup
if platform.system() == "Windows":
    BASE_DIR = r"C:\BiometricServer"
else:
    BASE_DIR = "/opt/biometric-server"

LOG_DIR = os.path.join(BASE_DIR, "logs")
ERROR_LOG_DIR = os.path.join(BASE_DIR, "error_logs")

# Create directories
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ERROR_LOG_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'commands'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'queue'), exist_ok=True)

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ERPNext Configuration
ERP_URL = "http://silerp.softlandindia.net"
ERP_API = "api/method/clean_plus.services.biometric_server_erp.add_checkin"

HOST = "0.0.0.0"
PORT = 8190

def write_error_log(employee_id, employee_name, device_id, error_message, timestamp_str):
    """
    Write detailed error information to a separate error log file
    """
    try:
        # Create daily error log file name
        today = datetime.now().strftime("%Y-%m-%d")
        error_filename = f"{today}_errors.txt"
        error_filepath = os.path.join(ERROR_LOG_DIR, error_filename)
        
        # Prepare error entry
        error_entry = f"""
================================================================================
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Employee ID: {employee_id}
Employee Name: {employee_name}
Device ID: {device_id}
Punch Time: {timestamp_str}
Error Details: {error_message}
================================================================================
"""
        
        # Write to error file
        with open(error_filepath, 'a', encoding='utf-8') as f:
            f.write(error_entry)
            
    except Exception as e:
        logger.error(f"Failed to write error log: {str(e)}")

class BiometricServer:
    def __init__(self, host='0.0.0.0', port=8190):
        self.host = host
        self.port = port
        self.connected_devices: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.device_info: Dict[str, str] = {}
        self.session = requests.Session()

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
            error_msg = f"Invalid timestamp format: {timestamp_str}"
            logger.error(f"Invalid timestamp format: {timestamp_str}")
            write_error_log(punchingcode, name, device_id, error_msg, timestamp_str)
            return False, "Invalid Timestamp"

        payload = {
            "punchingcode": punchingcode,
            "employee_name": name,
            "time": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
            "device_id": device_id,
        }
        
        print("#####################")
        print("Sending to ERP:", payload)

        try:
            # Send request to ERP
            response = self.session.post(f"{ERP_URL}/{ERP_API}", data=payload, timeout=5)
            print("ERP Response:", response.text) 
            
            # Check HTTP status code
            if response.status_code != 200:
                detailed_error = f"HTTP Error {response.status_code}: {response.text}"
                logger.error(f"ERP API error for {name}: {detailed_error}")
                write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
                return False, "HTTP Error"
            
            # Try to parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                detailed_error = f"Invalid JSON Response: {response.text}"
                logger.error(f"ERP returned non-JSON response for {name}: {detailed_error}")
                write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
                return False, "Invalid Response"
            
            # Check for ERP-specific error fields
            if "exception" in json_response:
                detailed_error = f"ERP Exception: {json_response.get('exception')}"
                logger.error(f"ERP exception for {name}: {detailed_error}")
                write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
                return False, "ERP Exception"
            
            # Handle nested error structures in message field
            if "message" in json_response:
                message = json_response["message"]
                
                # Case 1: message is a dictionary with error information
                if isinstance(message, dict):
                    # Check for various error key patterns
                    for error_key in ["Error", "error", "ERROR", "exc", "exception"]:
                        if error_key in message:
                            detailed_error = f"ERP Message Error ({error_key}): {message[error_key]}"
                            logger.error(f"ERP error for {name}: {detailed_error}")
                            write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
                            return False, "ERP Error"
                    
                    # If it's a dict but no clear error key, check if any value contains error indicators
                    for key, value in message.items():
                        if isinstance(value, str) and any(indicator in value.lower() for indicator in ["error", "fail", "exception", "not added"]):
                            detailed_error = f"ERP Message Error ({key}): {value}"
                            logger.error(f"ERP error for {name}: {detailed_error}")
                            write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
                            return False, "ERP Error"
                
                # Case 2: message is a string
                elif isinstance(message, str) and any(indicator in message.lower() for indicator in ["error", "fail", "exception", "not added"]):
                    detailed_error = f"ERP Message Error: {message}"
                    logger.error(f"ERP error message for {name}: {detailed_error}")
                    write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
                    return False, "ERP Error"
            
            # If we reach here, the request was successful
            logger.info(f"ERP Checkin log successfully added for {name} at {payload['time']}")
            return True, "Success"
            
        except requests.exceptions.Timeout:
            detailed_error = "Request timeout - ERP server not responding within 5 seconds"
            logger.error(f"ERP request timeout for {name}")
            write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
            return False, "Timeout"
            
        except requests.exceptions.ConnectionError:
            detailed_error = "Connection error - Cannot reach ERP server"
            logger.error(f"ERP connection error for {name}")
            write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
            return False, "Connection Error"
            
        except Exception as e:
            detailed_error = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to send to ERP for {name}: {detailed_error}")
            write_error_log(punchingcode, name, device_id, detailed_error, timestamp_str)
            return False, "System Error"

    async def store_attendance(self, records, device_id):
        if not records:
            return {"ret": "sendlog", "result": False, "reason": "No records provided"}

        for record in records:
            name = record.get("name")
            enroll_id = record.get("enrollid")
            timestamp = record.get("time")
            
            if not enroll_id or not timestamp or not name:
                logger.warning(f"Incomplete record data: {record}")
                continue

            # Call the enhanced send_to_erp method
            success, error_message = self.send_to_erp(enroll_id, name, timestamp, device_id)
            
            # Simple status for CSV logging
            if success:
                status = "Success"
            else:
                status = "Failed"  # Simple status for CSV, detailed errors go to separate file
            
            # Log to CSV with clean status
            log_attendance_to_csv(enroll_id, name, device_id, status, timestamp)

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


def clean_csv_field(field_value):
    """Clean field value for CSV compatibility"""
    if not isinstance(field_value, str):
        field_value = str(field_value)
    
    # Replace newlines and carriage returns with spaces
    field_value = field_value.replace('\n', ' ').replace('\r', ' ')
    
    # Remove extra whitespaces
    field_value = ' '.join(field_value.split())
    
    return field_value.strip()


def log_attendance_to_csv(enroll_id, name, device_id, status, timestamp_str):
    # Convert timestamp string to datetime object
    try:
        punch_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        punch_time = datetime.now()
        logger.error(f"Invalid timestamp format in CSV logging: {timestamp_str} for employee {name}")

    # Daily CSV file
    filename = punch_time.strftime("%Y-%m-%d") + ".csv"
    filepath = os.path.join(LOG_DIR, filename)

    # Check if file already exists
    file_exists = os.path.isfile(filepath)

    # Split date and time
    date_str = punch_time.strftime("%Y-%m-%d")
    time_str = punch_time.strftime("%H:%M:%S")

    # Clean all fields for CSV
    clean_name = clean_csv_field(str(name))
    clean_status = clean_csv_field(str(status))
    clean_device_id = clean_csv_field(str(device_id))
    clean_enroll_id = clean_csv_field(str(enroll_id))

    # Write to CSV
    try:
        with open(filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)  # Force quotes around all fields
            if not file_exists:
                writer.writerow(["Date", "Time", "Enroll_ID", "Name", "Device_ID", "ERP_Status"])
            writer.writerow([
                date_str,
                time_str,
                clean_enroll_id,
                clean_name,
                clean_device_id,
                clean_status
            ])
            
    except Exception as e:
        logger.error(f"Failed to write CSV log for {name} ({enroll_id}): {str(e)}")


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