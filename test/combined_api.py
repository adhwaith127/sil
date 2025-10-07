import frappe
from frappe.utils import format_datetime, time_diff_in_hours, today, getdate
from collections import OrderedDict, defaultdict
from datetime import datetime, date, timedelta
import calendar
from typing import List, Dict, Any, Tuple, Optional, Set


# === DATA RETRIEVAL FUNCTIONS ===

def _get_employee_holidays(start_date, end_date):
    """Get employee holidays for date range"""
    try:
        holiday_query = """
            SELECT em.name as employee, em.holiday_list, h.holiday_date
            FROM `tabEmployee` em 
            LEFT JOIN `tabHoliday` h ON em.holiday_list=h.parent
                AND h.holiday_date BETWEEN %s AND %s
            WHERE em.status='Active'
            ORDER BY em.name
        """
        employee_holiday_data = frappe.db.sql(holiday_query, (start_date, end_date), as_dict=True)

        employee_holidays = defaultdict(list)
        for holiday in employee_holiday_data:
            emp = holiday['employee']
            if holiday['holiday_date']:
                employee_holidays[emp].append(getdate(holiday['holiday_date']))
            else:
                employee_holidays.setdefault(emp, [])

        return dict(employee_holidays)
    except Exception as e:
        frappe.log_error("Error in getting employee holidays", str(e))
        return {}


def _get_leaves_for_period(start_date, end_date):
    """Get approved leaves for all employees in date range"""
    try:
        leaves_query = """
            SELECT employee, from_date, to_date
            FROM `tabLeave Application`
            WHERE status = 'Approved'
            AND docstatus = 1
            AND (
                (from_date BETWEEN %(start_date)s AND %(end_date)s) OR
                (to_date BETWEEN %(start_date)s AND %(end_date)s) OR  
                (from_date <= %(start_date)s AND to_date >= %(end_date)s)
            )
        """
        leaves_data = frappe.db.sql(leaves_query, {
            "start_date": start_date,
            "end_date": end_date
        }, as_dict=True)

        employee_leaves = defaultdict(set)
        for leave in leaves_data:
            leave_start = max(leave.from_date, start_date)
            leave_end = min(leave.to_date, end_date)

            current_date = leave_start
            while current_date <= leave_end:
                employee_leaves[leave.employee].add(str(current_date))
                current_date += timedelta(days=1)
        
        return dict(employee_leaves)
    except Exception as e:
        frappe.log_error("Error in getting employee leaves", str(e))
        return {}


def _get_employee_shift_info():
    """Get shift information including working days per employee"""
    try:
        query = """
            SELECT em.name as employee, 
                   COALESCE(st.working_days, 5) as working_days,
                   st.end_time
            FROM `tabEmployee` em
            LEFT JOIN `tabShift Type` st ON em.default_shift = st.name
            WHERE em.status = 'Active'
        """
        shift_data = frappe.db.sql(query, as_dict=True)
        
        employee_shift_info = {}
        for record in shift_data:
            employee_shift_info[record['employee']] = {
                'working_days': record['working_days'],
                'end_time': record['end_time']
            }
            
        return employee_shift_info
    except Exception as e:
        frappe.log_error("Error in getting employee shift info", str(e))
        return {}


def _get_employee_data(start_date, end_date):
    """Get employee checkin data with shift information"""
    try:
        query = """
            SELECT
                ec.employee, ec.time, ec.log_type,
                em.name, em.department, em.reports_to, em.default_shift, em.holiday_list, em.image,
                st.end_time, st.working_days
            FROM `tabEmployee Checkin` AS ec
            JOIN `tabEmployee` AS em ON ec.employee = em.name
            LEFT JOIN `tabShift Type` AS st on em.default_shift=st.name
            WHERE DATE(ec.time) BETWEEN %s and %s AND em.status = 'Active'
            ORDER BY ec.employee, ec.time
        """
        raw_checkin_data = frappe.db.sql(query, (start_date, end_date), as_dict=True)
        return raw_checkin_data
    except Exception as e:
        frappe.log_error("Error in employee data sql", str(e))
        return []


# === BUSINESS LOGIC FUNCTIONS ===

