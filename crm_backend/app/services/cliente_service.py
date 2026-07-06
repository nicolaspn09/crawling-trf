from app.repositories.cliente_repository import ClienteRepository
from app.models.domain import ClienteCreate

class ClienteService:
    def __init__(self, cliente_repository: ClienteRepository):
        self.repository = cliente_repository

    def create_or_update_cliente(self, cliente: ClienteCreate) -> int:
        # Aqui poderia ter validações de negócio, como validar formato do CPF
        cliente_id = self.repository.create_or_update(
            cpf=cliente.cpf,
            nome=cliente.nome,
            telefone=cliente.telefone,
            email=cliente.email
        )
        return cliente_id

    def get_cliente_by_cpf(self, cpf: str):
        return self.repository.get_by_cpf(cpf)
