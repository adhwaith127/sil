#!/usr/bin/env python3
"""
Enhanced Biometric Server Desktop Application with GUI
Fixes duplicate log issues and implements daily log organization
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import asyncio
import queue
import sys
import os
import logging
from datetime import datetime, time
import json

from config_manager import ConfigurationManager
from settings_dialog import SettingsDialog

# Import all the original server modules
import websockets
import requests
from datetime import timedelta
from logging.handlers import RotatingFileHandler
import platform
from typing import Dict, Set
import csv
import sqlite3
import time as time_module
import weakref

# ============================================================================
# ENHANCED SERVER CODE WITH DUPLICATE PREVENTION
# ============================================================================

# Initialize configuration manager
config_manager = ConfigurationManager()

# Get configuration values
server_config = config_manager.get_server_config()
erp_config = config_manager.get_erp_config()
retry_config = config_manager.get_retry_config()

# Set global variables from configuration
BASE_DIR = server_config.get('base_dir', r"E:\BiometricServer")
HOST = server_config.get('host', "0.0.0.0")
PORT = server_config.get('port', 8190)

# Create necessary directories
os.makedirs(BASE_DIR, exist_ok=True)
LOG_DIR = os.path.join(BASE_DIR, "logs")
DB_DIR = os.path.join(BASE_DIR, "database")
QUEUE_DIR = os.path.join(BASE_DIR, "queue")

# Ensure all directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(QUEUE_DIR, exist_ok=True)

ERP_URL = erp_config.get('url', "http://192.168.0.61:8000")
ERP_API = erp_config.get('api_endpoint', "api/method/sil.test.biometric_to_erp.add_checkin")

RETRY_INTERVAL = retry_config.get('interval_seconds', 180)
MAX_RETRY_ATTEMPTS = retry_config.get('max_attempts', 10)
MAX_RETRY_HOURS = retry_config.get('max_hours', 24)

# Database Configuration
DB_FILE = os.path.join(DB_DIR, "attendance_queue.db")

# Errors that should be queued for retry
QUEUEABLE_ERRORS = ["connection_error", "timeout", "server_error"]


class GUILogHandler(logging.Handler):
    """Custom log handler that sends logs to GUI"""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)


def get_daily_log_dir(base_log_dir, target_date=None):
    """Get or create daily log directory"""
    if target_date is None:
        target_date = datetime.now()
    
    date_folder = target_date.strftime("%Y-%m-%d")
    daily_dir = os.path.join(base_log_dir, date_folder)
    os.makedirs(daily_dir, exist_ok=True)
    return daily_dir


class EnhancedLogger:
    """Enhanced Logger with daily folder organization and GUI support"""
    
    def __init__(self, base_dir, gui_log_queue=None):
        self.base_dir = base_dir
        self.log_dir = os.path.join(base_dir, "logs")
        self.gui_log_queue = gui_log_queue
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup main logger for tailing
        self.setup_main_logger()
        
        # Setup category-specific loggers
        self.setup_category_loggers()
    
    def setup_main_logger(self):
        """Setup the main tailable log with daily rotation and GUI support"""
        self.main_logger = logging.getLogger('biometric_main')
        self.main_logger.setLevel(logging.DEBUG)

        if self.main_logger.hasHandlers():
            self.main_logger.handlers.clear()
        
        # Main log file in daily directory
        daily_dir = get_daily_log_dir(self.log_dir)
        main_log_file = os.path.join(daily_dir, "biometric_main.log")
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
        
        # Add GUI handler if queue is provided
        if self.gui_log_queue:
            gui_handler = GUILogHandler(self.gui_log_queue)
            gui_handler.setFormatter(main_formatter)
            self.main_logger.addHandler(gui_handler)
    
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
    
    def get_dated_handler(self, category, target_date=None):
        """Get a file handler for category logs in daily directory"""
        if target_date is None:
            target_date = datetime.now()
            
        daily_dir = get_daily_log_dir(self.log_dir, target_date)
        filename = f"{category}.log"
        filepath = os.path.join(daily_dir, filename)
        
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


class DeviceConnectionManager:
    """Manages device connections to prevent duplicates"""
    
    def __init__(self, enhanced_logger=None):
        self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.device_info: Dict[str, str] = {}
        self.enhanced_logger = enhanced_logger
        self.lock = asyncio.Lock()
    
    async def register_device(self, websocket, serial_number):
        """Register a device, closing old connection if exists"""
        async with self.lock:
            client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
            
            # Check if device is already connected
            if serial_number in self.active_connections:
                old_websocket = self.active_connections[serial_number]
                
                # Close old connection gracefully
                try:
                    if not old_websocket.closed:
                        await old_websocket.close(code=1000, reason="New connection from same device")
                        if self.enhanced_logger:
                            self.enhanced_logger.log_system_event(
                                "DUPLICATE_CONNECTION_CLOSED",
                                f"Closed duplicate connection for device {serial_number}"
                            )
                except Exception as e:
                    if self.enhanced_logger:
                        self.enhanced_logger.log_error(
                            "SYSTEM", "SYSTEM", serial_number,
                            f"Error closing old connection: {e}", "CONNECTION_ERROR"
                        )
            
            # Register new connection
            self.active_connections[serial_number] = websocket
            self.device_info[serial_number] = client_addr
            
            if self.enhanced_logger:
                self.enhanced_logger.log_system_event(
                    "DEVICE_REGISTERED",
                    f"Device {serial_number} connected from {client_addr}"
                )
    
    async def unregister_device(self, websocket):
        """Unregister a device when connection closes"""
        async with self.lock:
            # Find and remove the device
            serial_to_remove = None
            for serial, ws in self.active_connections.items():
                if ws == websocket:
                    serial_to_remove = serial
                    break
            
            if serial_to_remove:
                del self.active_connections[serial_to_remove]
                if serial_to_remove in self.device_info:
                    del self.device_info[serial_to_remove]
                
                if self.enhanced_logger:
                    self.enhanced_logger.log_system_event(
                        "DEVICE_UNREGISTERED",
                        f"Device {serial_to_remove} disconnected"
                    )
    
    def get_device_id(self, websocket):
        """Get device ID from websocket"""
        for serial, ws in self.active_connections.items():
            if ws == websocket:
                return serial
        return "unknown"
    
    def get_connected_count(self):
        """Get count of connected devices"""
        return len(self.active_connections)


class SQLiteQueueManager:
    """SQLite-based queue manager (unchanged from original)"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
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
    
    async def save_to_queue(self, record_data):
        """Save failed record to queue"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute('''
                    INSERT INTO pending_checkins 
                    (employee_id, employee_name, device_id, timestamp, queued_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    record_data['enrollid'],
                    record_data['name'], 
                    record_data['device_id'],
                    record_data['timestamp'],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
                conn.close()
                return True
            except Exception:
                return False
    
    def get_queue_size(self):
        """Get current queue size"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT COUNT(*) FROM pending_checkins')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_pending_records(self):
        """Get all pending records"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM pending_checkins 
                ORDER BY queued_at ASC
            ''')
            records = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return records
        except Exception:
            return []
    
    async def remove_from_queue(self, record_id):
        """Remove successfully processed record from queue"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute('DELETE FROM pending_checkins WHERE id = ?', (record_id,))
                conn.commit()
                conn.close()
                return True
            except Exception:
                return False
    
    async def update_retry_count_and_error(self, record_id, error_message=None):
        """Update retry count and error for a record"""
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
                conn.close()
                return True
            except Exception:
                return False
    
    async def move_to_failed(self, record_id, failure_reason="Max retry attempts exceeded"):
        """Move a record from pending to failed"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute('SELECT * FROM pending_checkins WHERE id = ?', (record_id,))
                record = cursor.fetchone()
                
                if record:
                    conn.execute('''
                        INSERT INTO failed_checkins 
                        (employee_id, employee_name, device_id, timestamp, queued_at, 
                         failed_at, total_attempts, final_error, failure_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record[1], record[2], record[3], record[4], record[5],
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        record[6], record[8], failure_reason
                    ))
                    
                    conn.execute('DELETE FROM pending_checkins WHERE id = ?', (record_id,))
                    conn.commit()
                
                conn.close()
                return True
            except Exception:
                return False


class BiometricServer:
    """Enhanced BiometricServer with duplicate prevention"""
    
    def __init__(self, host='0.0.0.0', port=8190, enhanced_logger=None):
        self.host = host
        self.port = port
        self.connection_manager = DeviceConnectionManager(enhanced_logger)
        self.session = requests.Session()
        self.queue_manager = SQLiteQueueManager(DB_FILE)
        self.retry_task = None
        self.enhanced_logger = enhanced_logger
        self.server = None
        self.running = False

    async def register_device(self, websocket, data):
        serial_number = data.get('sn')
        if not serial_number:
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    "UNKNOWN", "UNKNOWN", "UNKNOWN",
                    "Device registration failed: Missing serial number",
                    "REGISTRATION_ERROR"
                )
            return {"ret": "reg", "result": False, "reason": "Missing serial number"}
        
        # Use connection manager to handle duplicate connections
        await self.connection_manager.register_device(websocket, serial_number)
        
        return {"ret": "reg", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    def send_to_erp(self, punchingcode, name, timestamp_str, device_id):
        """Send attendance to ERP server"""
        start_time = time_module.time()
        
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    punchingcode, name, device_id,
                    f"Invalid timestamp format: {timestamp_str}", "INVALID_DATA"
                )
            return False, "invalid_data", "Invalid timestamp format"

        payload = {
            "punchingcode": punchingcode,
            "employee_name": name,
            "time": timestamp.strftime("%d-%m-%Y %H:%M:%S"),
            "device_id": device_id,
        }

        try:
            response = self.session.post(f"{ERP_URL}/{ERP_API}", data=payload, timeout=5)
            response_time = time_module.time() - start_time
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    
                    if "exception" in json_response:
                        error_msg = f"ERP Exception: {json_response.get('exception')}"
                        
                        if "No Employee found" in str(json_response.get('exception', '')):
                            if self.enhanced_logger:
                                self.enhanced_logger.log_error(
                                    punchingcode, name, device_id,
                                    error_msg, "EMPLOYEE_NOT_FOUND"
                                )
                            return False, "employee_not_found", "Employee not registered in ERP"
                        else:
                            if self.enhanced_logger:
                                self.enhanced_logger.log_error(
                                    punchingcode, name, device_id,
                                    error_msg, "SERVER_ERROR"
                                )
                            return False, "server_error", error_msg
                    
                    if self.enhanced_logger:
                        self.enhanced_logger.log_success(
                            punchingcode, name, device_id, response_time
                        )
                    return True, "success", "Checkin recorded successfully"
                    
                except ValueError:
                    if "success" in response.text.lower() or len(response.text.strip()) == 0:
                        if self.enhanced_logger:
                            self.enhanced_logger.log_success(
                                punchingcode, name, device_id, response_time
                            )
                        return True, "success", "Checkin recorded successfully"
                    else:
                        if self.enhanced_logger:
                            self.enhanced_logger.log_error(
                                punchingcode, name, device_id,
                                f"Invalid JSON response: {response.text}", "SERVER_ERROR"
                            )
                        return False, "server_error", f"Invalid JSON response"
            
            elif response.status_code in [500, 502, 503, 504]:
                if self.enhanced_logger:
                    self.enhanced_logger.log_error(
                        punchingcode, name, device_id,
                        f"ERP server error: {response.status_code}", "SERVER_ERROR"
                    )
                return False, "server_error", f"ERP server error: {response.status_code}"
            
            else:
                if self.enhanced_logger:
                    self.enhanced_logger.log_error(
                        punchingcode, name, device_id,
                        f"HTTP Error {response.status_code}", "HTTP_ERROR"
                    )
                return False, "server_error", f"HTTP Error {response.status_code}"
            
        except requests.exceptions.Timeout:
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    punchingcode, name, device_id,
                    "ERP server timeout", "TIMEOUT"
                )
            return False, "timeout", "ERP server timeout"
            
        except requests.exceptions.ConnectionError:
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    punchingcode, name, device_id,
                    "Cannot reach ERP server", "CONNECTION_ERROR"
                )
            return False, "connection_error", "Cannot reach ERP server"
            
        except Exception as e:
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    punchingcode, name, device_id,
                    f"Unexpected error: {str(e)}", "SYSTEM_ERROR"
                )
            return False, "system_error", f"Unexpected error: {str(e)}"

    async def store_attendance(self, records, device_id):
        """Process attendance records"""
        if not records:
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", device_id,
                    "No records provided", "INVALID_REQUEST"
                )
            return {"ret": "sendlog", "result": False, "reason": "No records provided"}

        if self.enhanced_logger:
            self.enhanced_logger.log_system_event(
                "PROCESSING_BATCH",
                f"Processing {len(records)} records from device {device_id}"
            )

        for record in records:
            name = record.get("name")
            enroll_id = record.get("enrollid")
            timestamp = record.get("time")
            
            if not enroll_id or not timestamp or not name:
                if self.enhanced_logger:
                    self.enhanced_logger.log_error(
                        enroll_id or "UNKNOWN", name or "UNKNOWN", device_id,
                        f"Incomplete record data", "INVALID_DATA"
                    )
                continue

            record_data = {
                "name": name,
                "enrollid": enroll_id,
                "timestamp": timestamp,
                "device_id": device_id
            }

            success, error_type, error_message = self.send_to_erp(enroll_id, name, timestamp, device_id)
            
            if success:
                log_attendance_to_csv(enroll_id, name, device_id, "Success", timestamp)
            elif error_type in QUEUEABLE_ERRORS:
                await self.queue_manager.save_to_queue(record_data)
                log_attendance_to_csv(enroll_id, name, device_id, "Queued", timestamp)
            else:
                log_attendance_to_csv(enroll_id, name, device_id, "Failed", timestamp)

        return {"ret": "sendlog", "result": True, "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    async def retry_queued_records(self):
        """Background task to retry queued records"""
        if self.enhanced_logger:
            self.enhanced_logger.log_system_event("RETRY_TASK_STARTED", "Queue retry task started")
        
        while self.running:
            try:
                await asyncio.sleep(RETRY_INTERVAL)
                
                if not self.running:
                    break
                
                pending_records = self.queue_manager.get_pending_records()
                
                if not pending_records:
                    continue
                
                if self.enhanced_logger:
                    self.enhanced_logger.log_system_event(
                        "RETRY_BATCH",
                        f"Processing {len(pending_records)} queued records"
                    )
                
                for record in pending_records:
                    if not self.running:
                        break
                        
                    record_id = record['id']
                    retry_count = record.get('retry_count', 0)
                    queued_at = datetime.strptime(record['queued_at'], "%Y-%m-%d %H:%M:%S")
                    
                    if retry_count >= MAX_RETRY_ATTEMPTS:
                        await self.queue_manager.move_to_failed(
                            record_id, 
                            f"Max retry attempts exceeded ({MAX_RETRY_ATTEMPTS})"
                        )
                        log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Failed (Max Retries)", 
                            record['timestamp']
                        )
                        continue
                    
                    hours_since_queued = (datetime.now() - queued_at).total_seconds() / 3600
                    if hours_since_queued > MAX_RETRY_HOURS:
                        await self.queue_manager.move_to_failed(
                            record_id,
                            f"Time limit exceeded ({MAX_RETRY_HOURS} hours)"
                        )
                        log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Failed (Timeout)", 
                            record['timestamp']
                        )
                        continue
                    
                    success, error_type, error_message = self.send_to_erp(
                        record['employee_id'],
                        record['employee_name'],
                        record['timestamp'],
                        record['device_id']
                    )
                    
                    if success:
                        await self.queue_manager.remove_from_queue(record_id)
                        log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Success (Retry)", 
                            record['timestamp']
                        )
                    elif error_type in QUEUEABLE_ERRORS:
                        await self.queue_manager.update_retry_count_and_error(record_id, error_message)
                    else:
                        await self.queue_manager.move_to_failed(
                            record_id, 
                            f"Permanent error: {error_message}"
                        )
                        log_attendance_to_csv(
                            record['employee_id'], 
                            record['employee_name'], 
                            record['device_id'], 
                            "Failed (Permanent)", 
                            record['timestamp']
                        )
                    
            except Exception as e:
                if self.enhanced_logger:
                    self.enhanced_logger.log_error(
                        "SYSTEM", "SYSTEM", "SYSTEM",
                        f"Error in retry task: {str(e)}", "RETRY_ERROR"
                    )

    async def process_message(self, websocket, message):
        try:
            data = json.loads(message)
            device_id = self.connection_manager.get_device_id(websocket)

            if 'cmd' in data:
                cmd = data['cmd']
                if cmd == 'reg':
                    return await self.register_device(websocket, data)
                elif cmd in ('sendlog', 'getalllog'):
                    return await self.store_attendance(data.get('record', []), device_id)

            return {"ret": data.get('cmd', 'unknown'), "result": True,
                    "cloudtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        except Exception as e:
            if self.enhanced_logger:
                self.enhanced_logger.log_error(
                    "SYSTEM", "SYSTEM", self.connection_manager.get_device_id(websocket),
                    f"Message processing error: {e}", "MESSAGE_ERROR"
                )
            return {"ret": "error", "result": False, "reason": str(e)}

    async def handle_device(self, websocket, path=None):
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        if self.enhanced_logger:
            self.enhanced_logger.log_system_event("DEVICE_CONNECTED", f"Device connected: {client_addr}")
        
        try:
            async for message in websocket:
                response = await self.process_message(websocket, message)
                if response:
                    await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            if self.enhanced_logger:
                self.enhanced_logger.log_system_event("DEVICE_DISCONNECTED", f"Connection closed: {client_addr}")
        finally:
            await self.connection_manager.unregister_device(websocket)

    async def start_server(self):
        """Start the WebSocket server"""
        self.running = True
        
        if self.enhanced_logger:
            self.enhanced_logger.log_system_event("SERVER_STARTING", f"WebSocket server starting on {self.host}:{self.port}")
        
        # Start retry task
        self.retry_task = asyncio.create_task(self.retry_queued_records())
        
        # Start WebSocket server
        self.server = await websockets.serve(self.handle_device, self.host, self.port)
        
        if self.enhanced_logger:
            self.enhanced_logger.log_system_event("SERVER_STARTED", f"Server listening on {self.host}:{self.port}")
            
            # Check for existing queued records
            pending_count = self.queue_manager.get_queue_size()
            if pending_count > 0:
                self.enhanced_logger.log_system_event(
                    "STARTUP_QUEUE_CHECK", 
                    f"Found {pending_count} pending records from previous session"
                )

    async def stop_server(self):
        """Stop the WebSocket server gracefully"""
        self.running = False
        
        if self.enhanced_logger:
            self.enhanced_logger.log_system_event("SERVER_STOPPING", "Shutting down server...")
        
        # Cancel retry task
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        if self.enhanced_logger:
            self.enhanced_logger.log_system_event("SERVER_STOPPED", "Server stopped successfully")

    def get_connected_devices_count(self):
        """Get number of connected devices"""
        return self.connection_manager.get_connected_count()


def clean_csv_field(field_value):
    """Clean field value for CSV compatibility"""
    if not isinstance(field_value, str):
        field_value = str(field_value)
    
    field_value = field_value.replace('\n', ' ').replace('\r', ' ')
    field_value = ' '.join(field_value.split())
    
    return field_value.strip()


def log_attendance_to_csv(enroll_id, name, device_id, status, timestamp_str):
    """Log attendance to CSV file in daily directory"""
    try:
        punch_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        punch_time = datetime.now()

    # Get daily directory for CSV logs
    daily_dir = get_daily_log_dir(LOG_DIR, punch_time)
    filename = punch_time.strftime("%Y-%m-%d") + ".csv"
    filepath = os.path.join(daily_dir, filename)
    file_exists = os.path.isfile(filepath)

    date_str = punch_time.strftime("%Y-%m-%d")
    time_str = punch_time.strftime("%H:%M:%S")

    clean_name = clean_csv_field(str(name))
    clean_status = clean_csv_field(str(status))
    clean_device_id = clean_csv_field(str(device_id))
    clean_enroll_id = clean_csv_field(str(enroll_id))

    try:
        with open(filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            if not file_exists:
                writer.writerow(["Date", "Time", "Enroll_ID", "Name", "Device_ID", "ERP_Status"])
            writer.writerow([
                date_str, time_str, clean_enroll_id, clean_name, clean_device_id, clean_status
            ])
    except Exception:
        pass


# ============================================================================
# ENHANCED GUI APPLICATION WITH AUTO LOG CLEARING
# ============================================================================

class BiometricServerGUI:
    """Enhanced GUI Application for Biometric Server with auto log clearing"""
    
    def __init__(self):
        self.config_manager = config_manager  # Use the global config manager
        self.root = tk.Tk()
        self.root.title("Enhanced Biometric Server Control Panel")

        # Use config for window size
        gui_config = self.config_manager.config.get("gui", {})
        width = gui_config.get("window_width", 950)  
        height = gui_config.get("window_height", 650)
        self.root.geometry(f"{width}x{height}")
        
        # Set icon if available
        try:
            self.root.iconbitmap(default='biometric.ico')
        except:
            pass
        
        # Server components
        self.server = None
        self.server_thread = None
        self.server_loop = None
        self.log_queue = queue.Queue()
        self.enhanced_logger = None
        
        # Server status tracking
        self.is_running = False
        self.start_time = None
        
        # Auto log clearing
        self.last_clear_date = datetime.now().date()
        
        # Setup GUI
        self.setup_gui()
        
        # Start periodic updaters
        self.update_logs()
        self.check_daily_clear()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_gui(self):
        """Setup the enhanced GUI components"""
        
        # Apply modern styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_color = '#f0f0f0'
        self.root.configure(bg=bg_color)
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # ===== Header Section =====
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_label = ttk.Label(header_frame, text="Enhanced Biometric Server Control Panel", 
                                font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Version info
        version_label = ttk.Label(header_frame, text="v2.0 - Duplicate Prevention & Daily Organization", 
                                 font=('Segoe UI', 9), 
                                 foreground='#666666')
        version_label.grid(row=1, column=0, sticky=tk.W)
        
        # ===== Control Section =====
        control_frame = ttk.LabelFrame(main_frame, text="Server Control", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        
        # Status indicator
        self.status_label = ttk.Label(control_frame, text="Status:", font=('Segoe UI', 10))
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.status_indicator = ttk.Label(control_frame, text="● STOPPED", 
                                         font=('Segoe UI', 10, 'bold'),
                                         foreground='red')
        self.status_indicator.grid(row=0, column=1, sticky=tk.W)
        
        # Server info
        info_text = f"Server Address: {HOST}:{PORT}"
        self.info_label = ttk.Label(control_frame, text=info_text, font=('Segoe UI', 9))
        self.info_label.grid(row=0, column=2, sticky=tk.E, padx=(20, 0))
        
        # Control buttons frame
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0))
        
        # Start button
        self.start_button = ttk.Button(button_frame, text="▶ Start Server", 
                                      command=self.start_server, 
                                      width=20)
        self.start_button.grid(row=0, column=0, padx=5)
        
        # Stop button
        self.stop_button = ttk.Button(button_frame, text="■ Stop Server", 
                                     command=self.stop_server, 
                                     state=tk.DISABLED,
                                     width=20)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Clear logs button
        self.clear_button = ttk.Button(button_frame, text="🗑 Clear Logs", 
                                      command=self.clear_logs,
                                      width=15)
        self.clear_button.grid(row=0, column=2, padx=5)
        
        # Open logs folder button
        self.folder_button = ttk.Button(button_frame, text="📁 Open Logs", 
                                       command=self.open_logs_folder,
                                       width=15)
        self.folder_button.grid(row=0, column=3, padx=5)
        
        # Settings button
        self.settings_button = ttk.Button(button_frame, text="⚙ Settings", 
                                         command=self.show_settings,
                                         width=15)
        self.settings_button.grid(row=0, column=4, padx=5)
        
        # ===== Enhanced Statistics Section =====
        stats_frame = ttk.LabelFrame(main_frame, text="Server Statistics", padding="10")
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create two rows of statistics
        stats_row1 = ttk.Frame(stats_frame)
        stats_row1.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        stats_row2 = ttk.Frame(stats_frame)
        stats_row2.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Row 1 statistics
        self.devices_label = ttk.Label(stats_row1, text="Connected Devices: 0", 
                                      font=('Segoe UI', 9))
        self.devices_label.grid(row=0, column=0, padx=(0, 30))
        
        self.queue_label = ttk.Label(stats_row1, text="Queue Size: 0", 
                                    font=('Segoe UI', 9))
        self.queue_label.grid(row=0, column=1, padx=(0, 30))
        
        self.uptime_label = ttk.Label(stats_row1, text="Uptime: 00:00:00", 
                                     font=('Segoe UI', 9))
        self.uptime_label.grid(row=0, column=2, padx=(0, 30))
        
        # Row 2 statistics
        self.duplicate_prevention_label = ttk.Label(stats_row2, text="Duplicate Prevention: Active", 
                                                   font=('Segoe UI', 9),
                                                   foreground='green')
        self.duplicate_prevention_label.grid(row=0, column=0, padx=(0, 30))
        
        self.daily_org_label = ttk.Label(stats_row2, text="Daily Organization: Enabled", 
                                        font=('Segoe UI', 9),
                                        foreground='blue')
        self.daily_org_label.grid(row=0, column=1, padx=(0, 30))
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.current_date_label = ttk.Label(stats_row2, text=f"Current Date: {current_date}", 
                                           font=('Segoe UI', 9))
        self.current_date_label.grid(row=0, column=2)
        
        # ===== Enhanced Log Section =====
        log_frame = ttk.LabelFrame(main_frame, text="Live Server Logs", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text area with scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)
        
        # Scrolled text widget for logs
        self.log_text = scrolledtext.ScrolledText(log_container, 
                                                  wrap=tk.WORD,
                                                  width=90, 
                                                  height=25,
                                                  font=('Consolas', 9),
                                                  bg='#1e1e1e',
                                                  fg='#d4d4d4')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for colored logs
        self.log_text.tag_config('INFO', foreground='#3794ff')
        self.log_text.tag_config('SUCCESS', foreground='#4ec950')
        self.log_text.tag_config('WARNING', foreground='#ffcc00')
        self.log_text.tag_config('ERROR', foreground='#f48771')
        self.log_text.tag_config('SYSTEM', foreground='#b267e6')
        self.log_text.tag_config('DUPLICATE', foreground='#ff6b35')
        
        # Enhanced log controls
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_check = ttk.Checkbutton(log_controls, 
                                                text="Auto-scroll", 
                                                variable=self.auto_scroll_var)
        self.auto_scroll_check.grid(row=0, column=0, sticky=tk.W)
        
        # Auto-clear info
        self.auto_clear_label = ttk.Label(log_controls, 
                                         text="Auto-clear: Daily at midnight", 
                                         font=('Segoe UI', 8),
                                         foreground='#666666')
        self.auto_clear_label.grid(row=0, column=1, padx=(20, 0))
        
        # Log count
        self.log_count_label = ttk.Label(log_controls, text="Lines: 0", 
                                        font=('Segoe UI', 8),
                                        foreground='#666666')
        self.log_count_label.grid(row=0, column=2, sticky=tk.E)
        log_controls.columnconfigure(2, weight=1)
        
        # ===== Status Bar =====
        status_bar = ttk.Frame(main_frame)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_text = ttk.Label(status_bar, text="Ready - Enhanced Version with Duplicate Prevention", 
                                    font=('Segoe UI', 9), 
                                    relief=tk.SUNKEN)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        status_bar.columnconfigure(0, weight=1)
    
    def update_logs(self):
        """Update log display from queue"""
        try:
            new_logs = 0
            while not self.log_queue.empty():
                log_msg = self.log_queue.get_nowait()
                self.append_log(log_msg)
                new_logs += 1
            
            if new_logs > 0:
                self.update_log_count()
                
        except queue.Empty:
            pass
        finally:
            # Schedule next update
            self.root.after(100, self.update_logs)
    
    def append_log(self, message):
        """Append a log message to the text widget"""
        self.log_text.config(state=tk.NORMAL)
        
        # Determine log level and tag
        tag = 'INFO'
        if 'ERROR' in message or 'Failed' in message:
            tag = 'ERROR'
        elif 'SUCCESS' in message or 'Success' in message:
            tag = 'SUCCESS'
        elif 'WARNING' in message or 'QUEUE' in message:
            tag = 'WARNING'
        elif 'SYSTEM' in message:
            tag = 'SYSTEM'
        elif 'DUPLICATE' in message or 'duplicate' in message:
            tag = 'DUPLICATE'
        
        # Insert message with timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, full_message, tag)
        
        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.log_text.config(state=tk.DISABLED)
    
    def update_log_count(self):
        """Update the log line count"""
        content = self.log_text.get(1.0, tk.END)
        line_count = len(content.splitlines()) - 1  # Subtract 1 for the empty line at end
        self.log_count_label.config(text=f"Lines: {line_count}")
    
    def clear_logs(self):
        """Clear the log display"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_log_count()
        self.append_log("GUI logs cleared manually")
    
    def check_daily_clear(self):
        """Check if it's time to auto-clear logs (daily at midnight)"""
        try:
            current_date = datetime.now().date()
            
            # Check if date has changed
            if current_date != self.last_clear_date:
                self.last_clear_date = current_date
                
                # Clear logs at start of new day
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)
                self.log_text.config(state=tk.DISABLED)
                self.update_log_count()
                
                # Add notification
                self.append_log(f"=== NEW DAY: {current_date.strftime('%Y-%m-%d')} - Logs Auto-Cleared ===")
                
                # Update current date display
                self.current_date_label.config(text=f"Current Date: {current_date.strftime('%Y-%m-%d')}")
                
        except Exception as e:
            # Silently handle any errors in auto-clear
            pass
        finally:
            # Check again in 1 minute
            self.root.after(60000, self.check_daily_clear)  # 60 seconds = 1 minute
    
    def open_logs_folder(self):
        """Open the logs folder in Windows Explorer"""
        try:
            os.startfile(LOG_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open logs folder: {e}")
    
    def show_settings(self):
        """Show configuration dialog"""
        if self.is_running:
            messagebox.showwarning(
                "Server Running",
                "Please stop the server before changing settings."
            )
            return

        settings_dialog = SettingsDialog(self.root, self.config_manager)
        settings_dialog.show()

    def reload_configuration(self):
        """Reload configuration after changes"""
        global HOST, PORT, BASE_DIR, ERP_URL, ERP_API, RETRY_INTERVAL, MAX_RETRY_ATTEMPTS, MAX_RETRY_HOURS
        
        # Reload config from file
        self.config_manager.config = self.config_manager.load_config()
        
        # Update global variables
        server_config = self.config_manager.get_server_config()
        erp_config = self.config_manager.get_erp_config()
        retry_config = self.config_manager.get_retry_config()
        
        BASE_DIR = server_config.get('base_dir', r"E:\BiometricServer")
        HOST = server_config.get('host', "0.0.0.0")
        PORT = server_config.get('port', 8190)
        
        ERP_URL = erp_config.get('url', "http://192.168.0.61:8000")
        ERP_API = erp_config.get('api_endpoint', "api/method/sil.test.biometric_to_erp.add_checkin")
        
        RETRY_INTERVAL = retry_config.get('interval_seconds', 180)
        MAX_RETRY_ATTEMPTS = retry_config.get('max_attempts', 10)
        MAX_RETRY_HOURS = retry_config.get('max_hours', 24)
        
        # Update GUI display
        info_text = f"Server Address: {HOST}:{PORT}"
        self.info_label.config(text=info_text)
    
    def start_server(self):
        """Start the enhanced biometric server in a background thread"""
        if self.is_running:
            return
        
        try:
            # Reload configuration before starting
            self.reload_configuration()        
            # Initialize logger with GUI queue
            self.enhanced_logger = EnhancedLogger(BASE_DIR, self.log_queue)
            
            # Create and start server thread
            self.server_thread = threading.Thread(target=self.run_server_thread, daemon=True)
            self.server_thread.start()
            
            # Update UI
            self.is_running = True
            self.start_time = datetime.now()
            self.status_indicator.config(text="● RUNNING", foreground='green')
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_text.config(text="Enhanced server running with duplicate prevention...")
            
            # Start status updater
            self.update_status()
            
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to start server: {e}")
            self.append_log(f"ERROR: Failed to start server: {e}")
    
    def run_server_thread(self):
        """Run the server in a separate thread with its own event loop"""
        try:
            # Create new event loop for this thread
            self.server_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.server_loop)
            
            # Create server instance
            self.server = BiometricServer(HOST, PORT, self.enhanced_logger)
            
            # Run server
            self.server_loop.run_until_complete(self.run_server())
            
        except Exception as e:
            self.log_queue.put(f"ERROR: Server thread error: {e}")
        finally:
            # Clean up
            if self.server_loop:
                self.server_loop.close()
    
    async def run_server(self):
        """Run the server asynchronously"""
        try:
            await self.server.start_server()
            
            # Keep running until stopped
            while self.is_running:
                await asyncio.sleep(1)
            
            # Stop server
            await self.server.stop_server()
            
        except Exception as e:
            self.log_queue.put(f"ERROR: Server error: {e}")
    
    def stop_server(self):
        """Stop the biometric server"""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            # Stop the server gracefully
            if self.server_loop and self.server:
                future = asyncio.run_coroutine_threadsafe(
                    self.server.stop_server(), 
                    self.server_loop
                )
                future.result(timeout=5)  # Wait up to 5 seconds
            
            # Wait for thread to finish
            if self.server_thread:
                self.server_thread.join(timeout=5)
            
            # Update UI
            self.status_indicator.config(text="● STOPPED", foreground='red')
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_text.config(text="Server stopped")
            self.start_time = None
            
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to stop server: {e}")
            self.append_log(f"ERROR: Failed to stop server: {e}")
    
    def update_status(self):
        """Update server status information"""
        if self.is_running and self.server:
            try:
                # Update connected devices count
                device_count = self.server.get_connected_devices_count()
                self.devices_label.config(text=f"Connected Devices: {device_count}")
                
                # Update queue size
                queue_size = self.server.queue_manager.get_queue_size()
                self.queue_label.config(text=f"Queue Size: {queue_size}")
                
                # Update uptime
                if self.start_time:
                    uptime = datetime.now() - self.start_time
                    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
                    self.uptime_label.config(text=f"Uptime: {uptime_str}")
                
                # Schedule next update
                self.root.after(2000, self.update_status)
                
            except Exception:
                pass
    
    def on_closing(self):
        """Handle window closing event"""
        if self.is_running:
            result = messagebox.askyesno("Confirm Exit", 
                                        "Server is still running. Do you want to stop it and exit?")
            if result:
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Run the GUI application"""
        # Initial log message
        self.append_log("=== Enhanced Biometric Server Control Panel Started ===")
        self.append_log("Features: Duplicate Prevention | Daily Log Organization | Auto Log Clearing")
        self.root.mainloop()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the enhanced application"""
    try:
        app = BiometricServerGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Application Error", f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()