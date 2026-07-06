import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings

def get_db_connection():
    """
    Dependency injection para obter conexão com o banco de dados.
    Utiliza as configurações do core/config.py
    """
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        port=settings.DB_PORT,
        options=f"-c search_path={settings.DB_SCHEMA}"
    )
    conn.autocommit = True
    return conn