def _is_working_day_for_employee(check_date, emp_holidays):
    """Check if date is working day for employee based on their holiday list"""
    weekday = check_date.weekday()  # 0=Monday, 6=Sunday
    
    # Sunday is always off day
    if weekday == 6:
        return False
    
    # Monday to Saturday: check if date is in employee's holiday list
    if check_date in emp_holidays:
        return False
    
    return True


def _filter_and_separate_checkins(raw_checkin_data, employee_holidays):
    """Separate checkins into regular work and overtime work"""
    try:
        regular_work = []
        overtime_work = []
        
        for record in raw_checkin_data:
            employee = record['employee']
            checkin_date = getdate(record['time'])
            emp_holidays = employee_holidays.get(employee, [])
            
            if _is_working_day_for_employee(checkin_date, emp_holidays):
                regular_work.append(record)
            else:
                overtime_work.append(record)
        
        return regular_work, overtime_work
    except Exception as e:
        frappe.log_error("Error in filtering checkins", str(e))
        return [], []


def _calculate_employee_work_hours(logs, shift_end=None):
    """Calculate work hours with advanced auto-close logic"""
    try:
        if not logs:
            return {
                "employee": None, 
                "department": None, 
                "reports_to": None,
                "date": None, 
                "daily_working_hours": 0.0, 
                "entry_time": None, 
                "exit_time": None, 
                "checkin_pairs": [],
                "status": "Absent"
            }

        total_working_hours = 0.0
        last_in_time = None
        first_in_time = None
        last_out_time = None
        checkin_pairs = []
        current_time = datetime.now()
        current_date = date.today()
        log_date = logs[0]['time'].date()

        # Define default close time (23:59 of log_date)
        default_close_time = datetime.combine(log_date, datetime.strptime("23:59", "%H:%M").time())

        # Process each log entry
        for log in sorted(logs, key=lambda x: x['time']):
            if log['log_type'] == "IN":
                if first_in_time is None:
                    first_in_time = log['time']
                if last_in_time is None:
                    last_in_time = log['time']
            elif log['log_type'] == "OUT":
                if last_in_time:
                    session_duration = time_diff_in_hours(log['time'], last_in_time)
                    total_working_hours += session_duration
                    checkin_pairs.append({
                        "in_time": last_in_time.strftime("%H:%M"),
                        "out_time": log['time'].strftime("%H:%M"),
                        "duration": round(session_duration, 2)
                    })
                    last_in_time = None
                last_out_time = log['time']
        
        # Handle unclosed sessions with advanced logic
        if last_in_time:
            candidate_close_time = shift_end if shift_end else default_close_time
            effective_close_time = max(last_in_time, candidate_close_time)

            should_auto_close = (
                (log_date < current_date) or
                (log_date == current_date and current_time >= effective_close_time)
            )

            if should_auto_close:
                session_duration = time_diff_in_hours(effective_close_time, last_in_time)
                total_working_hours += session_duration
                checkin_pairs.append({
                    "in_time": last_in_time.strftime("%H:%M"),
                    "out_time": effective_close_time.strftime("%H:%M"),
                    "duration": round(session_duration, 2),
                    "auto_closed": True
                })
                last_out_time = effective_close_time
            else:
                # Still ongoing session
                checkin_pairs.append({
                    "in_time": last_in_time.strftime("%H:%M"),
                    "out_time": "Ongoing",
                    "duration": 0.0,
                    "ongoing": True
                })

        # Determine exit time (only if no ongoing session)
        exit_time = None
        if last_out_time and not (last_in_time and not should_auto_close):
            exit_time = last_out_time.strftime("%H:%M")

        return {
            "employee": logs[0]['employee'],
            "department": logs[0]['department'],
            "reports_to": logs[0]['reports_to'],
            "image": logs[0].get('image'),
            "date": format_datetime(logs[0]['time'], 'yyyy-MM-dd'),
            "daily_working_hours": round(total_working_hours, 2),
            "entry_time": first_in_time.strftime("%H:%M") if first_in_time else None,
            "exit_time": exit_time,
            "checkin_pairs": checkin_pairs,
            "status": "Present",
            "has_ongoing_session": last_in_time is not None and not should_auto_close
        }

    except Exception as e:
        frappe.log_error("Error in calculating employee work hours", str(e)) 
        return {"error": "Error in calculating work hours"}


