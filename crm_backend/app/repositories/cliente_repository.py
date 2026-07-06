from psycopg2.extras import RealDictCursor

class ClienteRepository:
    def __init__(self, db_connection):
        self.conn = db_connection

    def get_by_cpf(self, cpf: str):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM clientes WHERE cpf = %s;", (cpf,))
            return cursor.fetchone()

    def create_or_update(self, cpf: str, nome: str = None, telefone: str = None, email: str = None):
        query = """
            INSERT INTO clientes (cpf, nome, telefone, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (cpf) DO UPDATE SET
                nome = COALESCE(EXCLUDED.nome, clientes.nome),
                telefone = COALESCE(EXCLUDED.telefone, clientes.telefone),
                email = COALESCE(EXCLUDED.email, clientes.email)
            RETURNING id;
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (cpf, nome, telefone, email))
            result = cursor.fetchone()
            return result['id'] if result else None
