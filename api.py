import frappe
from frappe.utils import add_days, get_datetime, today, getdate, add_months, formatdate
import json
import time
from datetime import timedelta
from collections import defaultdict

# -------------------------------------------------------------------------
# Cache implementation with TTL and manual invalidation
# -------------------------------------------------------------------------
_cache = {}
_cache_timestamp = {}
CACHE_TTL = 300  # 5 minutes in seconds

def cache_get(key):
    """Get a value from cache if it exists and is not expired"""
    if key in _cache and key in _cache_timestamp:
        if time.time() - _cache_timestamp[key] < CACHE_TTL:
            return _cache[key]
    return None

def cache_set(key, value):
    """Set a value in cache with current timestamp"""
    _cache[key] = value
    _cache_timestamp[key] = time.time()
    return value

def cache_clear(prefix=None):
    """Clear all cache or cache with specific prefix"""
    global _cache, _cache_timestamp
    if prefix is None:
        _cache = {}
        _cache_timestamp = {}
    else:
        keys_to_delete = [k for k in _cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            if key in _cache:
                del _cache[key]
            if key in _cache_timestamp:
                del _cache_timestamp[key]

# -------------------------------------------------------------------------
# Basic API Functions
# -------------------------------------------------------------------------
@frappe.whitelist()
def get_date():
    """Return current date"""
    return frappe.utils.today()

@frappe.whitelist()
def get_user_details(email=None):
    """Get user details from email"""
    if not email:
        return {"error": "Email parameter is required."}
    
    # Special case for admin users
    if email in ["Administrator", "silerp@softlandindia.co.in"]:
        return {
            "full_name": "MURALY G",
            "email": "silerp@softlandindia.co.in"
        }
    
    # Check cache first
    cache_key = f"user_details:{email}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    try:
        # Query the database
        employee = frappe.db.get_value(
            "Employee", 
            {"user_id": email}, 
            ["employee", "user_id"], 
            as_dict=True
        )
        
        if not employee:
            return {"error": "User not found."}
            
        result = {
            "full_name": employee.employee,
            "email": employee.user_id
        }
        
        # Cache the result
        return cache_set(cache_key, result)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Unexpected Error in get_user_details")
        return {"error": str(e)}

# -------------------------------------------------------------------------
# Attendance Data Functions
# -------------------------------------------------------------------------
def get_attendance_records(employee_name, date_str):
    """Get attendance records for an employee on a specific date"""
    cache_key = f"attendance:{employee_name}:{date_str}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    start_datetime = get_datetime(date_str + " 00:00:00")
    end_datetime = get_datetime(date_str + " 23:59:59")

    query = """
        SELECT `log_type`, `time`
        FROM `tabEmployee Checkin`
        WHERE `employee` = %s
        AND `time` BETWEEN %s AND %s
        ORDER BY `time` ASC
    """
    
    result = frappe.db.sql(query, (employee_name, start_datetime, end_datetime), as_dict=True)
    return cache_set(cache_key, result)

def get_employee_details(employee_name):
    """Get employee details"""
    cache_key = f"employee:{employee_name}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    result = frappe.db.get_value(
        "Employee", 
        {"employee": employee_name}, 
        ["department", "custom_team", "reports_to"], 
        as_dict=True
    ) or {}
    
    return cache_set(cache_key, result)

