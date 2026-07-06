from typing import Optional
from pydantic import BaseModel

class ClienteBase(BaseModel):
    cpf: str
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(ClienteBase):
    id: int

class ProcessoBase(BaseModel):
    numero_processo: str
    tribunal: Optional[str] = 'TRF4'
    link_processo: Optional[str] = None
    polo_passivo: Optional[str] = None
    tem_tese_concomitante: Optional[bool] = False
    status_merito: Optional[str] = None

class ProcessoCreate(ProcessoBase):
    cliente_id: int

class ProcessoResponse(ProcessoBase):
    id: int
    cliente_id: int

class OportunidadeBase(BaseModel):
    resultado_rpa: Optional[str] = None
    motivo_resultado: Optional[str] = None
    fase_funil: Optional[str] = 'Nova Oportunidade'

class OportunidadeCreate(OportunidadeBase):
    cliente_id: int

class OportunidadeResponse(OportunidadeBase):
    id: int
    cliente_id: int
