from app.repositories.dashboard_repository import DashboardRepository

class DashboardService:
    def __init__(self, dashboard_repository: DashboardRepository):
        self.repository = dashboard_repository

    def get_resumo_dashboard(self):
        return self.repository.get_resumo()