def _sort_checkin_data(filtered_checkin_data):
    """Sort and process checkin data into daily summaries"""
    try:
        grouped_emp_data = defaultdict(lambda: defaultdict(list))
        for entry in filtered_checkin_data:
            date_str = format_datetime(entry['time'], 'yyyy-MM-dd')
            grouped_emp_data[entry['employee']][date_str].append(entry)

        daily_summaries = []
        for employee, day in grouped_emp_data.items():
            for date, logs in day.items():
                if logs:
                    shift_end = logs[0]['end_time']
                    if isinstance(shift_end, timedelta):
                        shift_end = (datetime.min + shift_end).time()
                    elif isinstance(shift_end, str):
                        try:
                            shift_end = datetime.strptime(shift_end, "%H:%M:%S").time()
                        except ValueError:
                            shift_end = datetime.strptime(shift_end, "%H:%M").time()
                    elif isinstance(shift_end, datetime):
                        shift_end = shift_end.time() 
                    
                    if shift_end:
                        shift_end = datetime.combine(getdate(logs[0]['time']), shift_end)
                    daily_summary = _calculate_employee_work_hours(logs, shift_end)
                    daily_summaries.append(daily_summary)

        return daily_summaries
    except Exception as e:
        frappe.log_error("Error in processing checkin data", str(e))
        return []


def _calculate_daily_work_hours_with_status(logs, emp_holidays, emp_leaves, date_str, employee_info):
    """Enhanced daily work hours calculation with comprehensive status"""
    try:
        if not logs:
            if not employee_info:
                return None
                
            check_date = getdate(date_str)
            if date_str in [str(d) for d in emp_holidays]:
                status = "Holiday"
            elif date_str in emp_leaves:
                status = "On Leave"
            elif check_date.weekday() == 6:  # Sunday
                status = "Off Day"
            else:
                status = "Absent"
                
            return {
                "employee": employee_info['name'],
                "department": employee_info['department'], 
                "reports_to": employee_info['reports_to'],
                "image": employee_info.get('image'),
                "date": date_str,
                "daily_working_hours": 0.0,
                "entry_time": None,
                "exit_time": None, 
                "status": status,
                "checkin_pairs": []
            }

        # If logs exist, employee was present
        work_summary = _calculate_employee_work_hours(logs)
        
        return {
            "employee": work_summary['employee'],
            "department": work_summary['department'],
            "reports_to": work_summary['reports_to'], 
            "image": work_summary.get('image'),
            "date": work_summary['date'],
            "daily_working_hours": work_summary['daily_working_hours'],
            "entry_time": work_summary['entry_time'],
            "exit_time": work_summary['exit_time'],
            "status": "Present",
            "checkin_pairs": work_summary['checkin_pairs']
        }
        
    except Exception as e:
        frappe.log_error("Error in calculating daily work hours with status", str(e))
        return None


def _calculate_effective_working_days(start_date, end_date, emp_holidays, emp_leaves, 
                                    base_working_days, checkin_dates, is_current_period=False):
    """Calculate effective working days using improved logic from attendance_app.py"""
    try:
        today_date = getdate(today())
        yesterday = today_date - timedelta(days=1)
        
        # For current periods, end calculation at yesterday for historical averages
        if is_current_period:
            actual_end_date = min(end_date, yesterday)
        else:
            actual_end_date = end_date
            
        if actual_end_date < start_date:
            return 0
        
        # Convert emp_leaves to date objects
        emp_leave_dates = [getdate(leave_str) for leave_str in emp_leaves]
        
        effective_working_days = 0
        holiday_work_days = 0
        
        current_date = start_date
        while current_date <= actual_end_date:
            # If employee checked in on this date, it's definitely a valid working day
            if str(current_date) in checkin_dates:
                if _is_working_day_for_employee(current_date, emp_holidays):
                    effective_working_days += 1
                else:
                    # Worked on holiday/weekend - count as bonus working day
                    holiday_work_days += 1
            else:
                # No check-in - only count regular weekdays that aren't holidays or leaves
                if current_date.weekday() < 5:  # Monday-Friday
                    is_holiday = current_date in emp_holidays
                    is_on_leave = current_date in emp_leave_dates
                    
                    if not is_holiday and not is_on_leave:
                        effective_working_days += 1
                        
            current_date += timedelta(days=1)
        
        # Total effective working days = regular working days + holiday work
        total_effective_days = effective_working_days + holiday_work_days
        
        return max(total_effective_days, 0)
        
    except Exception as e:
        frappe.log_error("Error in calculating effective working days", str(e))
        return 0


