import frappe
from frappe.utils import get_datetime, getdate, time_diff_in_seconds
from frappe import _
from frappe.model.naming import make_autoname
from datetime import datetime, time, timedelta
import time as time_module

# Database connection retry configuration
MAX_DB_RETRY_ATTEMPTS = 3
DB_RETRY_DELAY = 1  # seconds


def retry_on_db_error(max_attempts=MAX_DB_RETRY_ATTEMPTS):
    """Decorator for database operations with retry logic"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a database connection error
                    if any(keyword in error_msg for keyword in [
                        'connection', 'timeout', 'lost connection', 'gone away',
                        'can\'t connect', 'access denied', 'database'
                    ]):
                        frappe.log_error(
                            f"Database error (attempt {attempt + 1}/{max_attempts}): {str(e)}", 
                            "Database Retry"
                        )
                        
                        if attempt < max_attempts - 1:  # Not the last attempt
                            time_module.sleep(DB_RETRY_DELAY * (attempt + 1))  # Exponential backoff
                            
                            # Try to reconnect to database
                            try:
                                frappe.db.connect()
                            except:
                                pass  # Will try again in next iteration
                            continue
                    else:
                        # Non-connection error, don't retry
                        raise e
            
            # All attempts failed
            raise last_error
        return wrapper
    return decorator


def safe_db_operation(operation_func, rollback_on_error=True):
    """
    Wrapper for database operations with proper transaction handling
    """
    try:
        result = operation_func()
        frappe.db.commit()
        return result
    except Exception as e:
        if rollback_on_error:
            frappe.db.rollback()
        frappe.log_error(f"Database operation failed: {str(e)}", "Database Error")
        raise


def is_recent_checkin(employee_id, checkin_time, table_name, field="time"):
    """
    Check if employee has a recent checkin (< 2 minutes) in the given table.
    Enhanced with better error handling and database connection checks.
    """
    try:
        @retry_on_db_error()
        def _check_recent():
            # Ensure database connection is active
            if not frappe.db._conn:
                frappe.db.connect()
                
            last_checkin_time = frappe.db.get_value(
                table_name,
                {"employee": employee_id},
                field,
                order_by=f"{field} desc"
            )
            
            if last_checkin_time:
                try:
                    diff_seconds = time_diff_in_seconds(checkin_time, last_checkin_time)
                    if diff_seconds < 120:  # less than 2 minutes
                        return diff_seconds
                except Exception as time_error:
                    frappe.log_error(f"Time calculation error: {str(time_error)}", "Time Calculation")
                    # If time calculation fails, allow the checkin to proceed
                    return None
            return None
        
        return _check_recent()
        
    except Exception as e:
        frappe.log_error(f"Error checking recent checkin: {str(e)}", "Recent Checkin Check")
        # If check fails, allow checkin to proceed (fail-safe approach)
        return None


@frappe.whitelist(allow_guest=True)  # Note: You mentioned to fix this later
def add_checkin(punchingcode, employee_name, time, device_id):
    """
    Main API function with enhanced error handling and transaction management
    """
    try:
        # Input validation with detailed error messages
        if not punchingcode or str(punchingcode).strip() == '':
            frappe.throw(_("Biometric ID (punchingcode) is required and cannot be empty"))
        if not time or str(time).strip() == '':
            frappe.throw(_("Time is required and cannot be empty"))
        if not device_id or str(device_id).strip() == '':
            frappe.throw(_("Device ID is required and cannot be empty"))

        # Step 1: Get employee with database retry
        @retry_on_db_error()
        def _get_employee():
            return frappe.db.get_value(
                "Employee",
                {"attendance_device_id": punchingcode},
                ["name", "employee_name"]
            )
        
        employee = _get_employee()
        if not employee:
            frappe.throw(_("No Employee found for Biometric ID: {0}").format(punchingcode))

        employee_id, full_name = employee
        
        # Validate and parse time with better error handling
        try:
            checkin_time = get_datetime(time)
            checkin_date = getdate(checkin_time)
        except Exception as e:
            frappe.log_error(f"Time parsing error for '{time}': {str(e)}", "Time Parsing Error")
            frappe.throw(_("Invalid time format '{0}': {1}").format(time, str(e)))

        # Step 2: Get device mapping with error handling
        device_mapping = get_device_mapping(device_id)
        
        if not device_mapping:
            # Default to Employee Checkin if no mapping found
            return safe_db_operation(
                lambda: handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, None)
            )
        
        target_table = device_mapping.get('database_table')
        location = device_mapping.get('location')

        if not target_table:
            frappe.throw(_("Database table not configured for device: {0}").format(device_id))

        # Step 3: Clean target table name and route to appropriate handler
        clean_target_table = target_table.strip('`').strip()
        
        # Route to appropriate handler with transaction safety
        if clean_target_table == 'tabEmployee Checkin':
            return safe_db_operation(
                lambda: handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location)
            )
        elif clean_target_table == 'tabOvertime Checkin':
            return safe_db_operation(
                lambda: handle_overtime_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location)
            )
        elif clean_target_table == 'tabSecurity Gate Checkin':
            return safe_db_operation(
                lambda: handle_security_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location)
            )
        else:
            frappe.throw(_("Invalid database table configuration: {0}").format(target_table))

    except frappe.ValidationError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        frappe.log_error(f"Unexpected error in add_checkin: {str(e)}", "Biometric API Critical Error")
        frappe.throw(_("Critical error processing checkin. Please contact administrator."))


def get_device_mapping(device_id):
    """
    Get device mapping with enhanced error handling and validation
    """
    try:
        @retry_on_db_error()
        def _get_mapping():
            # Check if doctype exists
            if not frappe.db.exists("DocType", "Biometric Device Mapping"):
                return None
                
            # Check if single doctype has been created
            if not frappe.db.exists("Biometric Device Mapping", "Biometric Device Mapping"):
                return None
                
            device_doc = frappe.get_single("Biometric Device Mapping")
            
            # Validate child table exists and has data
            if not hasattr(device_doc, 'table_sgvh') or not device_doc.table_sgvh:
                return None
            
            # Search for matching serial number
            for row in device_doc.table_sgvh:
                if hasattr(row, 'serial_number') and row.serial_number == device_id:
                    return {
                        'database_table': getattr(row, 'database_table', None),
                        'location': getattr(row, 'location', None)
                    }
            return None
        
        return _get_mapping()
        
    except Exception as e:
        frappe.log_error(f"Error fetching device mapping for device {device_id}: {str(e)}", "Device Mapping Error")
        return None


def handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Handle Employee Checkin with enhanced error handling and transaction safety
    """
    try:
        # Check for recent checkin
        recent = is_recent_checkin(employee_id, checkin_time, "Employee Checkin")
        if recent is not None and recent >= 0:  # Only block if we got a valid recent time
            return {
                "status": "ignored",
                "reason": f"Checkin blocked: Last entry was only {int(recent)} seconds ago",
                "employee": employee_id,
                "time": str(checkin_time)
            }

        # Determine log_type by checking last entry for the day
        @retry_on_db_error()
        def _get_last_log_type():
            return frappe.db.sql(
                """
                SELECT log_type FROM `tabEmployee Checkin`
                WHERE employee = %s AND DATE(time) = %s
                ORDER BY time DESC LIMIT 1
                """,
                (employee_id, checkin_date),
                as_dict=False
            )

        log_type = "IN"
        try:
            last_log_type = _get_last_log_type()
            if last_log_type and last_log_type[0] and last_log_type[0][0]:
                log_type = "OUT" if last_log_type[0][0] == "IN" else "IN"
        except Exception as e:
            frappe.log_error(f"Error determining log type, defaulting to IN: {str(e)}", "Log Type Error")

        # Generate name using naming series
        name = make_autoname('CHKIN-.#####')

        # Insert new checkin record with proper error handling
        @retry_on_db_error()
        def _insert_checkin():
            frappe.db.sql("""
                INSERT INTO `tabEmployee Checkin`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 employee, employee_name, time, device_id, log_type, custom_device_location)
                VALUES (%s, NOW(), NOW(), %s, %s, 0, 0,
                 %s, %s, %s, %s, %s, %s)
            """, (
                name, frappe.session.user or 'Administrator', frappe.session.user or 'Administrator',
                employee_id, full_name, checkin_time, device_id, log_type, location
            ))

        _insert_checkin()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Employee Checkin"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in handle_employee_checkin: {str(e)}", "Employee Checkin Error")
        raise


