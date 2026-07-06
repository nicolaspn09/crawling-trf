from fastapi import APIRouter, Depends, HTTPException
from app.services.dashboard_service import DashboardService
from app.repositories.dashboard_repository import DashboardRepository
from app.core.database import get_db_connection

router = APIRouter()

def get_dashboard_service(db_conn = Depends(get_db_connection)) -> DashboardService:
    repo = DashboardRepository(db_conn)
    return DashboardService(repo)

@router.get("/resumo")
def get_resumo(service: DashboardService = Depends(get_dashboard_service)):
    try:
        resumo = service.get_resumo_dashboard()
        return resumo
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar resumo do dashboard: {str(e)}")
