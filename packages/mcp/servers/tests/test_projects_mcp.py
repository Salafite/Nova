from unittest.mock import patch, MagicMock
from packages.mcp.servers import projects_mcp
from packages.mcp.servers.projects_mcp import register_tools


def _patch(name):
    return patch.object(projects_mcp, name, MagicMock())


class TestProjectsMcp:
    def setup_method(self):
        from packages.mcp import registry
        registry._tools.clear()

    def test_list_projects(self):
        with _patch("_proj_svc"):
            projects_mcp._proj_svc.list.return_value = [{"project_name": "ERP"}]
            assert projects_mcp._list_projects()[0]["project_name"] == "ERP"

    def test_get_project(self):
        with _patch("_proj_svc"):
            projects_mcp._proj_svc.get.return_value = {"id": 1, "project_name": "ERP"}
            assert projects_mcp._get_project(1)["project_name"] == "ERP"

    def test_list_tasks(self):
        with _patch("_task_svc"):
            projects_mcp._task_svc.list.return_value = [{"task_name": "Design"}]
            assert projects_mcp._list_tasks()[0]["task_name"] == "Design"

    def test_list_milestones(self):
        with _patch("_milestone_svc"):
            projects_mcp._milestone_svc.list.return_value = [{"hours": 10}]
            assert projects_mcp._list_milestones()[0]["hours"] == 10

    def test_register_tools(self):
        register_tools()
        from packages.mcp.registry import get_tools
        names = [t.name for t in get_tools()]
        assert "list_projects" in names
        assert "get_project" in names
        assert "list_tasks" in names
        assert "list_milestones" in names
