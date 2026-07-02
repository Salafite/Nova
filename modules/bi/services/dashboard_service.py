from ..repositories.dashboard_repo import get_stats, get_recent_activity


def get_dashboard_summary():
    stats = get_stats()
    recent = get_recent_activity()
    return {'stats': stats, 'recentActivity': recent}
