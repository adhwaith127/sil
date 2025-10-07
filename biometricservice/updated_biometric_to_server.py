#!/usr/bin/env python3
import asyncio
import websockets
import json
import requests
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import os
import platform
from typing import Dict
import csv
import sqlite3
import threading
import time
import signal
import sys

# Operating System Detection and Path Setup
if platform.system() == "Windows":
    BASE_DIR = r"E:\BiometricServer"
else:
    BASE_DIR = os.path.join(os.path.expanduser("~/Desktop"), "adwaith","biometricservice")

LOG_DIR = os.path.join(BASE_DIR, "logs")
ERROR_LOG_DIR = os.path.join(BASE_DIR, "error_logs")
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
DB_DIR = os.path.join(BASE_DIR, "database")

# Create directories
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ERROR_LOG_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'commands'), exist_ok=True)
os.makedirs(QUEUE_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# Enhanced Logging Configuration
class EnhancedLogger:
    """
    Custom logger that provides:
    1. Main tailable log file (with daily rotation)
    2. Separate categorized log files 
    3. Different log levels for filtering
    """
    
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.log_dir = os.path.join(base_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup main logger for tailing
        self.setup_main_logger()
        
        # Setup category-specific loggers
        self.setup_category_loggers()
    
    def setup_main_logger(self):
        """Setup the main tailable log with daily rotation"""
        self.main_logger = logging.getLogger('biometric_main')
        self.main_logger.setLevel(logging.DEBUG)
        
        # Main log file that can be tailed - rotates daily
        main_log_file = os.path.join(self.log_dir, "biometric_main.log")
        main_handler = RotatingFileHandler(
            main_log_file, 
            maxBytes=50*1024*1024,  # 50MB per file
            backupCount=7  # Keep 7 days of logs
        )
        
        # Format: timestamp - level - message - status_code
        main_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        self.main_logger.addHandler(main_handler)
        
        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(main_formatter)
        self.main_logger.addHandler(console_handler)
    
    def setup_category_loggers(self):
        """Setup separate loggers for different categories"""
        
        # Success logger
        self.success_logger = logging.getLogger('biometric_success')
        self.success_logger.setLevel(logging.INFO)
        
        # Error logger  
        self.error_logger = logging.getLogger('biometric_error')
        self.error_logger.setLevel(logging.ERROR)
        
        # Queue logger
        self.queue_logger = logging.getLogger('biometric_queue')
        self.queue_logger.setLevel(logging.INFO)
        
        # System logger
        self.system_logger = logging.getLogger('biometric_system')
        self.system_logger.setLevel(logging.INFO)
    
    def get_dated_handler(self, category):
        """Get a file handler with YYYY-MM-DD format for category logs"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{today}_{category}.log"
        filepath = os.path.join(self.log_dir, filename)
        
        handler = logging.FileHandler(filepath, mode='a', encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        return handler
    
    def log_success(self, employee_id, employee_name, device_id, response_time, status_code="SUCCESS"):
        """Log successful ERP processing"""
        message = f"Device:{device_id} | Employee:{employee_name}({employee_id}) | ResponseTime:{response_time:.2f}s | Status:{status_code}"
        
        # Log to main (tailable) log
        self.main_logger.info(message)
        
        # Log to dated success file
        success_handler = self.get_dated_handler("success")
        self.success_logger.addHandler(success_handler)
        self.success_logger.info(message)
        self.success_logger.removeHandler(success_handler)
        success_handler.close()
    
    def log_error(self, employee_id, employee_name, device_id, error_message, error_type, status_code="ERROR"):
        """Log error with detailed information"""
        message = f"Device:{device_id} | Employee:{employee_name}({employee_id}) | Error:{error_message} | Type:{error_type} | Status:{status_code}"
        
        # Log to main (tailable) log
        self.main_logger.error(message)
        
        # Log to dated error file
        error_handler = self.get_dated_handler("error")
        self.error_logger.addHandler(error_handler)
        self.error_logger.error(message)
        self.error_logger.removeHandler(error_handler)
        error_handler.close()
    
    def log_queue_operation(self, operation, employee_id, employee_name, details, status_code="QUEUE"):
        """Log queue operations (add, remove, retry)"""
        message = f"Operation:{operation} | Employee:{employee_name}({employee_id}) | Details:{details} | Status:{status_code}"
        
        # Log to main (tailable) log
        self.main_logger.info(message)
        
        # Log to dated queue file
        queue_handler = self.get_dated_handler("queue")
        self.queue_logger.addHandler(queue_handler)
        self.queue_logger.info(message)
        self.queue_logger.removeHandler(queue_handler)
        queue_handler.close()
    
    def log_system_event(self, event, details, status_code="SYSTEM"):
        """Log system events (startup, shutdown, device connections)"""
        message = f"Event:{event} | Details:{details} | Status:{status_code}"
        
        # Log to main (tailable) log
        self.main_logger.info(message)
        
        # Log to dated system file
        system_handler = self.get_dated_handler("system")
        self.system_logger.addHandler(system_handler)
        self.system_logger.info(message)
        self.system_logger.removeHandler(system_handler)
        system_handler.close()


# ERPNext Configuration
ERP_URL = "http://192.168.0.61:8000"
ERP_API = "api/method/sil.test.biometric_to_erp.add_checkin"

HOST = "0.0.0.0"
PORT = 8190

# Database Configuration
DB_FILE = os.path.join(DB_DIR, "attendance_queue.db")
RETRY_INTERVAL = 180  # 3 minutes
MAX_RETRY_HOURS = 24
MAX_RETRY_ATTEMPTS = 10

# Errors that should be queued for retry
QUEUEABLE_ERRORS = ["connection_error", "timeout", "server_error"]

# Initialize enhanced logger
enhanced_logger = EnhancedLogger(BASE_DIR)


class SQLiteQueueManager:
    """
    SQLite-based queue manager with proper retry logic:
    - Original record fails → Added to pending_checkins
    - Retry attempt fails → Only retry_count incremented (no new record)
    - Max retries reached → Moved to failed_checkins (removed from pending)
    - Success on retry → Removed from pending_checkins
    
    Using asyncio.Lock instead of threading.RLock because:
    1. This is an async application - asyncio.Lock is designed for async/await
    2. asyncio.Lock prevents blocking the event loop
    3. threading.RLock would block the entire event loop on database operations
    4. All our operations are async, so asyncio.Lock is the natural choice
    """
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
        # Using asyncio.Lock for async compatibility - prevents event loop blocking
        self.lock = asyncio.Lock()
    
    def init_database(self):
        """Initialize SQLite database with proper tables and indexes"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pending_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                employee_name TEXT NOT NULL,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                queued_at DATETIME NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_retry DATETIME,
                last_error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS failed_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                employee_name TEXT NOT NULL,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                queued_at DATETIME NOT NULL,
                failed_at DATETIME NOT NULL,
                total_attempts INTEGER DEFAULT 0,
                final_error TEXT,
                failure_reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for faster queries
        conn.execute('CREATE INDEX IF NOT EXISTS idx_employee_id ON pending_checkins(employee_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON pending_checkins(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_retry_count ON pending_checkins(retry_count)')
        
        conn.commit()
        conn.close()
        
        enhanced_logger.log_system_event("DATABASE_INIT", f"SQLite database initialized at {self.db_path}")
    
    async def save_to_queue(self, record_data):
        """Save failed record to queue - only creates ONE record"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                
                # Check if record already exists to prevent duplicates
                cursor = conn.execute('''
                    SELECT id FROM pending_checkins 
                    WHERE employee_id = ? AND timestamp = ? AND device_id = ?
                ''', (record_data['enrollid'], record_data['timestamp'], record_data['device_id']))
                
                existing = cursor.fetchone()
                if existing:
                    conn.close()
                    enhanced_logger.log_queue_operation(
                        "DUPLICATE_SKIP", 
                        record_data['enrollid'], 
                        record_data['name'],
                        f"Record already queued, skipping"
                    )
                    return True
                
                # Insert new record with retry_count = 0
                conn.execute('''
                    INSERT INTO pending_checkins 
                    (employee_id, employee_name, device_id, timestamp, queued_at, retry_count)
                    VALUES (?, ?, ?, ?, ?, 0)
                ''', (
                    record_data['enrollid'],
                    record_data['name'], 
                    record_data['device_id'],
                    record_data['timestamp'],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
                conn.close()
                
                enhanced_logger.log_queue_operation(
                    "ADD", 
                    record_data['enrollid'], 
                    record_data['name'],
                    f"Queued due to ERP failure"
                )
                
                # Get current queue size for monitoring
                queue_size = await self.get_queue_size()
                enhanced_logger.log_system_event(
                    "QUEUE_SIZE", 
                    f"Current queue size: {queue_size}"
                )
                
                return True
                
            except Exception as e:
                enhanced_logger.log_error(
                    record_data.get('enrollid', 'Unknown'),
                    record_data.get('name', 'Unknown'),
                    record_data.get('device_id', 'Unknown'),
                    f"Failed to save to queue: {str(e)}",
                    "DATABASE_ERROR"
                )
                return False
    
    async def get_queue_size(self):
        """Get current queue size"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute('SELECT COUNT(*) FROM pending_checkins')
                count = cursor.fetchone()[0]
                conn.close()
                return count
            except Exception as e:
                enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", "SYSTEM",
                    f"Failed to get queue size: {str(e)}",
                    "DATABASE_ERROR"
                )
                return 0
    
    async def get_pending_records(self):
        """Get all pending records - returns list of dictionaries"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row  # Makes results accessible by column name
                cursor = conn.execute('''
                    SELECT * FROM pending_checkins 
                    ORDER BY queued_at ASC
                ''')
                records = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return records
            except Exception as e:
                enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", "SYSTEM",
                    f"Failed to get pending records: {str(e)}",
                    "DATABASE_ERROR"
                )
                return []
    
    async def remove_from_queue(self, record_id):
        """Remove successfully processed record from queue"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute('SELECT employee_name, employee_id FROM pending_checkins WHERE id = ?', (record_id,))
                record = cursor.fetchone()
                
                if record:
                    conn.execute('DELETE FROM pending_checkins WHERE id = ?', (record_id,))
                    conn.commit()
                    
                    enhanced_logger.log_queue_operation(
                        "REMOVE",
                        record[1],  # employee_id
                        record[0],  # employee_name
                        f"Successfully processed and removed from queue"
                    )
                
                conn.close()
                return True
                
            except Exception as e:
                enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", "SYSTEM",
                    f"Failed to remove from queue: {str(e)}",
                    "DATABASE_ERROR"
                )
                return False
    
    async def increment_retry_count(self, record_id, error_message=None):
        """ONLY increment retry count and update error - NO new record creation"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute('''
                    UPDATE pending_checkins 
                    SET retry_count = retry_count + 1,
                        last_retry = ?,
                        last_error = ?
                    WHERE id = ?
                ''', (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    error_message,
                    record_id
                ))
                conn.commit()
                
                # Get updated retry count for logging
                cursor = conn.execute(
                    'SELECT retry_count, employee_id, employee_name FROM pending_checkins WHERE id = ?', 
                    (record_id,)
                )
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    new_retry_count, employee_id, employee_name = result
                    enhanced_logger.log_queue_operation(
                        "RETRY_INCREMENT",
                        employee_id,
                        employee_name,
                        f"Retry count incremented to {new_retry_count}. Error: {error_message}"
                    )
                
                return True
                
            except Exception as e:
                enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", "SYSTEM",
                    f"Failed to increment retry count: {str(e)}",
                    "DATABASE_ERROR"
                )
                return False
    
    async def move_to_failed(self, record_id, failure_reason="Max retry attempts exceeded"):
        """Move a record from pending to failed - removes from pending"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                
                # Get the record to move
                cursor = conn.execute('SELECT * FROM pending_checkins WHERE id = ?', (record_id,))
                record = cursor.fetchone()
                
                if record:
                    # Insert into failed_checkins
                    conn.execute('''
                        INSERT INTO failed_checkins 
                        (employee_id, employee_name, device_id, timestamp, queued_at, 
                         failed_at, total_attempts, final_error, failure_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record[1],  # employee_id
                        record[2],  # employee_name
                        record[3],  # device_id
                        record[4],  # timestamp
                        record[5],  # queued_at
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        record[6],  # retry_count
                        record[8],  # last_error
                        failure_reason
                    ))
                    
                    # Remove from pending
                    conn.execute('DELETE FROM pending_checkins WHERE id = ?', (record_id,))
                    
                    conn.commit()
                    
                    enhanced_logger.log_queue_operation(
                        "MOVE_TO_FAILED",
                        record[1],  # employee_id
                        record[2],  # employee_name
                        f"Reason: {failure_reason}"
                    )
                
                conn.close()
                return True
                
            except Exception as e:
                enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", "SYSTEM", 
                    f"Failed to move record to failed: {str(e)}",
                    "DATABASE_ERROR"
                )
                return False


class BiometricServer:
    def __init__(self, host='0.0.0.0', port=8190):
        self.host = host
        self.port = port
        self.connected_devices: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.device_info: Dict[str, str] = {}
        self.session = requests.Session()
        self.queue_manager = SQLiteQueueManager(DB_FILE)
        self.retry_task = None
        self.server = None
        self.shutdown_event = asyncio.Event()
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            enhanced_logger.log_system_event("SHUTDOWN_SIGNAL", f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGBREAK'):  # Windows
            signal.signal(signal.SIGBREAK, signal_handler)

    async def shutdown(self):
        """Graceful shutdown process"""
        enhanced_logger.log_system_event("SHUTDOWN_INITIATED", "Starting graceful shutdown")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # Close all WebSocket connections
        if self.connected_devices:
            enhanced_logger.log_system_event("CLOSING_CONNECTIONS", f"Closing {len(self.connected_devices)} device connections")
            disconnection_tasks = []
            for websocket in list(self.connected_devices.keys()):
                disconnection_tasks.append(self.close_websocket_gracefully(websocket))
            
            if disconnection_tasks:
                await asyncio.gather(*disconnection_tasks, return_exceptions=True)
        
        # Cancel retry task
        if self.retry_task and not self.retry_task.done():
            enhanced_logger.log_system_event("CANCELLING_RETRY_TASK", "Cancelling retry task")
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                enhanced_logger.log_system_event("RETRY_TASK_CANCELLED", "Retry task cancelled successfully")
        
        # Close HTTP session
        if self.session:
            self.session.close()
            enhanced_logger.log_system_event("HTTP_SESSION_CLOSED", "HTTP session closed")
        
        # Stop the WebSocket server
        if self.server:
            enhanced_logger.log_system_event("STOPPING_SERVER", "Stopping WebSocket server")
            self.server.close()
            await self.server.wait_closed()
            enhanced_logger.log_system_event("SERVER_STOPPED", "WebSocket server stopped")
        
        enhanced_logger.log_system_event("SHUTDOWN_COMPLETE", "Graceful shutdown completed")

    async def close_websocket_gracefully(self, websocket):
        """Gracefully close a WebSocket connection"""
        try:
            await websocket.close()
        except Exception as e:
            enhanced_logger.log_system_event("CONNECTION_CLOSE_ERROR", f"Error closing connection: {str(e)}")

    async def register_device(self, websocket, data):
        serial_number = data.get('sn')
        if not serial_number:
            enhanced_logger.log_error(
                "UNKNOWN", "UNKNOWN", "UNKNOWN",
                "Device registration failed: Missing serial number",
                "REGISTRATION_ERROR"
            )
            return {"ret": "reg", "result": False, "reason": "Missing serial number"}
            
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.connected_devices[websocket] = serial_number
        self.device_info[serial_number] = client_addr
        
        enhanced_logger.log_system_event(
            "DEVICE_REGISTERED",
            f"Device {serial_number} connected from {client_addr}"
        )
        
        return {"ret": "reg", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    def send_to_erp(self, punchingcode, name, timestamp_str, device_id):
        """Enhanced send_to_erp with better error classification and timing"""
        
        start_time = time.time()
        
        # Validate timestamp format
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            error_msg = f"Invalid timestamp format: {timestamp_str}"
            enhanced_logger.log_error(
                punchingcode, name, device_id,
                error_msg, "INVALID_DATA"
            )
            return False, "invalid_data", "Invalid timestamp format"

        payload = {
            "punchingcode": punchingcode,
            "employee_name": name,
            "time": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
            "device_id": device_id,
        }

        try:
            # Send request to ERP
            response = self.session.post(f"{ERP_URL}/{ERP_API}", data=payload, timeout=5)
            response_time = time.time() - start_time
            
            # Classify HTTP status codes
            if response.status_code == 200:
                # Check for success in JSON response
                try:
                    json_response = response.json()
                    
                    # Check for various error patterns in response
                    if "exception" in json_response:
                        error_msg = f"ERP Exception: {json_response.get('exception')}"
                        
                        # Classify ERP exceptions
                        if "No Employee found" in str(json_response.get('exception', '')):
                            enhanced_logger.log_error(
                                punchingcode, name, device_id,
                                error_msg, "EMPLOYEE_NOT_FOUND"
                            )
                            return False, "employee_not_found", "Employee not registered in ERP"
                        elif "Invalid time format" in str(json_response.get('exception', '')):
                            enhanced_logger.log_error(
                                punchingcode, name, device_id,
                                error_msg, "INVALID_DATA"
                            )
                            return False, "invalid_data", "Invalid timestamp format"
                        else:
                            enhanced_logger.log_error(
                                punchingcode, name, device_id,
                                error_msg, "SERVER_ERROR"
                            )
                            return False, "server_error", error_msg
                    
                    # If no errors detected, assume success
                    enhanced_logger.log_success(
                        punchingcode, name, device_id, response_time
                    )
                    return True, "success", "Checkin recorded successfully"
                    
                except ValueError:
                    # Non-JSON response but status 200 - might be success
                    if "success" in response.text.lower() or len(response.text.strip()) == 0:
                        enhanced_logger.log_success(
                            punchingcode, name, device_id, response_time
                        )
                        return True, "success", "Checkin recorded successfully"
                    else:
                        enhanced_logger.log_error(
                            punchingcode, name, device_id,
                            f"Invalid JSON response: {response.text}", "SERVER_ERROR"
                        )
                        return False, "server_error", f"Invalid JSON response: {response.text}"
            
            elif response.status_code in [500, 502, 503, 504]:
                enhanced_logger.log_error(
                    punchingcode, name, device_id,
                    f"ERP server error: {response.status_code}", "SERVER_ERROR"
                )
                return False, "server_error", f"ERP server error: {response.status_code}"
            
            else:
                enhanced_logger.log_error(
                    punchingcode, name, device_id,
                    f"HTTP Error {response.status_code}: {response.text}", "HTTP_ERROR"
                )
                return False, "server_error", f"HTTP Error {response.status_code}: {response.text}"
            
        except requests.exceptions.Timeout:
            enhanced_logger.log_error(
                punchingcode, name, device_id,
                "ERP server timeout - no response within 5 seconds", "TIMEOUT"
            )
            return False, "timeout", "ERP server timeout - no response within 5 seconds"
            
        except requests.exceptions.ConnectionError:
            enhanced_logger.log_error(
                punchingcode, name, device_id,
                "Cannot reach ERP server - connection failed", "CONNECTION_ERROR"
            )
            return False, "connection_error", "Cannot reach ERP server - connection failed"
            
        except Exception as e:
            enhanced_logger.log_error(
                punchingcode, name, device_id,
                f"Unexpected error: {str(e)}", "SYSTEM_ERROR"
            )
            return False, "system_error", f"Unexpected error: {str(e)}"

    async def store_attendance(self, records, device_id):
        """Process attendance records with proper retry logic"""
        if not records:
            enhanced_logger.log_error(
                "SYSTEM", "SYSTEM", device_id,
                "No records provided in request", "INVALID_REQUEST"
            )
            return {"ret": "sendlog", "result": False, "reason": "No records provided"}

        enhanced_logger.log_system_event(
            "PROCESSING_BATCH",
            f"Processing {len(records)} records from device {device_id}"
        )

        for record in records:
            name = record.get("name")
            enroll_id = record.get("enrollid")
            timestamp = record.get("time")
            
            if not enroll_id or not timestamp or not name:
                enhanced_logger.log_error(
                    enroll_id or "UNKNOWN", name or "UNKNOWN", device_id,
                    f"Incomplete record data: {record}", "INVALID_DATA"
                )
                continue

            # Prepare record data for potential queuing
            record_data = {
                "name": name,
                "enrollid": enroll_id,
                "timestamp": timestamp,
                "device_id": device_id
            }

            # Try to send to ERP with error classification
            success, error_type, error_message = self.send_to_erp(enroll_id, name, timestamp, device_id)
            
            if success:
                # Success - log to CSV
                await log_attendance_to_csv(enroll_id, name, device_id, "Success", timestamp)
                
            elif error_type in QUEUEABLE_ERRORS:
                # Queue-worthy error - add to SQLite queue (creates only ONE record)
                await self.queue_manager.save_to_queue(record_data)
                await log_attendance_to_csv(enroll_id, name, device_id, "Queued", timestamp)
                
            else:
                # Permanent error - log and don't queue
                await log_attendance_to_csv(enroll_id, name, device_id, "Failed", timestamp)

        return {"ret": "sendlog", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    async def retry_queued_records(self):
        """Background task to retry queued records with proper retry logic"""
        enhanced_logger.log_system_event("RETRY_TASK_STARTED", "Queue retry task started")
        
        try:
            while not self.shutdown_event.is_set():
                try:
                    # Wait for retry interval or shutdown signal
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=RETRY_INTERVAL)
                    # If we reach here, shutdown was signaled
                    break
                except asyncio.TimeoutError:
                    # Timeout is expected - continue with retry logic
                    pass
                
                pending_records = await self.queue_manager.get_pending_records()
                
                if not pending_records:
                    continue
                
                enhanced_logger.log_system_event(
                    "RETRY_BATCH",
                    f"Processing {len(pending_records)} queued records"
                )
                
                for record in pending_records:
                    # Check for shutdown signal during processing
                    if self.shutdown_event.is_set():
                        break
                        
                    record_id = record['id']
                    retry_count = record.get('retry_count', 0)
                    queued_at = datetime.strptime(record['queued_at'], "%Y-%m-%d %H:%M:%S")
                    
                    # Check if record has exceeded maximum retry attempts
                    if retry_count >= MAX_RETRY_ATTEMPTS:
                        await self.queue_manager.move_to_failed(
                            record_id, 
                            f"Max retry attempts exceeded ({MAX_RETRY_ATTEMPTS})"
                        )
                        await log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Failed (Max Retries)", 
                            record['timestamp']
                        )
                        continue
                    
                    # Check if record is too old
                    hours_since_queued = (datetime.now() - queued_at).total_seconds() / 3600
                    if hours_since_queued > MAX_RETRY_HOURS:
                        await self.queue_manager.move_to_failed(
                            record_id,
                            f"Time limit exceeded ({MAX_RETRY_HOURS} hours)"
                        )
                        await log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Failed (Timeout)", 
                            record['timestamp']
                        )
                        continue
                    
                    # Try to resend
                    success, error_type, error_message = self.send_to_erp(
                        record['employee_id'],
                        record['employee_name'],
                        record['timestamp'],
                        record['device_id']
                    )
                    
                    if success:
                        # Success - remove from queue
                        await self.queue_manager.remove_from_queue(record_id)
                        await log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Success (Retry)", 
                            record['timestamp']
                        )
                        
                    elif error_type in QUEUEABLE_ERRORS:
                        # Still a queue-worthy error - ONLY increment retry count (no new record)
                        await self.queue_manager.increment_retry_count(record_id, error_message)
                        
                    else:
                        # Permanent error discovered - move to failed
                        await self.queue_manager.move_to_failed(
                            record_id, 
                            f"Permanent error discovered: {error_message}"
                        )
                        await log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Failed (Permanent)", 
                            record['timestamp']
                        )
                    
        except Exception as e:
                enhanced_logger.log_error(
                "SYSTEM", "SYSTEM", "SYSTEM",
                f"Error in retry task: {str(e)}", "RETRY_ERROR"
            )
                    
        except asyncio.CancelledError:
            enhanced_logger.log_system_event("RETRY_TASK_CANCELLED", "Retry task cancelled during shutdown")
            raise
        except Exception as e:
            enhanced_logger.log_error(
                "SYSTEM", "SYSTEM", "SYSTEM",
                f"Fatal error in retry task: {str(e)}", "RETRY_FATAL_ERROR"
            )
        finally:
            enhanced_logger.log_system_event("RETRY_TASK_STOPPED", "Queue retry task stopped")

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
            enhanced_logger.log_error(
                "SYSTEM", "SYSTEM", self.connected_devices.get(websocket, "unknown"),
                f"Message processing error: {e}", "MESSAGE_ERROR"
            )
            return {"ret": "error", "result": False, "reason": str(e)}

    async def handle_device(self, websocket, path=None):
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        enhanced_logger.log_system_event("DEVICE_CONNECTED", f"Device connected: {client_addr}")
        
        try:
            async for message in websocket:
                # Check for shutdown during message processing
                if self.shutdown_event.is_set():
                    break
                    
                response = await self.process_message(websocket, message)
                if response:
                    await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            enhanced_logger.log_system_event("DEVICE_DISCONNECTED", f"Connection closed: {client_addr}")
        except Exception as e:
            enhanced_logger.log_error(
                "SYSTEM", "SYSTEM", self.connected_devices.get(websocket, "unknown"),
                f"Error handling device connection: {str(e)}", "CONNECTION_ERROR"
            )
        finally:
            if websocket in self.connected_devices:
                serial = self.connected_devices[websocket]
                del self.connected_devices[websocket]
                if serial in self.device_info:
                    del self.device_info[serial]
                enhanced_logger.log_system_event("DEVICE_UNREGISTERED", f"Device disconnected: {serial}")

    async def start_server(self):
        enhanced_logger.log_system_event("SERVER_STARTING", f"WebSocket server starting on {self.host}:{self.port}")
        
        # Start retry task
        self.retry_task = asyncio.create_task(self.retry_queued_records())
        
        # Create and start WebSocket server
        self.server = await websockets.serve(self.handle_device, self.host, self.port)
        enhanced_logger.log_system_event("SERVER_STARTED", f"Server listening on {self.host}:{self.port}")
        
        # Check for existing queued records on startup
        pending_count = await self.queue_manager.get_queue_size()
        if pending_count > 0:
            enhanced_logger.log_system_event(
                "STARTUP_QUEUE_CHECK", 
                f"Found {pending_count} pending records from previous session"
            )
        
        # Wait for shutdown signal
        try:
            await self.shutdown_event.wait()
        except KeyboardInterrupt:
            enhanced_logger.log_system_event("KEYBOARD_INTERRUPT", "Received keyboard interrupt")
        
        # Initiate shutdown
        await self.shutdown()


def clean_csv_field(field_value):
    """Clean field value for CSV compatibility"""
    if not isinstance(field_value, str):
        field_value = str(field_value)
    
    field_value = field_value.replace('\n', ' ').replace('\r', ' ')
    field_value = ' '.join(field_value.split())
    
    return field_value.strip()


async def log_attendance_to_csv(enroll_id, name, device_id, status, timestamp_str):
    """Log attendance with enhanced status tracking - made async for consistency"""
    try:
        punch_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        punch_time = datetime.now()
        enhanced_logger.log_error(
            enroll_id, name, device_id,
            f"Invalid timestamp format in CSV logging: {timestamp_str}", "TIMESTAMP_ERROR"
        )

    filename = punch_time.strftime("%Y-%m-%d") + ".csv"
    filepath = os.path.join(LOG_DIR, filename)
    file_exists = os.path.isfile(filepath)

    date_str = punch_time.strftime("%Y-%m-%d")
    time_str = punch_time.strftime("%H:%M:%S")

    clean_name = clean_csv_field(str(name))
    clean_status = clean_csv_field(str(status))
    clean_device_id = clean_csv_field(str(device_id))
    clean_enroll_id = clean_csv_field(str(enroll_id))

    try:
        # Use asyncio to prevent blocking during CSV writes
        def write_csv():
            with open(filepath, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                if not file_exists:
                    writer.writerow(["Date", "Time", "Enroll_ID", "Name", "Device_ID", "ERP_Status"])
                writer.writerow([
                    date_str, time_str, clean_enroll_id, clean_name, clean_device_id, clean_status
                ])
        
        # Run CSV writing in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_csv)
            
    except Exception as e:
        enhanced_logger.log_error(
            enroll_id, name, device_id,
            f"Failed to write CSV log: {str(e)}", "CSV_ERROR"
        )


async def main():
    """Main async function with proper exception handling"""
    server = BiometricServer(HOST, PORT)
    try:
        enhanced_logger.log_system_event("APPLICATION_STARTING", "Biometric server application starting")
        await server.start_server()
    except KeyboardInterrupt:
        enhanced_logger.log_system_event("APPLICATION_STOPPED", "Server stopped by user")
    except Exception as e:
        enhanced_logger.log_error(
            "SYSTEM", "SYSTEM", "SYSTEM",
            f"Server error: {e}", "FATAL_ERROR"
        )
    finally:
        enhanced_logger.log_system_event("APPLICATION_SHUTDOWN", "Application shutting down")


def run_server():
    """Entry point that handles event loop creation and cleanup"""
    loop = None
    try:
        # Create new event loop for clean startup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the main async function
        loop.run_until_complete(main())
        
    except KeyboardInterrupt:
        enhanced_logger.log_system_event("KEYBOARD_INTERRUPT", "Application interrupted by user")
    except Exception as e:
        enhanced_logger.log_error(
            "SYSTEM", "SYSTEM", "SYSTEM",
            f"Fatal application error: {str(e)}", "FATAL_ERROR"
        )
    finally:
        if loop:
            try:
                # Cancel all remaining tasks
                pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
                if pending_tasks:
                    enhanced_logger.log_system_event("CANCELLING_TASKS", f"Cancelling {len(pending_tasks)} pending tasks")
                    for task in pending_tasks:
                        task.cancel()
                    
                    # Wait for tasks to be cancelled
                    loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
                
                # Close the event loop
                loop.close()
                enhanced_logger.log_system_event("EVENT_LOOP_CLOSED", "Event loop closed successfully")
            except Exception as e:
                enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", "SYSTEM",
                    f"Error during event loop cleanup: {str(e)}", "CLEANUP_ERROR"
                )


if __name__ == "__main__":
    run_server()