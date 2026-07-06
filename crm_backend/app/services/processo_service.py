from app.repositories.processo_repository import ProcessoRepository

class ProcessoService:
    def __init__(self, processo_repository: ProcessoRepository):
        self.repository = processo_repository

    def get_all_processos(self):
        return self.repository.get_all()
