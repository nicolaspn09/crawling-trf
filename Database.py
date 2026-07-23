import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv, find_dotenv

# Obtém o caminho do diretório onde o script está localizado
script_dir = os.path.dirname(os.path.abspath(__file__))
# Procura o .env a partir do diretório do script
dotenv_path = find_dotenv(os.path.join(script_dir, '.env'))

load_dotenv(dotenv_path)

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
            
            # Auto-Migration: garante que as colunas novas existam no banco sem dar erro
            try:
                self.cursor.execute("ALTER TABLE processos ADD COLUMN IF NOT EXISTS link_sentenca TEXT;")
                self.cursor.execute("ALTER TABLE processos ADD COLUMN IF NOT EXISTS assunto TEXT;")
                self.cursor.execute("ALTER TABLE processos ADD COLUMN IF NOT EXISTS tem_tese_322 BOOLEAN DEFAULT FALSE;")
                self.cursor.execute("ALTER TABLE processos ADD COLUMN IF NOT EXISTS tem_tese_emendas BOOLEAN DEFAULT FALSE;")
                self.cursor.execute("ALTER TABLE processos ADD COLUMN IF NOT EXISTS tem_tese_buraco_negro BOOLEAN DEFAULT FALSE;")
                
                # Cria a tabela de controle de atualizações
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS controle_atualizacoes (
                        id SERIAL PRIMARY KEY,
                        data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ultimo_sha VARCHAR(40) NOT NULL,
                        resumo_enviado TEXT
                    );
                """)
            except Exception as ex:
                print(f"[Aviso DB] Não foi possível verificar/criar colunas ou tabelas automaticamente: {ex}")
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def obter_ultimo_sha_atualizacao(self):
        """Busca o último commit SHA que foi processado e resumido no banco."""
        try:
            query = "SELECT ultimo_sha FROM controle_atualizacoes ORDER BY data_envio DESC LIMIT 1;"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            return result['ultimo_sha'] if result else None
        except Exception as e:
            print(f"[Aviso DB] Erro ao obter último SHA de atualização: {e}")
            return None

    def inserir_log_atualizacao(self, sha, resumo):
        """Grava um registro de resumo enviado no banco de dados."""
        try:
            query = """
                INSERT INTO controle_atualizacoes (ultimo_sha, resumo_enviado)
                VALUES (%s, %s)
                RETURNING id;
            """
            self.cursor.execute(query, (sha, resumo))
            result = self.cursor.fetchone()
            return result['id'] if result else None
        except Exception as e:
            print(f"[Erro DB] Falha ao gravar log de atualização: {e}")
            return None

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

    def inserir_processo(self, cliente_id, numero_processo, tribunal='TRF4', link_processo=None, polo_passivo=None, 
                         tem_tese_concomitante=False, status_merito=None, link_sentenca=None, assunto=None,
                         tem_tese_322=False, tem_tese_emendas=False, tem_tese_buraco_negro=False):
        query = """
            INSERT INTO processos 
            (cliente_id, numero_processo, tribunal, link_processo, polo_passivo, 
             tem_tese_concomitante, tem_tese_322, tem_tese_emendas, tem_tese_buraco_negro, 
             status_merito, link_sentenca, assunto)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_processo) DO UPDATE SET
                status_merito = EXCLUDED.status_merito,
                tem_tese_concomitante = EXCLUDED.tem_tese_concomitante,
                tem_tese_322 = EXCLUDED.tem_tese_322,
                tem_tese_emendas = EXCLUDED.tem_tese_emendas,
                tem_tese_buraco_negro = EXCLUDED.tem_tese_buraco_negro,
                polo_passivo = EXCLUDED.polo_passivo,
                link_sentenca = EXCLUDED.link_sentenca,
                assunto = EXCLUDED.assunto
            RETURNING id;
        """
        self.cursor.execute(query, (cliente_id, numero_processo, tribunal, link_processo, polo_passivo, 
                                    tem_tese_concomitante, tem_tese_322, tem_tese_emendas, tem_tese_buraco_negro, 
                                    status_merito, link_sentenca, assunto))
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
