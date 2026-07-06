from psycopg2.extras import RealDictCursor

class DashboardRepository:
    def __init__(self, db_connection):
        self.conn = db_connection

    def get_resumo(self):
        query = """
            SELECT 
                (SELECT COUNT(*) FROM clientes) as total_clientes,
                (SELECT COUNT(*) FROM processos) as total_processos,
                (SELECT COUNT(*) FROM oportunidades) as total_oportunidades,
                (SELECT COUNT(*) FROM processos WHERE tem_tese_concomitante = True) as processos_com_tese
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchone()
