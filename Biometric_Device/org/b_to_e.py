import frappe
from frappe.utils import get_datetime, getdate, time_diff_in_seconds
from frappe import _
from frappe.model.naming import make_autoname
from datetime import datetime, time, timedelta

def is_recent_checkin(employee_id, checkin_time, table_name, field="time"):
    """
    Check if employee has a recent checkin (< 2 minutes) in the given table.
    """
    last_checkin_time = frappe.db.get_value(
        table_name,
        {"employee": employee_id},
        field,
        order_by=f"{field} desc"
    )
    if last_checkin_time:
        diff_seconds = time_diff_in_seconds(checkin_time, last_checkin_time)
        if diff_seconds < 120:  # less than 2 minutes
            return diff_seconds
    return None


@frappe.whitelist(allow_guest=True)
def add_checkin(punchingcode, employee_name, time, device_id):
    """
    Main API function that routes attendance logs to appropriate tables
    based on device mapping configuration
    """
    try:
        # Validate required parameters
        if not punchingcode:
            frappe.throw(_("Biometric ID (punchingcode) is required"))
        if not time:
            frappe.throw(_("Time is required"))
        if not device_id:
            frappe.throw(_("Device ID is required"))

        # Step 1: Get employee by biometric ID
        employee = frappe.db.get_value(
            "Employee",
            {"attendance_device_id": punchingcode},
            ["name", "employee_name"]
        )

        if not employee:
            frappe.throw(_("No Employee found for Biometric ID: {0}").format(punchingcode))

        employee_id, full_name = employee
        
        # Validate and parse time
        try:
            checkin_time = get_datetime(time)
            checkin_date = getdate(checkin_time)
        except Exception as e:
            frappe.throw(_("Invalid time format: {0}").format(str(e)))

        # Step 2: Get device mapping to determine target table
        device_mapping = get_device_mapping(device_id)
        
        if not device_mapping:
            # Default to Employee Checkin if no mapping found
            return handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, None)
        
        target_table = device_mapping.get('database_table')
        location = device_mapping.get('location')

        if not target_table:
            frappe.throw(_("Database table not configured for device: {0}").format(device_id))

        # Step 3: Clean target table name (remove backticks) and route to appropriate handler
        clean_target_table = target_table.strip('`').strip()
        
        if clean_target_table == 'tabEmployee Checkin':
            return handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location)
        elif clean_target_table == 'tabOvertime Checkin':
            return handle_overtime_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location)
        elif clean_target_table == 'tabSecurity Gate Checkin':
            return handle_security_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location)
        else:
            frappe.throw(_("Invalid database table configuration: {0}. Cleaned value: {1}").format(target_table, clean_target_table))

    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error in add_checkin: {str(e)}", "Biometric API Error")
        frappe.throw(_("Error processing checkin: {0}").format(str(e)))


def get_device_mapping(device_id):
    """
    Get device mapping configuration from Biometric Device Mapping doctype
    """
    try:
        if not frappe.db.exists("DocType", "Biometric Device Mapping"):
            frappe.log_error("Biometric Device Mapping doctype not found", "Device Mapping Error")
            return None
            
        device_doc = frappe.get_single("Biometric Device Mapping")
        
        # Validate child table exists
        if not hasattr(device_doc, 'table_sgvh') or not device_doc.table_sgvh:
            return None
        
        # Search in the child table for matching serial number
        for row in device_doc.table_sgvh:
            if row.serial_number == device_id:
                return {
                    'database_table': row.database_table,
                    'location': getattr(row, 'location', None)
                }
        return None
        
    except Exception as e:
        frappe.log_error(f"Error fetching device mapping: {str(e)}", "Device Mapping Error")
        return None


def handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Handle traditional Employee Checkin - creates new row for each punch
    """
    try:
        recent = is_recent_checkin(employee_id, checkin_time, "Employee Checkin")
        if recent:
            return {
                "status": "ignored",
                "reason": f"Checkin blocked: Last entry was only {int(recent)} seconds ago",
                "employee": employee_id,
                "time": str(checkin_time)
            }

        # Determine log_type by checking last entry for the day
        log_type = "IN"
        last_log_type = frappe.db.sql(
            """
            SELECT log_type FROM `tabEmployee Checkin`
            WHERE employee = %s AND DATE(time) = %s
            ORDER BY time DESC LIMIT 1
            """,
            (employee_id, checkin_date),
            as_dict=False
        )

        if last_log_type and last_log_type[0] and last_log_type[0][0]:
            log_type = "OUT" if last_log_type[0][0] == "IN" else "IN"

        # Generate name using naming series
        name = make_autoname('CHKIN-.#####')

        # Insert new checkin record with proper error handling
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

        frappe.db.commit()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Employee Checkin"
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in handle_employee_checkin: {str(e)}", "Employee Checkin Error")
        raise


def handle_overtime_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Handle Overtime Checkin - one row per day with child table for sessions
    """
    try:
        recent = is_recent_checkin(employee_id, checkin_time, "Overtime Sessions", field="time")
        if recent:
            return {
                "status": "ignored",
                "reason": f"Overtime checkin blocked: Last entry was only {int(recent)} seconds ago",
                "employee": employee_id,
                "time": str(checkin_time)
            }

        # Check if record exists for today
        existing_record = frappe.db.get_value(
            "Overtime Checkin",
            {"employee": employee_id, "date": checkin_date},
            ["name", "total_overtime"]
        )

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
    Handle Security Gate Checkin - one row per day with child table for sessions
    """
    try:
        recent = is_recent_checkin(employee_id, checkin_time, "Security Gate Sessions", field="time")
        if recent:
            return {
                "status": "ignored",
                "reason": f"Security checkin blocked: Last entry was only {int(recent)} seconds ago",
                "employee": employee_id,
                "time": str(checkin_time)
            }

        # Check if record exists for today
        existing_record = frappe.db.get_value(
            "Security Gate Checkin",
            {"employee": employee_id, "date": checkin_date},
            ["name", "total_session_time"]
        )

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
    Create new Overtime Checkin record for the day
    """
    try:
        name = make_autoname('OT-.#####')
        log_type = "IN"  # First entry is always IN
        
        # Insert main record
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

        # Insert child record for the session
        child_name = make_autoname('OTS-.#####')
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

        frappe.db.commit()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Overtime Checkin"
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error creating overtime record: {str(e)}", "Overtime Creation Error")
        raise