def handle_overtime_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Handle Overtime Checkin with enhanced error handling
    """
    try:
        recent = is_recent_checkin(employee_id, checkin_time, "Overtime Sessions", field="time")
        if recent is not None and recent >= 0:
            return {
                "status": "ignored",
                "reason": f"Overtime checkin blocked: Last entry was only {int(recent)} seconds ago",
                "employee": employee_id,
                "time": str(checkin_time)
            }

        # Check if record exists for today
        @retry_on_db_error()
        def _get_existing_record():
            return frappe.db.get_value(
                "Overtime Checkin",
                {"employee": employee_id, "date": checkin_date},
                ["name", "total_overtime"]
            )

        existing_record = _get_existing_record()

        if existing_record and existing_record[0]:
            # Update existing record
            return update_overtime_session(existing_record[0], employee_id, checkin_time, checkin_date)
        else:
            # Create new record for today
            return create_new_overtime_record(employee_id, full_name, checkin_time, checkin_date, device_id, location)
            
    except Exception as e:
        frappe.log_error(f"Error in handle_overtime_checkin: {str(e)}", "Overtime Checkin Error")
        raise


def handle_security_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Handle Security Gate Checkin with enhanced error handling
    """
    try:
        recent = is_recent_checkin(employee_id, checkin_time, "Security Gate Sessions", field="time")
        if recent is not None and recent >= 0:
            return {
                "status": "ignored",
                "reason": f"Security checkin blocked: Last entry was only {int(recent)} seconds ago",
                "employee": employee_id,
                "time": str(checkin_time)
            }

        # Check if record exists for today
        @retry_on_db_error()
        def _get_existing_record():
            return frappe.db.get_value(
                "Security Gate Checkin",
                {"employee": employee_id, "date": checkin_date},
                ["name", "total_session_time"]
            )

        existing_record = _get_existing_record()

        if existing_record and existing_record[0]:
            # Update existing record
            return update_security_session(existing_record[0], employee_id, checkin_time, checkin_date)
        else:
            # Create new record for today
            return create_new_security_record(employee_id, full_name, checkin_time, checkin_date, device_id, location)
            
    except Exception as e:
        frappe.log_error(f"Error in handle_security_checkin: {str(e)}", "Security Checkin Error")
        raise


