import frappe
from frappe.utils import get_datetime, getdate, time_diff_in_seconds
from frappe import _
from frappe.model.naming import make_autoname
from datetime import datetime, timedelta, time
import pytz
import pymysql


def handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id, location=None):
    """
    Create Employee Checkin Log with enhanced error handling
    """
    try:    
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

        if last_log_type:
            log_type = "OUT" if last_log_type[0][0] == "IN" else "IN"

        # Generate name using naming series
        name = make_autoname('CHKIN-.#####')

        # Insert new checkin record
        ist = pytz.timezone('Asia/Kolkata')
        current_ist = datetime.now(ist).replace(microsecond=0)
        
        frappe.db.sql("""
            INSERT INTO `tabEmployee Checkin`
            (name, creation, modified, modified_by, owner, docstatus, idx,
             employee, employee_name, time, device_id, log_type, custom_device_location)
            VALUES (%s, %s, %s, %s, %s, 0, 0,
             %s, %s, %s, %s, %s, %s)
        """, (
            name, current_ist, current_ist, frappe.session.user, frappe.session.user,
            employee_id, full_name, checkin_time, device_id, log_type, location
        ))

        # Commit the transaction
        frappe.db.commit()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time,
            "table": "Employee Checkin"
        }
    
    except pymysql.err.ProgrammingError as e:
        frappe.db.rollback()
        error_msg = f"SQL syntax or column error: {str(e)}"
        frappe.log_error(f"SQL Entry Error for {employee_id}: {error_msg}", "SQL Entry Error")
        frappe.throw(_("Database query error. Please check system configuration."))
        
    except pymysql.err.IntegrityError as e:
        frappe.db.rollback()
        error_msg = f"Database integrity error: {str(e)}"
        frappe.log_error(f"DB Integrity Error for {employee_id}: {error_msg}", "Database Integrity Error")
        frappe.throw(_("Data integrity error. Record may already exist."))
        
    except pymysql.err.OperationalError as e:
        frappe.db.rollback()
        error_msg = f"Database operational error: {str(e)}"
        frappe.log_error(f"DB Operational Error for {employee_id}: {error_msg}", "Database Operational Error")
        frappe.throw(_("Database connection error. Please try again."))
        
    except Exception as e:
        frappe.db.rollback()
        error_msg = f"Unexpected error in handle_employee_checkin: {str(e)}"
        frappe.log_error(f"Employee Checkin Error for {employee_id}: {error_msg}", "Employee Checkin Error")
        frappe.throw(_("Error in adding employee checkin: {0}").format(str(e)))


@frappe.whitelist(allow_guest=True)
def add_checkin(punchingcode, employee_name, time, device_id):
    """
    Main API function with enhanced error handling and validation
    """
    try:
        # Input validation
        if not punchingcode:
            frappe.throw(_("Punching code is required"))
        if not time:
            frappe.throw(_("Time is required"))
        if not device_id:
            frappe.throw(_("Device ID is required"))

        # Get employee by biometric ID
        employee = frappe.db.get_value(
            "Employee",
            {"attendance_device_id": punchingcode},
            ["name", "employee_name"]
        )

        if not employee:
            error_msg = f"No Employee found for Biometric ID: {punchingcode}"
            frappe.log_error(error_msg, "Employee Not Found")
            frappe.throw(_(error_msg))

        employee_id, full_name = employee

        # Parse and validate time
        try:
            checkin_time = datetime.strptime(time, "%d-%m-%Y %H:%M:%S")
            checkin_date = checkin_time.date()
        except ValueError as e:
            error_msg = f"Invalid time format received: {time}. Expected format: dd-mm-yyyy HH:MM:SS"
            frappe.log_error(f"Time Format Error for {punchingcode}: {error_msg}", "Time Format Error")
            frappe.throw(_(error_msg))

        # Validate parsed values
        if not checkin_date or not checkin_time:
            frappe.throw(_("Invalid checkin time after parsing"))

        # Validate that all required parameters are present
        if any(param is None for param in [employee_id, full_name, checkin_time, checkin_date, device_id]):
            missing_params = []
            if employee_id is None: missing_params.append("employee_id")
            if full_name is None: missing_params.append("full_name")
            if checkin_time is None: missing_params.append("checkin_time")
            if checkin_date is None: missing_params.append("checkin_date")
            if device_id is None: missing_params.append("device_id")
            
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            frappe.log_error(f"Parameter Validation Error for {punchingcode}: {error_msg}", "Parameter Error")
            frappe.throw(_(error_msg))

        # Process the checkin
        result = handle_employee_checkin(employee_id, full_name, checkin_time, checkin_date, device_id)
        
        # Log successful processing
        frappe.logger().info(f"Successfully processed checkin for {full_name} ({punchingcode}) at {checkin_time}")
        
        return result

    except frappe.DoesNotExistError as e:
        error_msg = f"Employee record not found: {str(e)}"
        frappe.log_error(f"Employee Lookup Error for {punchingcode}: {error_msg}", "Employee Not Found")
        frappe.throw(_("Employee not found in system."))
        
    except frappe.ValidationError as e:
        error_msg = f"Validation error: {str(e)}"
        frappe.log_error(f"Validation Error for {punchingcode}: {error_msg}", "Validation Error")
        frappe.throw(_("Validation error: {0}").format(str(e)))
        
    except frappe.PermissionError as e:
        error_msg = f"Permission error: {str(e)}"
        frappe.log_error(f"Permission Error for {punchingcode}: {error_msg}", "Permission Error")
        frappe.throw(_("Insufficient permissions to process checkin."))
        
    except Exception as e:
        error_msg = f"Unexpected error in add_checkin: {str(e)}"
        frappe.log_error(f"API Error for {punchingcode}: {error_msg}", "Biometric API Error")
        frappe.throw(_("Error processing checkin: {0}").format(str(e)))