def create_new_security_record(employee_id, full_name, checkin_time, checkin_date, device_id, location):
    """
    Create new Security Gate Checkin record for the day
    """
    try:
        name = make_autoname('SEC-.#####')
        log_type = "IN"  # First entry is always IN
        
        # Insert main record
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

        # Insert child record for the session
        child_name = make_autoname('SECS-.#####')
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

        frappe.db.commit()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Security Gate Checkin"
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error creating security record: {str(e)}", "Security Creation Error")
        raise


def update_overtime_session(record_name, employee_id, checkin_time, checkin_date):
    """
    Add new session to existing overtime record
    """
    try:
        # Get last log type for this record
        last_session = frappe.db.sql("""
            SELECT log_type, time FROM `tabOvertime Sessions`
            WHERE parent = %s
            ORDER BY idx DESC LIMIT 1
        """, (record_name,), as_dict=True)

        log_type = "OUT" if (last_session and last_session[0]['log_type'] == "IN") else "IN"
        
        # Get next idx with proper null handling
        max_idx_result = frappe.db.sql("""
            SELECT COALESCE(MAX(idx), 0) + 1 as next_idx
            FROM `tabOvertime Sessions`
            WHERE parent = %s
        """, (record_name,), as_dict=True)
        
        max_idx = max_idx_result[0]['next_idx'] if max_idx_result else 1

        # Insert new session
        child_name = make_autoname('OTS-.#####')
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

        # Calculate and update total overtime if this is an OUT
        if log_type == "OUT" and last_session and last_session[0].get('time'):
            calculate_and_update_overtime_total(record_name, last_session[0]['time'], checkin_time.time())

        frappe.db.commit()

        return {
            "status": "success",
            "name": record_name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Overtime Checkin"
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error updating overtime session: {str(e)}", "Overtime Update Error")
        raise


def update_security_session(record_name, employee_id, checkin_time, checkin_date):
    """
    Add new session to existing security record
    """
    try:
        # Get last log type for this record
        last_session = frappe.db.sql("""
            SELECT log_type, time FROM `tabSecurity Gate Sessions`
            WHERE parent = %s
            ORDER BY idx DESC LIMIT 1
        """, (record_name,), as_dict=True)

        log_type = "OUT" if (last_session and last_session[0]['log_type'] == "IN") else "IN"
        
        # Get next idx with proper null handling
        max_idx_result = frappe.db.sql("""
            SELECT COALESCE(MAX(idx), 0) + 1 as next_idx
            FROM `tabSecurity Gate Sessions`
            WHERE parent = %s
        """, (record_name,), as_dict=True)
        
        max_idx = max_idx_result[0]['next_idx'] if max_idx_result else 1

        # Insert new session
        child_name = make_autoname('SECS-.#####')
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

        # Calculate and update total session time if this is an OUT
        if log_type == "OUT" and last_session and last_session[0].get('time'):
            calculate_and_update_security_total(record_name, last_session[0]['time'], checkin_time.time())

        frappe.db.commit()

        return {
            "status": "success",
            "name": record_name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Security Gate Checkin"
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error updating security session: {str(e)}", "Security Update Error")
        raise


def calculate_and_update_overtime_total(record_name, in_time, out_time):
    """
    Calculate session duration and update total overtime
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
        current_total = frappe.db.get_value("Overtime Checkin", record_name, "total_overtime") or 0
        new_total = current_total + session_seconds
        
        # Update total overtime
        frappe.db.sql("""
            UPDATE `tabOvertime Checkin`
            SET total_overtime = %s, modified = NOW()
            WHERE name = %s
        """, (new_total, record_name))
        
    except Exception as e:
        frappe.log_error(f"Error calculating overtime: {str(e)}", "Overtime Calculation Error")


def calculate_and_update_security_total(record_name, in_time, out_time):
    """
    Calculate session duration and update total security session time
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
        current_total = frappe.db.get_value("Security Gate Checkin", record_name, "total_session_time") or 0
        new_total = current_total + session_seconds
        
        # Update total session time
        frappe.db.sql("""
            UPDATE `tabSecurity Gate Checkin`
            SET total_session_time = %s, modified = NOW()
            WHERE name = %s
        """, (new_total, record_name))
        
    except Exception as e:
        frappe.log_error(f"Error calculating security time: {str(e)}", "Security Calculation Error")
