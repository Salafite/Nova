from modules.core.services.base import CrudService
from modules.core.repositories.base import CrudRepository
from packages.mcp.registry import register_tool
from packages.mcp.types import Tool


_emp_repo = CrudRepository('T0030', business_columns=['id', 'employee_code', 'full_name', 'email', 'phone', 'employment_status', 'department_id', 'designation_id', 'manager_id', 'is_active'])
_emp_svc = CrudService(_emp_repo)

_dept_repo = CrudRepository('T0028', business_columns=['id', 'department_code', 'department_name', 'parent_id', 'manager_id', 'is_active'])
_dept_svc = CrudService(_dept_repo)

_att_repo = CrudRepository('T0034', business_columns=['id', 'employee_id', 'date', 'shift_id', 'clock_in', 'clock_out', 'status', 'is_active'])
_att_svc = CrudService(_att_repo)

_leave_repo = CrudRepository('T0036', business_columns=['id', 'employee_id', 'leave_type_id', 'start_date', 'end_date', 'days', 'reason', 'status', 'approved_by'])
_leave_svc = CrudService(_leave_repo)

_payroll_repo = CrudRepository('T0038', business_columns=['id', 'employee_id', 'payroll_period_id', 'basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances', 'overtime', 'deductions', 'tax', 'gross_pay', 'net_pay', 'status', 'payment_date', 'notes'])
_payroll_svc = CrudService(_payroll_repo)

_shift_repo = CrudRepository('T0033', business_columns=['id', 'shift_code', 'shift_name', 'start_time', 'end_time', 'grace_minutes', 'is_active'])
_shift_svc = CrudService(_shift_repo)

_job_repo = CrudRepository('T0039', business_columns=['id', 'job_code', 'job_title', 'department_id', 'designation_id', 'openings', 'status', 'posted_date', 'closing_date'])
_job_svc = CrudService(_job_repo)


def register_tools():
    register_tool(Tool(name="list_employees", description="List employees", input_schema={
        "type": "object", "properties": {
            "department_id": {"type": "integer"}, "employment_status": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }), _list_employees)
    register_tool(Tool(name="get_employee", description="Get employee by ID", input_schema={
        "type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"],
    }), _get_employee)
    register_tool(Tool(name="list_departments", description="List departments", input_schema={
        "type": "object", "properties": {},
    }), _list_depts)
    register_tool(Tool(name="list_attendance", description="List attendance records", input_schema={
        "type": "object", "properties": {
            "employee_id": {"type": "integer"}, "date_from": {"type": "string"},
            "date_to": {"type": "string"}, "limit": {"type": "integer"},
        },
    }), _list_attendance)
    register_tool(Tool(name="list_leave_requests", description="List leave requests", input_schema={
        "type": "object", "properties": {
            "employee_id": {"type": "integer"}, "status": {"type": "string"},
            "limit": {"type": "integer"},
        },
    }), _list_leaves)
    register_tool(Tool(name="list_payroll_entries", description="List payroll entries", input_schema={
        "type": "object", "properties": {
            "employee_id": {"type": "integer"}, "payroll_period_id": {"type": "integer"},
            "status": {"type": "string"}, "limit": {"type": "integer"},
        },
    }), _list_payroll)
    register_tool(Tool(name="list_shifts", description="List work shifts", input_schema={
        "type": "object", "properties": {},
    }), _list_shifts)
    register_tool(Tool(name="list_job_openings", description="List job openings", input_schema={
        "type": "object", "properties": {
            "status": {"type": "string"}, "department_id": {"type": "integer"},
        },
    }), _list_jobs)


def _list_employees(department_id: int = None, employment_status: str = None, limit: int = 50):
    filters = {}
    if department_id: filters["department_id"] = department_id
    if employment_status: filters["employment_status"] = employment_status
    return _emp_svc.list(filters=filters or None, limit=limit)

def _get_employee(id: int):
    return _emp_svc.get(id)

def _list_depts():
    return _dept_svc.list()

def _list_attendance(employee_id: int = None, date_from: str = None, date_to: str = None, limit: int = 50):
    filters = {}
    if employee_id: filters["employee_id"] = employee_id
    return _att_svc.list(filters=filters or None, limit=limit)

def _list_leaves(employee_id: int = None, status: str = None, limit: int = 50):
    filters = {}
    if employee_id: filters["employee_id"] = employee_id
    if status: filters["status"] = status
    return _leave_svc.list(filters=filters or None, limit=limit)

def _list_payroll(employee_id: int = None, payroll_period_id: int = None, status: str = None, limit: int = 50):
    filters = {}
    if employee_id: filters["employee_id"] = employee_id
    if payroll_period_id: filters["payroll_period_id"] = payroll_period_id
    if status: filters["status"] = status
    return _payroll_svc.list(filters=filters or None, limit=limit)

def _list_shifts():
    return _shift_svc.list()

def _list_jobs(status: str = None, department_id: int = None):
    filters = {}
    if status: filters["status"] = status
    if department_id: filters["department_id"] = department_id
    return _job_svc.list(filters=filters or None)


def main():
    register_tools()
    from packages.mcp.server import McpServer
    from packages.mcp.stdio import run_stdio
    run_stdio(McpServer(name="hr-mcp", version="1.0"))

if __name__ == "__main__":
    main()
