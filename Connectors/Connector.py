#python -m pip install mysql-connector-python
import traceback

import mysql.connector
import pandas as pd

from Utils import Config


class Connector:
    def __init__(self, server=None, port=None, database=None, username=None, password=None):
        self.server = server or Config.DB_SERVER
        self.port = port or Config.DB_PORT
        self.database = Config.DB_DATABASE if database is None else database
        self.username = username or Config.DB_USERNAME
        self.password = Config.DB_PASSWORD if password is None else password
        self.conn = None

    def connect(self):
        try:
            self.conn = mysql.connector.connect(
                host=self.server,
                port=self.port,
                database=self.database or None,   # "" -> chưa chọn DB (lúc tạo schema)
                user=self.username,
                password=self.password)
            return self.conn
        except:
            self.conn = None
            traceback.print_exc()
        return None

    def disConnect(self):
        if self.conn != None:
            self.conn.close()

    def queryDataset(self, sql, params=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            df = pd.DataFrame(cursor.fetchall())
            if not df.empty:
                df.columns = cursor.column_names
            cursor.close()
            return df
        except:
            traceback.print_exc()
        return None

    def getTablesName(self):
        cursor = self.conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def executeNonQuery(self, sql, params=None):
        """INSERT / UPDATE / DELETE / DDL - trả về số dòng bị ảnh hưởng."""
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        self.conn.commit()
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount

    def executeMany(self, sql, rows, batch_size=10_000):
        """Chèn nhiều dòng theo lô để không vượt max_allowed_packet."""
        cursor = self.conn.cursor()
        total = 0
        try:
            for i in range(0, len(rows), batch_size):
                cursor.executemany(sql, rows[i:i + batch_size])
                total += cursor.rowcount
            self.conn.commit()
        except:
            self.conn.rollback()
            raise
        finally:
            cursor.close()
        return total

    def executeScript(self, path):
        """Chạy file .sql nhiều câu lệnh (bỏ qua dòng comment)."""
        lines = [l for l in open(path, encoding="utf-8") if not l.strip().startswith("--")]
        for stmt in "".join(lines).split(";"):
            if stmt.strip():
                self.executeNonQuery(stmt)
