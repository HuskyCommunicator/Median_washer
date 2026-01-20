import sqlite3
import json
import os

class SimpleDB:
    def __init__(self, db_name="game_data.db"):
        # 默认数据库存在当前运行目录下
        self.db_path = os.path.join(os.getcwd(), db_name)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 创建一个通用的键值对表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS storage (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def set(self, key, value):
        """保存数据，如果是dict/list/None会自动转换为json字符串"""
        if value is None or isinstance(value, (dict, list, bool, int, float)):
            save_value = json.dumps(value, ensure_ascii=False)
        else:
            save_value = str(value)
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 插入或更新
            cursor.execute('''
                INSERT OR REPLACE INTO storage (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, save_value))
            conn.commit()

    def get(self, key, default=None):
        """获取数据，尝试自动解析JSON"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM storage WHERE key = ?', (key,))
            row = cursor.fetchone()
            
            if row:
                val = row[0]
                try:
                    return json.loads(val)
                except:
                    return val
            return default

    def delete(self, key):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM storage WHERE key = ?', (key,))
            conn.commit()

    def list_keys(self, prefix=""):
        """列出所有以 prefix 开头的 key"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key FROM storage WHERE key LIKE ?', (f'{prefix}%',))
            return [row[0] for row in cursor.fetchall()]