# === DATA PROCESSING FUNCTIONS ===

def _get_processed_checkin_data(from_date, to_date):
    """Process checkin data with holiday and leave integration"""
    try:
        if not from_date or not to_date:
            return [], {}, {}, {}
        
        # Get all data
        raw_checkin_data = _get_employee_data(from_date, to_date)
        if not raw_checkin_data:
            return [], {}, {}, {}
        
        # Get holidays, leaves, and shift info
        employee_holidays = _get_employee_holidays(from_date, to_date)
        employee_leaves = _get_leaves_for_period(from_date, to_date)
        employee_shift_info = _get_employee_shift_info()

        # Separate regular work from overtime work
        filtered_checkin_data, overtime_data = _filter_and_separate_checkins(raw_checkin_data, employee_holidays)

        # Process daily summaries for regular work
        daily_summaries = _sort_checkin_data(filtered_checkin_data)

        return daily_summaries, employee_holidays, employee_leaves, employee_shift_info
        
    except Exception as e:
        frappe.log_error("Error in processing checkin data", str(e))
        return [], {}, {}, {}


def _create_summary_with_effective_working_days(daily_records, period_type, start_date, end_date, 
                                               employee_holidays, employee_leaves, employee_shift_info, is_current_period=False):
    """Create period summary with effective working days calculation"""
    try:
        # Group daily records by employee
        employee_stats = defaultdict(lambda: {
            'total_work_hours': 0.0, 
            'days_worked': 0, 
            'department': None, 
            'reports_to': None,
            'image': None,
            'checkin_dates': set()
        })

        for record in daily_records:
            emp = employee_stats[record['employee']]
            emp['total_work_hours'] += record.get('daily_working_hours', 0.0)
            emp['days_worked'] += 1
            emp['checkin_dates'].add(record['date'])
            if not emp['department']: emp['department'] = record.get('department')
            if not emp['reports_to']: emp['reports_to'] = record.get('reports_to')
            if not emp['image']: emp['image'] = record.get('image')
        
        result = []
        for emp_name, stats in employee_stats.items():
            # Get employee specific data
            emp_holidays = employee_holidays.get(emp_name, [])
            emp_leaves = employee_leaves.get(emp_name, set())
            shift_info = employee_shift_info.get(emp_name, {'working_days': 5})
            base_working_days = shift_info['working_days']
            
            # Calculate effective working days
            effective_working_days = _calculate_effective_working_days(
                start_date, end_date, emp_holidays, emp_leaves, 
                base_working_days, stats['checkin_dates'], is_current_period
            )
            
            # Calculate average hours
            avg_hours = round(stats['total_work_hours'] / effective_working_days, 2) if effective_working_days > 0 else 0
            
            # Count holidays and leaves in period
            emp_leave_dates = [getdate(leave_str) for leave_str in emp_leaves]
            holidays_in_period = [h for h in emp_holidays if start_date <= h <= end_date]
            leaves_in_period = [l for l in emp_leave_dates if start_date <= l <= end_date]
            
            result.append({
                "employee": emp_name, 
                "average_work_hours": avg_hours, 
                "total_hours_worked": round(stats['total_work_hours'], 2),
                "total_days_worked": stats['days_worked'],
                "effective_working_days": effective_working_days,
                "holidays_in_period": len(holidays_in_period),
                "leaves_in_period": len(leaves_in_period)
            })
            
        return result
        
    except Exception as e:
        frappe.log_error("Error in creating summary with effective working days", str(e))
        return []


# === HIERARCHY MANAGEMENT FUNCTIONS ===