def process_attendance_records(employee_name, attendance_records):
    """Process attendance records to get sessions and total working hours"""
    sessions = []
    total_working_seconds = 0
    current_session = {}
    first_checkin = None
    last_logout = None

    for record in attendance_records:
        log_type = record["log_type"]
        log_time = record["time"]

        if log_type == "IN":
            if not first_checkin:
                first_checkin = log_time.strftime("%H:%M:%S")
                
            if "in_time" in current_session and "out_time" not in current_session:
                # Incomplete previous session
                sessions.append({
                    f"session {len(sessions) + 1}": {
                        "employee_name": employee_name,
                        "date": str(current_session["in_time"].date()),
                        "in_time": current_session["in_time"].strftime("%H:%M:%S"),
                        "out_time": "",
                        "working_hours": "0:00:00"
                    }
                })
            current_session = {"in_time": log_time}
        
        elif log_type == "OUT":
            last_logout = log_time.strftime("%H:%M:%S")
            
            if "in_time" not in current_session:
                # Orphaned check-out
                sessions.append({
                    f"session {len(sessions) + 1}": {
                        "employee_name": employee_name,
                        "date": str(log_time.date()),
                        "in_time": "",
                        "out_time": log_time.strftime("%H:%M:%S"),
                        "working_hours": "0:00:00"
                    }
                })
            else:
                # Complete session
                in_time = current_session["in_time"]
                out_time = log_time
                working_seconds = (out_time - in_time).total_seconds()
                total_working_seconds += working_seconds

                working_hours = format_seconds_to_time(working_seconds)

                sessions.append({
                    f"session {len(sessions) + 1}": {
                        "employee_name": employee_name,
                        "date": str(in_time.date()),
                        "in_time": in_time.strftime("%H:%M:%S"),
                        "out_time": out_time.strftime("%H:%M:%S"),
                        "working_hours": working_hours
                    }
                })
                current_session = {}

    # Handle incomplete final session
    if "in_time" in current_session:
        sessions.append({
            f"session {len(sessions) + 1}": {
                "employee_name": employee_name,
                "date": str(current_session["in_time"].date()),
                "in_time": current_session["in_time"].strftime("%H:%M:%S"),
                "out_time": "",
                "working_hours": "0:00:00"
            }
        })

    total_working_hours = format_seconds_to_time(total_working_seconds)
    
    return sessions, total_working_hours, total_working_seconds, first_checkin, last_logout