def create_new_overtime_record(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Create new Overtime Checkin record with enhanced error handling
    """
    try:
        name = make_autoname('OT-.#####')
        log_type = "IN"  # First entry is always IN
        
        # Insert main record
        @retry_on_db_error()
        def _insert_main_record():
            frappe.db.sql("""
                INSERT INTO `tabOvertime Checkin`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 employee, employee_name, date, total_overtime, device_id)
                VALUES (%s, NOW(), NOW(), %s, %s, 0, 0,
                 %s, %s, %s, %s, %s)
            """, (
                name, frappe.session.user or 'Administrator', frappe.session.user or 'Administrator',
                employee_id, full_name, checkin_date, 0, device_id
            ))

        _insert_main_record()

        # Insert child record for the session
        child_name = make_autoname('OTS-.#####')
        
        @retry_on_db_error()
        def _insert_child_record():
            frappe.db.sql("""
                INSERT INTO `tabOvertime Sessions`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 parent, parentfield, parenttype, time, log_type)
                VALUES (%s, NOW(), NOW(), %s, %s, 0, 1,
                 %s, 'overtime_sessions', 'Overtime Checkin', %s, %s)
            """, (
                child_name, frappe.session.user or 'Administrator', frappe.session.user or 'Administrator',
                name, checkin_time.time(), log_type
            ))

        _insert_child_record()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Overtime Checkin"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating overtime record: {str(e)}", "Overtime Creation Error")
        raise


def create_new_security_record(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Create new Security Gate Checkin record with enhanced error handling
    """
    try:
        name = make_autoname('SEC-.#####')
        log_type = "IN"  # First entry is always IN
        
        # Insert main record
        @retry_on_db_error()
        def _insert_main_record():
            frappe.db.sql("""
                INSERT INTO `tabSecurity Gate Checkin`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 employee, employee_name, date, total_session_time, device_id)
                VALUES (%s, NOW(), NOW(), %s, %s, 0, 0,
                 %s, %s, %s, %s, %s)
            """, (
                name, frappe.session.user or 'Administrator', frappe.session.user or 'Administrator',
                employee_id, full_name, checkin_date, 0, device_id
            ))

        _insert_main_record()

        # Insert child record for the session
        child_name = make_autoname('SECS-.#####')
        
        @retry_on_db_error()
        def _insert_child_record():
            frappe.db.sql("""
                INSERT INTO `tabSecurity Gate Sessions`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 parent, parentfield, parenttype, time, log_type)
                VALUES (%s, NOW(), NOW(), %s, %s, 0, 1,
                 %s, 'security_gate_sessions', 'Security Gate Checkin', %s, %s)
            """, (
                child_name, frappe.session.user or 'Administrator', frappe.session.user or 'Administrator',
                name, checkin_time.time(), log_type
            ))

        _insert_child_record()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Security Gate Checkin"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating security record: {str(e)}", "Security Creation Error")
        raise