def _get_hierarchy_map():
    """Get manager to subordinates mapping"""
    try:
        employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "reports_to"])
        hierarchy = defaultdict(list)
        for emp in employees:
            if emp.reports_to:
                hierarchy[emp.reports_to].append(emp.name)
        return hierarchy
    except Exception as e:
        frappe.log_error("Error in hierarchy mapping", str(e))
        return defaultdict(list)


def _get_all_subordinates(manager_id, hierarchy_map):
    """Get all subordinates using breadth-first search"""
    if not manager_id or not hierarchy_map:
        return []

    all_subordinates = set()
    queue = hierarchy_map.get(manager_id, [])
    visited = set(queue)
    all_subordinates.update(queue)

    while queue:
        current = queue.pop(0)
        direct_reports = hierarchy_map.get(current, [])
        for report in direct_reports:
            if report not in visited:
                visited.add(report)
                all_subordinates.add(report)
                queue.append(report)
    
    return list(all_subordinates)


def _get_date_boundaries(target_date):
    """Calculate week/month boundaries with current vs past logic"""
    try:
        today_date = getdate(today())
        yesterday = today_date - timedelta(days=1)
        
        # Calculate month boundaries
        month_start = target_date.replace(day=1)
        _, days_in_month = calendar.monthrange(target_date.year, target_date.month)
        month_end = target_date.replace(day=days_in_month)
        
        # Calculate week boundaries (Monday to Friday)
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=4)  # Friday
        
        # Check if target_date is in current period
        is_current_month = (target_date.year == today_date.year and target_date.month == today_date.month)
        is_current_week = (week_start <= today_date <= week_end)
        
        return {
            "month_start": month_start,
            "month_end": month_end,
            "week_start": week_start,
            "week_end": week_end,
            "earliest_date": min(month_start, week_start),
            "latest_date": max(month_end, week_end),
            "is_current_month": is_current_month,
            "is_current_week": is_current_week
        }
        
    except Exception as e:
        frappe.log_error("Error in calculating date boundaries", str(e))
        return {}


def _build_employee_registry(employees):
    """Create employee registry structure"""
    return {
        emp.name: {
            'employee_info': {
                'name': emp.name, 
                'department': emp.department, 
                'reports_to': emp.reports_to,
                'image': emp.image
            },
            'daily_data': {}, 
            'weekly_summary': {}, 
            'monthly_summary': {}
        } for emp in employees
    }


def _add_to_registry(registry, data, data_key):
    """Add data to employee registry"""
    for record in data:
        emp_name = record.get('employee')
        if emp_name and emp_name in registry:
            clean_record = record.copy()
            # Remove redundant fields but keep "status" for daily_data
            for field in ['employee', 'department', 'reports_to', 'image']:
                clean_record.pop(field, None)
            registry[emp_name][data_key] = clean_record


