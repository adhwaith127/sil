import frappe
from frappe.utils import get_datetime, getdate
from frappe import _
from frappe.model.naming import make_autoname
from datetime import timedelta,datetime

def _check_duplicate_checkin(employee_id, checkin_time):
    recent = frappe.db.sql("""
        SELECT time FROM `tabEmployee Checkin`
        WHERE employee = %s AND time >= %s
        ORDER BY time DESC LIMIT 1
    """, (employee_id, checkin_time - timedelta(minutes=2)))
    
    if recent:
        return True
    return False

@frappe.whitelist(allow_guest=True)
def add_checkin(punchingcode, employee_name, time, device_id):
    try:
        if not punchingcode or not str(punchingcode).strip():
            frappe.log_error("Punchingcode not provided")
            frappe.throw("Punchingcode not provided")
        if not time or not str(time).strip():
            frappe.log_error("Time not provided")
            frappe.throw("Time not provided")

        try:
            # checkin_time = get_datetime(time)
            checkin_time=datetime.strptime(time,"%d-%m-%Y %H:%M:%S")
        except:
            frappe.log_error("Invalid time format")
            frappe.throw("Invalid time format")

        frappe.db.begin()
        # Get employee by biometric ID
        employee = frappe.db.get_value(
            "Employee",
            {"attendance_device_id": punchingcode},
            ["name", "employee_name"]
        )

        if not employee:
            frappe.throw(_("No Employee found for Biometric ID: {0}").format(punchingcode), frappe.DoesNotExistError)

        employee_id, full_name = employee
        
        checkin_date = getdate(checkin_time)

        if _check_duplicate_checkin(employee_id,checkin_time):
            frappe.throw("Already has a checkin log within the cooldown period")

        # Determine log_type
        log_type = "IN"
        last_log_type = frappe.db.sql(
            """
            SELECT log_type FROM `tabEmployee Checkin`
            WHERE employee = %s AND DATE(time) = %s
            ORDER BY time DESC LIMIT 1
            """,
            (employee_id, checkin_date),
            as_dict=0
        )

        if last_log_type:
            log_type = "OUT" if last_log_type[0][0] == "IN" else "IN"

        # Generate name using naming series (e.g., CHKIN-00001)
        name = make_autoname('CHKIN-.#####')

        device_doc = frappe.get_single("Biometric Device Mapping")
        # Search in the child table
        location = None
        try:
            for row in device_doc.table_sgvh:
                if row.serial_number == device_id:
                    location = row.location
                    break 
        except Exception as e:
            frappe.log_error(f"Error while fetching device location: {str(e)}", "Biometric Lookup Error")
	
        # Insert using SQL
        frappe.db.sql("""
            INSERT INTO `tabEmployee Checkin`
            (name, creation, modified, modified_by, owner, docstatus, idx,
            employee, employee_name, time, device_id, log_type,custom_device_location)
            VALUES (%s, NOW(), NOW(), %s, %s, 0, 0,
            %s, %s, %s, %s, %s, %s)
        """, (
            name, frappe.session.user, frappe.session.user,
            employee_id, full_name, checkin_time, device_id, log_type,location
        ))

        frappe.db.commit()

        return {
            "status": "success",
            "name": name,
            "log_type": log_type,
            "checkin_time": checkin_time
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error("Error in adding checkin",str(e))
        return {"Error":"Error in adding checkin. Checkin not added !!!!!!"}
