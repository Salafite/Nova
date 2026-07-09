from unittest.mock import patch, MagicMock
from packages.mcp.servers import hr_mcp
from packages.mcp.servers.hr_mcp import register_tools


def _patch(name):
    return patch.object(hr_mcp, name, MagicMock())


class TestHrMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_employees(self):
        with _patch("_emp_svc"):
            hr_mcp._emp_svc.list.return_value = [{"id": 1, "full_name": "John"}]
            assert hr_mcp._list_employees() == [{"id": 1, "full_name": "John"}]

    def test_get_employee(self):
        with _patch("_emp_svc"):
            hr_mcp._emp_svc.get.return_value = {"id": 1, "full_name": "John"}
            assert hr_mcp._get_employee(1)["full_name"] == "John"

    def test_list_departments(self):
        with _patch("_dept_svc"):
            hr_mcp._dept_svc.list.return_value = [{"department_name": "IT"}]
            assert hr_mcp._list_depts()[0]["department_name"] == "IT"

    def test_list_attendance(self):
        with _patch("_att_svc"):
            hr_mcp._att_svc.list.return_value = [{"status": "Present"}]
            assert hr_mcp._list_attendance()[0]["status"] == "Present"

    def test_list_leaves(self):
        with _patch("_leave_svc"):
            hr_mcp._leave_svc.list.return_value = [{"status": "Approved"}]
            assert hr_mcp._list_leaves()[0]["status"] == "Approved"

    def test_list_payroll(self):
        with _patch("_payroll_svc"):
            hr_mcp._payroll_svc.list.return_value = [{"net_pay": 5000}]
            assert hr_mcp._list_payroll()[0]["net_pay"] == 5000

    def test_list_shifts(self):
        with _patch("_shift_svc"):
            hr_mcp._shift_svc.list.return_value = [{"shift_name": "Morning"}]
            assert hr_mcp._list_shifts()[0]["shift_name"] == "Morning"

    def test_list_jobs(self):
        with _patch("_job_svc"):
            hr_mcp._job_svc.list.return_value = [{"job_title": "Engineer"}]
            assert hr_mcp._list_jobs()[0]["job_title"] == "Engineer"

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_employees" in names
        assert "get_employee" in names
        assert "list_departments" in names
        assert "list_attendance" in names
        assert "list_leave_requests" in names
        assert "list_payroll_entries" in names
        assert "list_shifts" in names
        assert "list_job_openings" in names