def format_seconds_to_time(seconds):
    """Format seconds to HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}"

# -------------------------------------------------------------------------
# Main Attendance API
# -------------------------------------------------------------------------
@frappe.whitelist()
def get_main_attendance(employee_name, date):
    """Get attendance summary for an employee"""
    cache_key = f"main_attendance:{employee_name}:{date}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    # Fetch attendance records
    attendance_records = get_attendance_records(employee_name, date)
    
    # Process records
    _, total_working_hours, _, first_checkin, last_logout = process_attendance_records(
        employee_name, attendance_records
    )

    # Employee details
    employee_details = get_employee_details(employee_name)
    
    # Get report hierarchy using a non-recursive approach
    report_hierarchy = get_all_reportees_api(employee_name, date)
    
    # Calculate weekly and monthly averages
    w_m_average = get_w_m_average(employee_name, date)

    result = {
        "employee_name": employee_name,
        "first_checkin": first_checkin if first_checkin else "-",
        "last_logout": last_logout if last_logout else "-",
        "department": employee_details.get("department", "-") if employee_details else "-",
        "custom_team": employee_details.get("custom_team", "-") if employee_details else "-",
        "total_working_hours": total_working_hours,
        "w_m_average": w_m_average,
        "report_hierarchy": report_hierarchy
    }
    
    return cache_set(cache_key, result)

@frappe.whitelist()
def get_attendance(employee_name, date):
    """Get detailed attendance sessions for an employee"""
    cache_key = f"attendance_details:{employee_name}:{date}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    # Get attendance records
    attendance_records = get_attendance_records(employee_name, date)
    
    # Process records to get sessions and working hours
    sessions, total_working_hours, _, _, _ = process_attendance_records(
        employee_name, attendance_records
    )

    # Construct the final response JSON
    result = {
        "attendance_sessions": sessions,
        "working_hours": total_working_hours
    }
    
    return cache_set(cache_key, result)

@frappe.whitelist()
def get_working_days_status(employee_name, date):
    """Get working days status for an employee"""
    cache_key = f"working_days_status:{employee_name}:{date}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    return cache_set(cache_key, get_working_days_status_api(employee_name, date))

# -------------------------------------------------------------------------
# Reporting Hierarchy Functions
# -------------------------------------------------------------------------
def get_reportees_map():
    """Get all employee reporting relationships in one query"""
    cache_key = "all_reporting_relationships"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    query = """
        SELECT employee, reports_to
        FROM `tabEmployee`
        WHERE status = 'Active' AND reports_to IS NOT NULL
    """
    
    results = frappe.db.sql(query, as_dict=True)
    
    # Build reporting hierarchy as a directed graph
    hierarchy = defaultdict(list)
    for row in results:
        if row['reports_to']:
            hierarchy[row['reports_to']].append(row['employee'])
    
    return cache_set(cache_key, dict(hierarchy))

def get_all_reportees_api(employee_name, current_date):
    """Get all reportees for an employee in a non-recursive way"""
    cache_key = f"reportees:{employee_name}:{current_date}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    # Get all reporting relationships
    all_reports = get_reportees_map()
    
    # Use queue to process all reportees without recursion
    result_reportees = []
    queue = [(employee_name, None)]  # (employee, reports_to)
    processed = set()
    direct_reports = []
    
    # First level reportees are handled separately
    if employee_name in all_reports:
        direct_reports = all_reports[employee_name]
        for reportee in direct_reports:
            queue.append((reportee, employee_name))
    
    # Process direct reports first for a cleaner hierarchy
    for reportee in direct_reports:
        if reportee in processed:
            continue
            
        processed.add(reportee)
        
        # Get attendance for the reportee
        reportee_attendance = get_main_attendance(reportee, current_date)
        
        # Add reportee to the result
        reportee_data = {
            "employee": reportee,
            "reportee_attendance": reportee_attendance,
            # We'll add sub-reportees later as needed
        }
        
        result_reportees.append(reportee_data)
    
    result = {
        "current_date": current_date, 
        "report_names": result_reportees
    }
    
    return cache_set(cache_key, result)

# -------------------------------------------------------------------------
# Average Calculation Functions
# -------------------------------------------------------------------------

def get_working_days_status_api(employee_name, current_date):
    """Get working days status for an employee for the current month"""
    current_date = getdate(current_date)
    
    # Get first and last day of current month
    first_day_of_month = current_date.replace(day=1)
    next_month = add_months(first_day_of_month, 1)
    last_day_of_month = add_days(next_month, -1)

    # Shared parameters
    date_params = {
        "employee_name": employee_name,
        "first_day": str(first_day_of_month),
        "last_day": str(last_day_of_month)
    }
    
    # Get employee's holiday list
    holiday_list = frappe.db.get_value("Employee", employee_name, "holiday_list") or ""

    # Total working days (excluding holidays)
    total_working_days_query = """
        WITH RECURSIVE date_range AS (
            SELECT %(first_day)s AS work_date
            UNION ALL
            SELECT DATE_ADD(work_date, INTERVAL 1 DAY)
            FROM date_range
            WHERE work_date < %(last_day)s
        )
        SELECT COUNT(*) AS total_working_days
        FROM date_range dr
        LEFT JOIN `tabHoliday` h ON dr.work_date = h.holiday_date AND h.parent = %(holiday_list)s
        WHERE h.holiday_date IS NULL
    """
    total_working_days_result = frappe.db.sql(total_working_days_query, {
        **date_params,
        "holiday_list": holiday_list
    }, as_dict=True)
    total_working_days = total_working_days_result[0]["total_working_days"] if total_working_days_result else 0

    # Days worked (distinct check-in dates)
    days_worked_query = """
        SELECT COUNT(DISTINCT DATE(`time`)) AS days_worked
        FROM `tabEmployee Checkin`
        WHERE `employee` = %(employee_name)s
        AND DATE(`time`) BETWEEN %(first_day)s AND %(last_day)s
    """
    days_worked_result = frappe.db.sql(days_worked_query, date_params, as_dict=True)
    days_worked = days_worked_result[0]["days_worked"] if days_worked_result else 0

    # Reusable function for approved leave by type
    def get_approved_leave(leave_type):
        leave_query = """
            SELECT COALESCE(SUM(total_leave_days), 0) AS approved_leave
            FROM `tabLeave Application`
            WHERE employee = %(employee_name)s
            AND leave_type = %(leave_type)s
            AND status = 'Approved'
            AND docstatus = 1
            AND (
                (from_date BETWEEN %(first_day)s AND %(last_day)s)
                OR (to_date BETWEEN %(first_day)s AND %(last_day)s)
                OR (from_date <= %(first_day)s AND to_date >= %(last_day)s)
            )
        """
        result = frappe.db.sql(leave_query, {**date_params, "leave_type": leave_type}, as_dict=True)
        return result[0]["approved_leave"] if result else 0

    approved_leave = get_approved_leave("Casual Leave")
    approved_sick_leave = get_approved_leave("Sick Leave")
    approved_compensatory_leave = get_approved_leave("Compensatory Leave")  # Fixed leave type from 'Sick Leave'
    
    # Return the result
    result = {
        "employee_name": employee_name,
        "month": formatdate(first_day_of_month, "MMMM YYYY"),
        "total_working_days": int(total_working_days),
        "days_worked": int(days_worked),
        "approved_leave": int(approved_leave),
        "approved_sick_leave": int(approved_sick_leave),
        "approved_compensatory_leave": int(approved_compensatory_leave),
        "days_remaining": max(0, int(total_working_days) - int(days_worked) - int(approved_leave))
    }
    
    return result


def get_total_working_days(start_date, end_date, holiday_list):
    """Calculate total working days (weekdays excluding holidays) in the given period"""
    query = """
    WITH RECURSIVE date_range AS (
        SELECT %(start_date)s AS work_date
        UNION ALL
        SELECT DATE_ADD(work_date, INTERVAL 1 DAY)
        FROM date_range
        WHERE work_date < %(end_date)s
    )
    SELECT COUNT(*) AS total_working_days
    FROM date_range dr
    LEFT JOIN `tabHoliday` h ON dr.work_date = h.holiday_date AND h.parent = %(holiday_list)s
    WHERE 
        DAYOFWEEK(dr.work_date) NOT IN (1, 7)  -- Exclude Sundays (1) and Saturdays (7)
        AND h.holiday_date IS NULL  -- Exclude holidays
    """
    
    result = frappe.db.sql(query, {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "holiday_list": holiday_list or ""
    }, as_dict=True)
    
    return result[0]["total_working_days"] if result else 0

def get_days_worked(employee_name, start_date, end_date):
    """Get count of days with check-ins for the employee in the given period"""
    query = """
    SELECT COUNT(DISTINCT DATE(`time`)) AS days_worked
    FROM `tabEmployee Checkin`
    WHERE employee = %(employee_name)s
    AND DATE(`time`) BETWEEN %(start_date)s AND %(end_date)s
    """
    
    result = frappe.db.sql(query, {
        "employee_name": employee_name,
        "start_date": str(start_date),
        "end_date": str(end_date)
    }, as_dict=True)
    
    return result[0]["days_worked"] if result else 0

def get_available_leave(employee_name):
    """Get total available leave balance for the employee"""
    # Get current year
    current_year = today()[:4]
    
    # Query to get leave allocation balance
    query = """
    SELECT 
        COALESCE(SUM(
            CASE 
                WHEN la.carry_forward = 1 
                THEN la.new_leaves_allocated + COALESCE(la.carry_forwarded_leaves_count, 0)
                ELSE la.new_leaves_allocated
            END
        ), 0) as total_allocated,
        COALESCE(SUM(COALESCE(la.leaves_taken, 0)), 0) as total_taken
    FROM `tabLeave Allocation` la
    WHERE la.employee = %(employee_name)s
    AND la.docstatus = 1  -- Only approved allocations
    AND YEAR(la.from_date) = %(current_year)s
    """
    
    result = frappe.db.sql(query, {
        "employee_name": employee_name,
        "current_year": current_year
    }, as_dict=True)
    
    if result:
        total_allocated = result[0]["total_allocated"] or 0
        total_taken = result[0]["total_taken"] or 0
        return max(0, total_allocated - total_taken)  # Ensure non-negative
    
    return 0

def get_approved_leave(employee_name, start_date, end_date):
    """Get count of approved leave days for the employee in the given period"""
    query = """
    SELECT COALESCE(SUM(la.total_leave_days), 0) as approved_leave_days
    FROM `tabLeave Application` la
    WHERE la.employee = %(employee_name)s
    AND la.docstatus = 1  -- Only approved leave applications
    AND la.status = 'Approved'
    AND (
        (la.from_date BETWEEN %(start_date)s AND %(end_date)s) OR
        (la.to_date BETWEEN %(start_date)s AND %(end_date)s) OR
        (la.from_date <= %(start_date)s AND la.to_date >= %(end_date)s)
    )
    """
    
    result = frappe.db.sql(query, {
        "employee_name": employee_name,
        "start_date": str(start_date),
        "end_date": str(end_date)
    }, as_dict=True)
    
    return result[0]["approved_leave_days"] if result else 0


# Get the count of expected working days without check-ins
def get_expected_workdays_without_checkins(employee_name, start_date, end_date, holiday_list, exclude_date):
    """Returns the count of expected working days without check-ins or valid leave"""
    query = """
    WITH RECURSIVE date_range AS (
        SELECT %(start_date)s AS work_date
        UNION ALL
        SELECT DATE_ADD(work_date, INTERVAL 1 DAY)
        FROM date_range
        WHERE work_date < %(end_date)s
    ),
    checkins AS (
        SELECT DISTINCT DATE(`time`) AS checkin_date
        FROM `tabEmployee Checkin`
        WHERE employee = %(employee_name)s
          AND DATE(`time`) BETWEEN %(start_date)s AND %(end_date)s
    )
    SELECT COUNT(*) AS expected_days_count
    FROM date_range dr
    LEFT JOIN `tabHoliday` h ON dr.work_date = h.holiday_date AND h.parent = %(holiday_list)s
    LEFT JOIN `tabAttendance` att ON dr.work_date = att.attendance_date AND att.employee = %(employee_name)s
    LEFT JOIN checkins c ON c.checkin_date = dr.work_date
    WHERE 
        DAYOFWEEK(dr.work_date) NOT IN (1, 7)
        AND h.holiday_date IS NULL
        AND (att.status IS NULL OR att.status NOT IN ('On Leave', 'Half Day', 'Work From Home'))
        AND c.checkin_date IS NULL
    """
    result = frappe.db.sql(query, {
        "employee_name": employee_name,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "holiday_list": holiday_list,
        "exclude_date": str(exclude_date)
    }, as_dict=True)

    return result[0]["expected_days_count"] if result else 0

def get_w_m_average(employee_name, current_date):
    """Get weekly and monthly averages"""
    cache_key = f"w_m_average:{employee_name}:{current_date}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
    
    # Calculate averages
    week_data = get_weekly_average(employee_name, current_date)
    month_data = get_monthly_average(employee_name, current_date)
    
    result = {"week_data": week_data, "month_data": month_data}
    return cache_set(cache_key, result)

def get_weekly_average(employee_name, current_date):
    """Calculate weekly average working hours including expected non-checkin days"""
    cache_key = f"weekly_avg:{employee_name}:{current_date}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data

    current_date = getdate(current_date)
    week_start = add_days(current_date, -current_date.weekday())

    # ✅ Query check-in records
    query = """
        SELECT DATE(`time`) as work_date, `log_type`, `time`
        FROM `tabEmployee Checkin`
        WHERE `employee` = %s
        AND DATE(`time`) BETWEEN %s AND %s
        ORDER BY `time` ASC
    """
    week_records = frappe.db.sql(query, (employee_name, week_start, current_date), as_dict=True)

    # ✅ RECURSIVE query for expected workdays without check-ins
    holiday_list = frappe.db.get_value("Employee", employee_name, "holiday_list")
    current_date_str = str(current_date)


    # expected workdays without check-ins
    extra_days = get_expected_workdays_without_checkins(
        employee_name, week_start, current_date, holiday_list, current_date_str
    )

    # ✅ Process check-ins into working hours
    daily_records = {}
    for record in week_records:
        date_str = str(record["work_date"])
        if date_str not in daily_records:
            daily_records[date_str] = []
        daily_records[date_str].append(record)

    total_seconds = 0
    valid_days = 0

    for date_str, records in daily_records.items():
        if date_str == str(current_date):
            continue
        day_seconds = 0
        current_session = {}

        for record in records:
            log_type = record["log_type"]
            log_time = record["time"]
            if log_type == "IN":
                current_session["in_time"] = log_time
            elif log_type == "OUT" and "in_time" in current_session:
                working_seconds = (log_time - current_session["in_time"]).total_seconds()
                day_seconds += working_seconds
                current_session = {}

        if day_seconds > 0:
            total_seconds += day_seconds
            valid_days += 1

    total_considered_days = valid_days + extra_days

    if total_considered_days == 0:
        result = {"weekly_avg_hh_mm": "0.00", "days_considered": 0}
    else:
        avg_seconds = total_seconds // total_considered_days
        avg_hours = int(avg_seconds // 3600)
        avg_minutes = int((avg_seconds % 3600) // 60)
        avg_hh_mm = f"{avg_hours}.{str(avg_minutes).zfill(2)}"
        result = {
            "weekly_avg_hh_mm": avg_hh_mm,
            "days_considered": total_considered_days,
            "extra_days": extra_days
        }

    return cache_set(cache_key, result)

def get_monthly_average(employee_name, current_date):
    """Calculate monthly average working hours"""
    cache_key = f"monthly_avg:{employee_name}:{current_date}"
    cached_data = cache_get(cache_key)
    if cached_data:
        return cached_data
        
    current_date = getdate(current_date)
    
    # Get the first day of the current month
    first_day_of_current_month = current_date.replace(day=1)

    # Get the first day of the next month
    first_day_of_next_month = add_months(current_date.replace(day=1), 1)
    
    # Get all check-ins/check-outs for the month in one query
    query = """
        SELECT DATE(`time`) as work_date, `log_type`, `time`
        FROM `tabEmployee Checkin`
        WHERE `employee` = %s
        AND DATE(`time`) >= %s
        AND DATE(`time`) < %s
        ORDER BY `time` ASC
    """
    
    month_records = frappe.db.sql(
        query, 
        (
            employee_name, 
            first_day_of_current_month,
            first_day_of_next_month
        ), 
        as_dict=True
    )

     # ✅ RECURSIVE query for expected workdays without check-ins
    holiday_list = frappe.db.get_value("Employee", employee_name, "holiday_list")
    current_date_str = str(current_date)
    
    # expected workdays without check-ins
    extra_days = get_expected_workdays_without_checkins(
        employee_name, first_day_of_current_month, first_day_of_next_month, holiday_list, current_date_str
    )
    
    # Group records by date
    daily_records = {}
    for record in month_records:
        date_str = str(record["work_date"])
        if date_str not in daily_records:
            daily_records[date_str] = []
        daily_records[date_str].append(record)
    
    # Calculate working hours for each day
    total_seconds = 0
    valid_days = 0
    
    for date_str, records in daily_records.items():
        # if date_str == str(current_date):
        #     continue  # Skip current day
            
        # Calculate working hours for this day
        day_seconds = 0
        current_session = {}
        
        for record in records:
            log_type = record["log_type"]
            log_time = record["time"]
            
            if log_type == "IN":
                current_session["in_time"] = log_time
            elif log_type == "OUT" and "in_time" in current_session:
                working_seconds = (log_time - current_session["in_time"]).total_seconds()
                day_seconds += working_seconds
                current_session = {}
        
        if day_seconds > 0:
            total_seconds += day_seconds
            valid_days += 1
    
    # Calculate average
    # if valid_days == 0:
    total_considered_days = valid_days + extra_days

    if total_considered_days == 0:
        result = {
            "monthly_avg_hh_mm": "0.00", 
            "days_considered": 0,
            "month": formatdate(first_day_of_current_month, "MMMM YYYY")
        }
    else:
        avg_seconds = total_seconds // total_considered_days 
        avg_hours = int(avg_seconds // 3600)
        avg_minutes = int((avg_seconds % 3600) // 60)
        
        # Format output
        avg_hh_mm = f"{avg_hours}.{str(avg_minutes).zfill(2)}"
        
        result = {
            "monthly_avg_hh_mm": avg_hh_mm,
            "days_considered": valid_days,
            "extra_days": extra_days,
            "month": formatdate(first_day_of_current_month, "MMMM YYYY")
        }
    
    return cache_set(cache_key, result)

# Optional: Add this function if you need to manually clear cache
@frappe.whitelist()
def clear_attendance_cache(employee_name=None):
    """Clear attendance cache for a specific employee or all employees"""
    if employee_name:
        cache_clear(f"attendance:{employee_name}")
        cache_clear(f"main_attendance:{employee_name}")
        cache_clear(f"attendance_details:{employee_name}")
        cache_clear(f"weekly_avg:{employee_name}")
        cache_clear(f"monthly_avg:{employee_name}")
        cache_clear(f"w_m_average:{employee_name}")
        cache_clear(f"reportees:{employee_name}")
        return {"status": "success", "message": f"Cache cleared for employee {employee_name}"}
    else:
        cache_clear()
        return {"status": "success", "message": "All cache cleared"}
    