def _process_data_by_periods(registry, all_data, boundaries, target_date, 
                           employee_holidays, employee_leaves, employee_shift_info):
    """Process and categorize data into daily/weekly/monthly periods"""
    try:
        if not all_data:
            all_data = []

        daily_data, weekly_data, monthly_data = [], [], []
        
        # Categorize data by periods
        for record in all_data:
            record_date = getdate(record['date'])
            if boundaries['month_start'] <= record_date <= boundaries['month_end']:
                monthly_data.append(record)
            if boundaries['week_start'] <= record_date <= boundaries['week_end']:
                weekly_data.append(record)
            if record_date == target_date:
                daily_data.append(record)

        # Process daily data with enhanced status
        if daily_data:
            for record in daily_data:
                emp_name = record['employee']
                emp_holidays = employee_holidays.get(emp_name, [])
                emp_leaves = employee_leaves.get(emp_name, set())
                date_str = format_datetime(target_date, 'yyyy-MM-dd')
                daily_summary = _calculate_daily_work_hours_with_status(
                    [r for r in daily_data if r['employee'] == emp_name],
                    emp_holidays,
                    emp_leaves,
                    date_str,
                    registry[emp_name]['employee_info']
                )
                if daily_summary:
                    for field in ['employee', 'department', 'reports_to', 'image']:
                        daily_summary.pop(field, None)
                    registry[emp_name]['daily_data'] = daily_summary

        # Process weekly summary
        if weekly_data:
            summary = _create_summary_with_effective_working_days(
                weekly_data, 'weekly', boundaries['week_start'], boundaries['week_end'], 
                employee_holidays, employee_leaves, employee_shift_info, boundaries['is_current_week']
            )
            _add_to_registry(registry, summary, 'weekly_summary')

        # Process monthly summary
        if monthly_data:
            summary = _create_summary_with_effective_working_days(
                monthly_data, 'monthly', boundaries['month_start'], boundaries['month_end'], 
                employee_holidays, employee_leaves, employee_shift_info, boundaries['is_current_month']
            )
            _add_to_registry(registry, summary, 'monthly_summary')

        # Fill missing employees with default status
        target_date_str = format_datetime(target_date, 'yyyy-MM-dd')
        for emp_name, emp_data in registry.items():
            emp_holidays = employee_holidays.get(emp_name, [])
            emp_leaves = employee_leaves.get(emp_name, set())
            shift_info = employee_shift_info.get(emp_name, {'working_days': 5})
            employee_info = emp_data['employee_info']

            # Fill daily data if missing
            if not emp_data['daily_data']:
                daily_summary = _calculate_daily_work_hours_with_status(
                    None, emp_holidays, emp_leaves, target_date_str, employee_info
                )
                if daily_summary:
                    for field in ['employee', 'department', 'reports_to', 'image']:
                        daily_summary.pop(field, None)
                    emp_data['daily_data'] = daily_summary

            # Fill weekly summary if missing
            if not emp_data['weekly_summary']:
                effective_working_days = _calculate_effective_working_days(
                    boundaries['week_start'], boundaries['week_end'], emp_holidays,
                    emp_leaves, shift_info['working_days'], set(), boundaries['is_current_week']
                )
                holidays_in_week = [h for h in emp_holidays if boundaries['week_start'] <= h <= boundaries['week_end']]
                emp_leave_dates = [getdate(leave_str) for leave_str in emp_leaves]
                leaves_in_week = [l for l in emp_leave_dates if boundaries['week_start'] <= l <= boundaries['week_end']]
                
                emp_data['weekly_summary'] = {
                    "average_work_hours": 0.0, 
                    "total_hours_worked": 0.0, 
                    "total_days_worked": 0,
                    "effective_working_days": effective_working_days,
                    "holidays_in_period": len(holidays_in_month),
                    "leaves_in_period": len(leaves_in_month)
                }

    except Exception as e:
        frappe.log_error("Error in processing data by periods", str(e))


def _create_hierarchy_response(registry, manager_id, subordinate_ids):
    """Structure final response with hierarchy"""
    manager_data = registry.get(manager_id, {})
    subordinates_data = {emp_id: data for emp_id, data in registry.items() if emp_id in subordinate_ids}
    
    return {
        "user_id": manager_id,
        "manager_data": manager_data,
        "subordinates_data": subordinates_data,
        "total_count": len(subordinates_data) + (1 if manager_data else 0)
    }


# === MAIN API ENDPOINTS ===