def update_overtime_session(record_name, employee_id, checkin_time, checkin_date):
    """
    Add new session to existing overtime record with enhanced error handling
    """
    try:
        # Get last log type for this record
        @retry_on_db_error()
        def _get_last_session():
            return frappe.db.sql("""
                SELECT log_type, time FROM `tabOvertime Sessions`
                WHERE parent = %s
                ORDER BY idx DESC LIMIT 1
            """, (record_name,), as_dict=True)

        last_session = _get_last_session()
        log_type = "OUT" if (last_session and last_session[0]['log_type'] == "IN") else "IN"
        
        # Get next idx with proper null handling
        @retry_on_db_error()
        def _get_next_idx():
            result = frappe.db.sql("""
                SELECT COALESCE(MAX(idx), 0) + 1 as next_idx
                FROM `tabOvertime Sessions`
                WHERE parent = %s
            """, (record_name,), as_dict=True)
            return result[0]['next_idx'] if result else 1

        max_idx = _get_next_idx()

        # Insert new session
        child_name = make_autoname('OTS-.#####')
        
        @retry_on_db_error()
        def _insert_session():
            frappe.db.sql("""
                INSERT INTO `tabOvertime Sessions`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 parent, parentfield, parenttype, time, log_type)
                VALUES (%s, NOW(), NOW(), %s, %s, 0, %s,
                 %s, 'overtime_sessions', 'Overtime Checkin', %s, %s)
            """, (
                child_name, frappe.session.user or 'Administrator', frappe.session.user or 'Administrator', max_idx,
                record_name, checkin_time.time(), log_type
            ))

        _insert_session()

        # Calculate and update total overtime if this is an OUT
        if log_type == "OUT" and last_session and last_session[0].get('time'):
            calculate_and_update_overtime_total(record_name, last_session[0]['time'], checkin_time.time())

        return {
            "status": "success",
            "name": record_name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Overtime Checkin"
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating overtime session: {str(e)}", "Overtime Update Error")
        raise


def update_security_session(record_name, employee_id, checkin_time, checkin_date):
    """
    Add new session to existing security record with enhanced error handling
    """
    try:
        # Get last log type for this record
        @retry_on_db_error()
        def _get_last_session():
            return frappe.db.sql("""
                SELECT log_type, time FROM `tabSecurity Gate Sessions`
                WHERE parent = %s
                ORDER BY idx DESC LIMIT 1
            """, (record_name,), as_dict=True)

        last_session = _get_last_session()
        log_type = "OUT" if (last_session and last_session[0]['log_type'] == "IN") else "IN"
        
        # Get next idx with proper null handling
        @retry_on_db_error()
        def _get_next_idx():
            result = frappe.db.sql("""
                SELECT COALESCE(MAX(idx), 0) + 1 as next_idx
                FROM `tabSecurity Gate Sessions`
                WHERE parent = %s
            """, (record_name,), as_dict=True)
            return result[0]['next_idx'] if result else 1

        max_idx = _get_next_idx()

        # Insert new session
        child_name = make_autoname('SECS-.#####')
        
        @retry_on_db_error()
        def _insert_session():
            frappe.db.sql("""
                INSERT INTO `tabSecurity Gate Sessions`
                (name, creation, modified, modified_by, owner, docstatus, idx,
                 parent, parentfield, parenttype, time, log_type)
                VALUES (%s, NOW(), NOW(), %s, %s, 0, %s,
                 %s, 'security_gate_sessions', 'Security Gate Checkin', %s, %s)
            """, (
                child_name, frappe.session.user or 'Administrator', frappe.session.user or 'Administrator', max_idx,
                record_name, checkin_time.time(), log_type
            ))

        _insert_session()

        # Calculate and update total session time if this is an OUT
        if log_type == "OUT" and last_session and last_session[0].get('time'):
            calculate_and_update_security_total(record_name, last_session[0]['time'], checkin_time.time())

        return {
            "status": "success",
            "name": record_name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Security Gate Checkin"
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating security session: {str(e)}", "Security Update Error")
        raise


def calculate_and_update_overtime_total(record_name, in_time, out_time):
    """
    Calculate session duration and update total overtime with enhanced error handling
    """
    try:
        # Validate time objects
        if not isinstance(in_time, time) or not isinstance(out_time, time):
            frappe.log_error(f"Invalid time objects in overtime calculation: {type(in_time)}, {type(out_time)}", "Overtime Time Error")
            return
            
        # Convert time objects to datetime for calculation
        today = datetime.now().date()
        in_datetime = datetime.combine(today, in_time)
        out_datetime = datetime.combine(today, out_time)
        
        # Handle case where out_time is next day
        if out_time < in_time:
            out_datetime = datetime.combine(today + timedelta(days=1), out_time)
        
        session_seconds = time_diff_in_seconds(out_datetime, in_datetime)
        
        # Validate positive duration
        if session_seconds < 0:
            frappe.log_error(f"Negative session duration calculated: {session_seconds}", "Overtime Duration Error")
            return
        
        # Get current total and add session time
        @retry_on_db_error()
        def _update_total():
            current_total = frappe.db.get_value("Overtime Checkin", record_name, "total_overtime") or 0
            new_total = current_total + session_seconds
            
            frappe.db.sql("""
                UPDATE `tabOvertime Checkin`
                SET total_overtime = %s, modified = NOW()
                WHERE name = %s
            """, (new_total, record_name))

        _update_total()
        
    except Exception as e:
        frappe.log_error(f"Error calculating overtime: {str(e)}", "Overtime Calculation Error")


def calculate_and_update_security_total(record_name, in_time, out_time):
    """
    Calculate session duration and update total security session time with enhanced error handling
    """
    try:
        # Validate time objects
        if not isinstance(in_time, time) or not isinstance(out_time, time):
            frappe.log_error(f"Invalid time objects in security calculation: {type(in_time)}, {type(out_time)}", "Security Time Error")
            return
            
        # Convert time objects to datetime for calculation
        today = datetime.now().date()
        in_datetime = datetime.combine(today, in_time)
        out_datetime = datetime.combine(today, out_time)
        
        # Handle case where out_time is next day
        if out_time < in_time:
            out_datetime = datetime.combine(today + timedelta(days=1), out_time)
        
        session_seconds = time_diff_in_seconds(out_datetime, in_datetime)
        
        # Validate positive duration
        if session_seconds < 0:
            frappe.log_error(f"Negative session duration calculated: {session_seconds}", "Security Duration Error")
            return
        
        # Get current total and add session time
        @retry_on_db_error()
        def _update_total():
            current_total = frappe.db.get_value("Security Gate Checkin", record_name, "total_session_time") or 0
            new_total = current_total + session_seconds
            
            frappe.db.sql("""
                UPDATE `tabSecurity Gate Checkin`
                SET total_session_time = %s, modified = NOW()
                WHERE name = %s
            """, (new_total, record_name))

        _update_total()
        
    except Exception as e:
        frappe.log_error(f"Error calculating security time: {str(e)}", "Security Calculation Error")
