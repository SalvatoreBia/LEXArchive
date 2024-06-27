import sqlite3
import datetime


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            Database._instance = super(Database, cls).__new__(cls)
        return Database._instance

    def __init__(self):
        self.DUMP = 'config/dump.txt'
        self.DB = 'archive/db.json'
        self.LIMIT = 20
        self.conn = None
        self.cursor = None
        self._setup()

    def _setup(self):
        self.conn = sqlite3.connect(self.DB)
        self.cursor = self.conn.cursor()
        with open (self.DUMP, 'r') as file:
            self.cursor.execute(file.read())
        self.conn.commit()

    def execute_query(self, query, params=None):
        if params is None:
            params = []
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor

    def close(self):
        self.conn.close()

    def limit(self):
        return self.LIMIT


db = Database()


def insert(rows: list):
    try:
        query = '''
                    INSERT INTO ps VALUES 
                    (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                '''
        for row in rows:
            res = db.execute_query(query, row)
        return True
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False


def set_current_date():
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    try:
        query = 'UPDATE ps SET last_write = ?'
        res = db.execute_query(query, [date])
        return True
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False


def get_last_date():
    try:
        query = 'SELECT last_write FROM ps LIMIT 1'
        res = db.execute_query(query)
        return res.fetchone()[0] if res else None
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


def delete(rows: list):
    try:
        query = 'DELETE FROM ps WHERE pl_name = ?'
        res = db.execute_query(query, rows)
        return True
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return False


def count():
    try:
        query = 'SELECT COUNT(id) FROM ps'
        res = db.execute_query(query)
        return res.fetchone()[0] if res else -1
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return -1


def count_pl():
    try:
        query = 'SELECT COUNT(DISTINCT pl_name) FROM ps'
        res = db.execute_query(query)
        return res.fetchone()[0] if res else -1
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return -1


def disc_in(year: int):
    try:
        query = 'SELECT COUNT(DISTINCT pl_name) FROM ps WHERE disc_year = ?'
        res = db.execute_query(query, [year])
        return res.fetchone()[0] if res else -1
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return -1


def search_pl(start: int, end: int, keyword=None):
    try:
        query = 'SELECT DISTINCT pl_name FROM ps'
        res = None
        if keyword is not None:
            query += ' WHERE LOWER(REPLACE(pl_name, " ", "")) LIKE ?'
            query += ' ORDER BY pl_name LIMIT ? OFFSET ?'
            res = db.execute_query(query, [f'%{keyword}%', end-start, start])
        else:
            query += ' ORDER BY pl_name LIMIT ? OFFSET ?'
            res = db.execute_query(query, [end-start, start])
        return [row[0] for row in res.fetchall()] if res else None
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


def count_like(keyword: str):
    try:
        if keyword is None:
            return count_pl()
        else:
            query = 'SELECT COUNT(DISTINCT pl_name) FROM ps WHERE LOWER(REPLACE(pl_name, " ", "")) LIKE ?'
            res = db.execute_query(query, [f'%{keyword}%'])
            return res.fetchone()[0] if res else None
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


def get_pl_by_name(keyword: str):
    try:
        query = f'SELECT * FROM ps WHERE LOWER(REPLACE(pl_name, " ", "")) LIKE ? LIMIT {db.limit()}'
        res = db.execute_query(query, [f'%{keyword}%'])
        return [row for row in res.fetchall()] if res else None
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


def get_field_values(keyword: str):
    try:
        query = f'SELECT {keyword} FROM ps WHERE {keyword} != ""'
        res = db.execute_query(query)
        return [float(row[0]) for row in res.fetchall()] if res else None
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None