@frappe.whitelist()
def fetch_checkins(from_date=None, to_date=None, specific_date=None):
    """Enhanced API endpoint for fetching attendance data with advanced features"""
    try:
        # Input validation
        if from_date and not to_date: 
            frappe.throw("Please provide 'to_date' for date range.")
        if to_date and not from_date: 
            frappe.throw("Please provide 'from_date' for date range.")
        if (from_date or to_date) and specific_date: 
            frappe.throw("Provide either date range or specific date, not both.")
        
        if not any([from_date, to_date, specific_date]):
            specific_date = today()

        # Handle date range request
        if from_date and to_date:
            try:
                start_date, end_date = getdate(from_date), getdate(to_date)
                processed_data, employee_holidays, employee_leaves, employee_shift_info = _get_processed_checkin_data(start_date, end_date)
                
                if not processed_data:
                    return {"message": f"No check-in data found between {from_date} and {to_date}."}
                
                # Determine if current period for effective working days calculation
                today_date = getdate(today())
                is_current_period = end_date >= today_date
                
                days_diff = (end_date - start_date).days + 1
                period_type = 'weekly' if days_diff <= 7 else 'monthly'
                    
                return _create_summary_with_effective_working_days(
                    processed_data, period_type, start_date, end_date, 
                    employee_holidays, employee_leaves, employee_shift_info, is_current_period
                )
                
            except Exception as e:
                frappe.log_error("Error in date range processing", str(e))
                return {"error": "Failed to process date range request"}

        # Handle specific date request
        elif specific_date:
            try:
                target_date = getdate(specific_date)
                if target_date > getdate(today()):
                    return {"error": "Cannot fetch data for future date."}
                
                # Determine user hierarchy
                if frappe.session.user == 'Administrator':
                    manager_id = "Administrator"
                    all_employees = frappe.get_all("Employee", 
                        filters=[['status', '=', 'Active']], 
                        fields=["name", 'department', 'reports_to', 'image']
                    )
                    subordinate_ids = [emp.name for emp in all_employees if emp.name != manager_id]
                else:
                    manager_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
                    if not manager_id:
                        frappe.throw("User not linked to active employee record.")
                    
                    hierarchy_map = _get_hierarchy_map()
                    subordinate_ids = _get_all_subordinates(manager_id, hierarchy_map)
                    allowed_employees = set(subordinate_ids + [manager_id])
                    all_employees = frappe.get_all("Employee", 
                        filters={"name": ["in", list(allowed_employees)]},
                        fields=["name", "department", "reports_to", 'image']
                    )

                # Build registry and process data
                registry = _build_employee_registry(all_employees)
                boundaries = _get_date_boundaries(target_date)

                all_data, employee_holidays, employee_leaves, employee_shift_info = _get_processed_checkin_data(
                    boundaries['earliest_date'], boundaries['latest_date']
                )
                _process_data_by_periods(
                    registry, all_data, boundaries, target_date, 
                    employee_holidays, employee_leaves, employee_shift_info
                )

                return _create_hierarchy_response(registry, manager_id, subordinate_ids)
                
            except Exception as e:
                frappe.log_error("Error in specific date processing", str(e))
                return {"error": "Failed to process request"}

    except Exception as e:
        frappe.log_error("Error in main function", str(e))
        return {"error": "System error occurred."}


