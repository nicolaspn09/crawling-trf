from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.models.domain import ClienteCreate, ClienteResponse
from app.services.cliente_service import ClienteService
from app.repositories.cliente_repository import ClienteRepository
from app.core.database import get_db_connection

router = APIRouter()

def get_cliente_service(db_conn = Depends(get_db_connection)) -> ClienteService:
    repo = ClienteRepository(db_conn)
    return ClienteService(repo)

@router.post("/", response_model=dict, status_code=201)
def create_or_update_cliente(
    cliente: ClienteCreate,
    service: ClienteService = Depends(get_cliente_service)
):
    try:
        cliente_id = service.create_or_update_cliente(cliente)
        return {"id": cliente_id, "message": "Cliente criado ou atualizado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{cpf}")
def get_cliente(
    cpf: str,
    service: ClienteService = Depends(get_cliente_service)
):
    cliente = service.get_cliente_by_cpf(cpf)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente
