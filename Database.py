import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                database=os.getenv("DB_NAME", "NcTechnology"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                port=os.getenv("DB_PORT", "5432"),
                options="-c search_path=lodettisilveira"
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def obter_ou_criar_cliente(self, cpf, nome=None, telefone=None, email=None):
        """Busca o cliente pelo CPF. Se não existir, cria e retorna o ID."""
        query = """
            INSERT INTO clientes (cpf, nome, telefone, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (cpf) DO UPDATE SET
                nome = COALESCE(EXCLUDED.nome, clientes.nome),
                telefone = COALESCE(EXCLUDED.telefone, clientes.telefone),
                email = COALESCE(EXCLUDED.email, clientes.email)
            RETURNING id;
        """
        self.cursor.execute(query, (cpf, nome, telefone, email))
        result = self.cursor.fetchone()
        return result['id'] if result else None

    def inserir_processo(self, cliente_id, numero_processo, tribunal='TRF4', link_processo=None, polo_passivo=None, tem_tese_concomitante=False, status_merito=None):
        query = """
            INSERT INTO processos 
            (cliente_id, numero_processo, tribunal, link_processo, polo_passivo, tem_tese_concomitante, status_merito)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_processo) DO UPDATE SET
                status_merito = EXCLUDED.status_merito,
                tem_tese_concomitante = EXCLUDED.tem_tese_concomitante,
                polo_passivo = EXCLUDED.polo_passivo
            RETURNING id;
        """
        self.cursor.execute(query, (cliente_id, numero_processo, tribunal, link_processo, polo_passivo, tem_tese_concomitante, status_merito))
        result = self.cursor.fetchone()
        return result['id'] if result else None

    def inserir_oportunidade(self, cliente_id, resultado_rpa, motivo_resultado, fase_funil='Nova Oportunidade'):
        query = """
            INSERT INTO oportunidades (cliente_id, resultado_rpa, motivo_resultado, fase_funil)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        self.cursor.execute(query, (cliente_id, resultado_rpa, motivo_resultado, fase_funil))
        result = self.cursor.fetchone()
        return result['id'] if result else None

    def obter_clientes_pendentes_de_analise(self):
        """Retorna CPFs que ainda não têm registro de oportunidade gerado pelo RPA."""
        query = """
            SELECT c.id, c.cpf 
            FROM clientes c
            LEFT JOIN oportunidades o ON c.id = o.cliente_id
            WHERE o.id IS NULL
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def fechar_conexao(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