@frappe.whitelist(allow_guest=True)
def get_employee_details(user_id, select_date=None):
    """Individual employee attendance API with enhanced calculations"""
    try:
        # Validate user
        if not frappe.db.exists("User", user_id):
            return {"success": False, "message": f"User {user_id} not found"}

        employee = frappe.db.get_value(
            "Employee",
            {"user_id": user_id, "status": "Active"},
            ["name", "employee_name", "department", "designation"],
            as_dict=True
        )

        if not employee:
            return {"success": False, "message": f"No active Employee linked with user {user_id}"}

        target_date = getdate(select_date) if select_date else getdate(today())
        yesterday = target_date - timedelta(days=1)
        emp_name = employee['name']

        # Define period boundaries - ending at yesterday for historical averages
        month_start = target_date.replace(day=1)
        week_start = target_date - timedelta(days=target_date.weekday())
        
        week_end = yesterday
        month_end = yesterday
        earliest_date = min(month_start, week_start)

        # Get all required data
        all_data, employee_holidays, employee_leaves, employee_shift_info = _get_processed_checkin_data(
            earliest_date, target_date
        )
        
        # Filter for this employee
        emp_holidays = employee_holidays.get(emp_name, [])
        emp_leaves = employee_leaves.get(emp_name, set())
        shift_info = employee_shift_info.get(emp_name, {'working_days': 5})

        # Find today's data
        target_date_str = format_datetime(target_date, 'yyyy-MM-dd')
        daily_data = next((s for s in all_data if s['employee'] == emp_name and s['date'] == target_date_str), None)
        
        if not daily_data:
            # No check-in data for target date - determine status
            check_date = target_date
            if target_date_str in [str(d) for d in emp_holidays]:
                status = "Holiday"
            elif target_date_str in emp_leaves:
                status = "On Leave"
            elif check_date.weekday() == 6:  # Sunday
                status = "Off Day"
            else:
                status = "Absent"
            
            daily_data = {
                "date": target_date_str,
                "daily_working_hours": 0.0,
                "entry_time": None,
                "exit_time": None,
                "checkin_pairs": [],
                "status": status
            }
        else:
            # Clean up daily data for response
            daily_data.pop("employee", None)
            daily_data.pop("department", None)
            daily_data.pop("reports_to", None)
            daily_data.pop("image", None)

        # Filter historical data for averages
        historical_data = [s for s in all_data if s['employee'] == emp_name and getdate(s['date']) <= yesterday]
        
        # Calculate weekly and monthly summaries
        weekly_data = [s for s in historical_data if week_start <= getdate(s['date']) <= week_end]
        monthly_data = [s for s in historical_data if month_start <= getdate(s['date']) <= month_end]
        
        # Calculate effective working days and summaries
        weekly_checkin_dates = {s['date'] for s in weekly_data}
        monthly_checkin_dates = {s['date'] for s in monthly_data}
        
        weekly_effective_days = _calculate_effective_working_days(
            week_start, week_end, emp_holidays, emp_leaves, 
            shift_info['working_days'], weekly_checkin_dates, is_current_period=True
        )
        
        monthly_effective_days = _calculate_effective_working_days(
            month_start, month_end, emp_holidays, emp_leaves, 
            shift_info['working_days'], monthly_checkin_dates, is_current_period=True
        )
        
        weekly_hours = sum(s.get('daily_working_hours', 0.0) for s in weekly_data)
        monthly_hours = sum(s.get('daily_working_hours', 0.0) for s in monthly_data)
        
        weekly_avg = round(weekly_hours / weekly_effective_days, 2) if weekly_effective_days > 0 else 0.0
        monthly_avg = round(monthly_hours / monthly_effective_days, 2) if monthly_effective_days > 0 else 0.0
        
        # Count holidays and leaves in periods
        weekly_holidays = [h for h in emp_holidays if week_start <= h <= week_end]
        monthly_holidays = [h for h in emp_holidays if month_start <= h <= month_end]
        
        emp_leave_dates = [getdate(leave_str) for leave_str in emp_leaves]
        weekly_leaves = [l for l in emp_leave_dates if week_start <= l <= week_end]
        monthly_leaves = [l for l in emp_leave_dates if month_start <= l <= month_end]

        return {
            "success": True,
            "employee_details": {
                "name": employee['employee_name'],
                "department": employee['department'],
                "designation": employee['designation']
            },
            "selected_date_data": daily_data,
            "weekly_summary": {
                "total_hours_worked": round(weekly_hours, 2),
                "average_work_hours": weekly_avg,
                "days_worked": len(weekly_data),
                "effective_working_days": weekly_effective_days,
                "holidays_in_period": len(weekly_holidays),
                "leaves_in_period": len(weekly_leaves)
            },
            "monthly_summary": {
                "total_hours_worked": round(monthly_hours, 2),
                "average_work_hours": monthly_avg,
                "days_worked": len(monthly_data),
                "effective_working_days": monthly_effective_days,
                "holidays_in_period": len(monthly_holidays),
                "leaves_in_period": len(monthly_leaves)
            }
        }

    except Exception as e:
        frappe.log_error("Error in get_employee_details", str(e))
        return {"success": False, "message": "System error occurred"}": effective_working_days,
                    "holidays_in_period": len(holidays_in_week),
                    "leaves_in_period": len(leaves_in_week)
                }

            # Fill monthly summary if missing
            if not emp_data['monthly_summary']:
                effective_working_days = _calculate_effective_working_days(
                    boundaries['month_start'], boundaries['month_end'], emp_holidays,
                    emp_leaves, shift_info['working_days'], set(), boundaries['is_current_month']
                )
                holidays_in_month = [h for h in emp_holidays if boundaries['month_start'] <= h <= boundaries['month_end']]
                emp_leave_dates = [getdate(leave_str) for leave_str in emp_leaves]
                leaves_in_month = [l for l in emp_leave_dates if boundaries['month_start'] <= l <= boundaries['month_end']]
                
                emp_data['monthly_summary'] = {
                    "average_work_hours": 0.0, 
                    "total_hours_worked": 0.0, 
                    "total_days_worked": 0,
                    "effective_working_days