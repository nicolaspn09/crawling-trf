from psycopg2.extras import RealDictCursor

class ProcessoRepository:
    def __init__(self, db_connection):
        self.conn = db_connection

    def get_all(self):
        query = """
            SELECT p.numero_processo, p.tribunal, p.status_merito, c.cpf, c.nome
            FROM processos p
            INNER JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.id DESC
            LIMIT 100;
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchall()
