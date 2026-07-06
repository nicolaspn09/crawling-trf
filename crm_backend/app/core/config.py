import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Carrega o arquivo .env da pasta principal do projeto
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
load_dotenv(env_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lodetti Silveira CRM API"
    VERSION: str = "1.0.0"
    
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_NAME: str = os.getenv("DB_NAME", "NcTechnology")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_SCHEMA: str = "lodettisilveira"

settings = Settings()
