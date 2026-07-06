import sys
import os

# Adiciona a pasta pai ao sys.path para importar Database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Database import Database

try:
    db = Database()
    print("Conexão bem sucedida!")
    
    # Lista tabelas
    db.cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'lodettisilveira' OR table_schema = 'public';
    """)
    tables = db.cursor.fetchall()
    print("Tabelas encontradas:", tables)
    
    # Se existirem, tenta ver as colunas
    for t in tables:
        table_name = t['table_name']
        db.cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}';")
        cols = db.cursor.fetchall()
        print(f"Colunas de {table_name}:", cols)
        
except Exception as e:
    import traceback
    print("Erro:")
    traceback.print_exc()
