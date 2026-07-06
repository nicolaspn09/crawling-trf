from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import clientes, processos, dashboard
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API para o CRM Lodetti Silveira com arquitetura limpa (SRP)"
)

# Configuração de CORS para permitir o frontend interagir com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrando os roteadores
app.include_router(clientes.router, prefix="/api/v1/clientes", tags=["clientes"])
app.include_router(processos.router, prefix="/api/v1/processos", tags=["processos"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])

from fastapi.responses import FileResponse
import os

@app.get("/")
def read_root():
    # Caminho até o seu HTML na pasta original
    html_path = r"C:\Users\nicol\OneDrive\Cursos online\Treinamento Python - Hashtag\Códigos\Nexus Systems\Lodetti Silveira\Reunioes\2026-06-17\teste.html"
    
    # Se o arquivo existir, retorna a tela; se não, retorna a mensagem
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"message": f"Bem-vindo à API do {settings.PROJECT_NAME}"}
