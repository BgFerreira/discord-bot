import sqlite3
import os
from typing import Optional

class DatabaseManager:
    """
    Gerencia todas as conexões e operações com o banco de dados SQLite.
    """

    def __init__(self, db_path):
        """
        Inicializa o gerenciador com o caminho para o arquivo do banco.
        """

        self.db_path = db_path
        print(f"SYSTEM: Database Manager has been started. Path: {db_path}")
    
    def _get_connection(self):
        """
        [FUNÇÃO HELPER] Cria e retorna uma conexão com o banco de dados.
        """

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """
        Cria as tabelas necessárias no banco se elas ainda não existirem.
        Deve ser chamado na inicialização do bot.
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS moderators (user_id INTEGER PRIMARY KEY)""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)""")
                conn.commit()

            print("SYSTEM: Database tables initialized")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to initialize database tables --> {e}")

    def is_moderator(self, user_id: int) -> bool:
        """
        Verifica se um user_id está na tabela de moderadores.
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM moderators WHERE user_id = ?", (user_id))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"ERROR: Failed to check moderator status --> {e}")
            return False

    def is_banned(self, user_id: int) -> bool:
        """
        Verifica se um user_id está na tabela de banidos.
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"ERROR: Failed to check ban status --> {e}")
            return False

    def get_user_id(self, user_id: int) -> Optional[int]:
        """
        Retona o user_id ou None da tabela de usuários.
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"ERROR: Failed to get user_id --> {e}")
            return None

    def add_moderator(self, user_id: int):
        """
        Adiciona um novo moderador ao banco.
        """

        try:
            with self._get_connection() as conn:
                conn.execute("INSERT OR IGNORE INTO moderators (user_id) VALUES (?)", (user_id))
                conn.commit()
        except Exception as e:
            print(f"ERROR: Failed to add moderator --> {e}")

    def remove_moderator(self, user_id: int):
        """
        Remove um moderador do banco.
        """

        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM moderators WHERE user_id = ?", (user_id))
                conn.commit()
        except Exception as e:
            print(f"ERROR: Failed to remove moderator --> {e}")

    def ban_user(self, user_id: int):
        """
        Adiciona um usuário banido ao banco.
        """

        try:
            with self._get_connection() as conn:
                conn.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id))
                conn.commit()
        except Exception as e:
            print(f"ERROR: Failed to ban user --> {e}")

    def unban_user(self, user_id: int):
        """
        Remove um usuário banido do banco.
        """

        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id))
                conn.commit()
        except Exception as e:
            print(f"ERROR: Failed to unban user --> {e}")

    def save_user(self, user_id: int):
        """
        Adiciona um usuário ao banco.
        """

        try:
            with self._get_connection() as conn:
                conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id))
                conn.commit()
        except Exception as e:
            print(f"ERROR: Failed to save user --> {e}")

    def delete_user(self, user_id: int):
        """
        Remove um usuário do banco.
        """

        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM users WHERE user_id = ?", (user_id))
                conn.commit()
        except Exception as e:
            print(f"ERROR: Failed to delete user --> {e}")