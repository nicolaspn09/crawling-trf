from fastapi import APIRouter, Depends, HTTPException
from app.services.processo_service import ProcessoService
from app.repositories.processo_repository import ProcessoRepository
from app.core.database import get_db_connection

router = APIRouter()

def get_processo_service(db_conn = Depends(get_db_connection)) -> ProcessoService:
    repo = ProcessoRepository(db_conn)
    return ProcessoService(repo)

@router.get("/")
def get_processos(service: ProcessoService = Depends(get_processo_service)):
    try:
        processos = service.get_all_processos()
        return processos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar processos no banco de dados: {str(e)}")
