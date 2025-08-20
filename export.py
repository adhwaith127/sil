import io
import pandas as pd
import frappe
from frappe import _
from collections import defaultdict
from frappe.utils import format_datetime, time_diff_in_hours

@frappe.whitelist(allow_guest=True)
def get_employee_checkin(from_date, to_date, employee_name=None, department=None):
    if not from_date or not to_date:
        frappe.throw("Provide date range")

    employees = []
    if department and not employee_name:
        employees = frappe.get_all("Employee", filters={"department": department}, pluck="name")
        if not employees:
            return []

    conditions = "ec.time BETWEEN %s AND %s"
    values = [from_date, to_date]

    if employee_name:
        conditions += " AND ec.employee = %s"
        values.append(employee_name)
    elif employees:
        placeholders = ', '.join(['%s'] * len(employees))
        conditions += f" AND ec.employee IN ({placeholders})"
        values.extend(employees)

    checkins = frappe.db.sql(f"""
        SELECT 
            ec.employee,
            ec.time,
            ec.log_type,
            e.department,
            e.custom_team
        FROM 
            `tabEmployee Checkin` ec
        LEFT JOIN 
            `tabEmployee` e ON ec.employee = e.name
        WHERE
            {conditions}
        ORDER BY
            ec.employee, ec.time
    """, values, as_dict=True)

    grouped_data = defaultdict(lambda: defaultdict(list))
    for entry in checkins:
        date_str = format_datetime(entry['time'], 'yyyy-MM-dd')
        grouped_data[entry['employee']][date_str].append(entry)

    result = []
    for emp, days in grouped_data.items():
        for date, logs in days.items():
            logs = sorted(logs, key=lambda x: x['time'])
            total_hours = 0.0
            flat_details = {}
            idx = 1
            i = 0
            while i < len(logs) - 1:
                current = logs[i]
                next_log = logs[i + 1]
                if current['log_type'] == 'IN' and next_log['log_type'] == 'OUT':
                    duration = time_diff_in_hours(next_log['time'], current['time'])
                    total_hours += duration
                    flat_details[f'check_in_{idx}'] = format_datetime(current['time'], 'hh:mm a')
                    flat_details[f'check_out_{idx}'] = format_datetime(next_log['time'], 'hh:mm a')
                    idx += 1
                    i += 2
                else:
                    i += 1

            first_time = logs[0]['time']
            last_time = logs[-1]['time']
            result.append({
                'employee': emp,
                'department': logs[0].get('department'),
                'team': logs[0].get('custom_team'),
                'date': date,
                'first_checkin': format_datetime(first_time, 'hh:mm a'),
                'last_checkout': format_datetime(last_time, 'hh:mm a'),
                'working_hours': round(total_hours, 2),
                **flat_details
            })

    return result



@frappe.whitelist(allow_guest=True)
def download_excel(from_date, to_date, employee_name=None, department=None):
    # Get attendance data
    response = get_employee_checkin(from_date, to_date, employee_name, department)

    # Prepare rows for Excel (each item is already flat)
    rows = []
    for data in response:
        rows.append(data)

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')

    output.seek(0)

    # Setup file download response
    frappe.response['filename'] = "attendance_export.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'
    frappe.response['headers'] = {
        'Content-Disposition': 'attachment; filename="attendance_export.xlsx"',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

@frappe.whitelist(allow_guest=True)
def get_all_employees_and_department():
    return frappe.get_all(
        'Employee',
        fields=['name', 'department'],
        filters={"status": "Active"},
    )

