import sys
import os

# Adiciona a pasta crm_backend ao sys.path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/crm_backend')

from app.core.database import get_db_connection
from app.repositories.processo_repository import ProcessoRepository

try:
    conn = get_db_connection()
    repo = ProcessoRepository(conn)
    processos = repo.get_all()
    print("Processos retornados (primeiros 2):", processos[:2])
    print("Tipo de uma linha:", type(processos[0]))
    
    # Testa serializar pra JSON
    import json
    print(json.dumps(processos[:2], default=str))

except Exception as e:
    import traceback
    print("Erro:")
    traceback.print_exc()
