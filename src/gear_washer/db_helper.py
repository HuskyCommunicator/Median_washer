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
            
            # 装备类型位置配置表
            # id 自增主键
            # name 类型名称
            # gear_pos_x/y 装备坐标
            # affix_area_p1/p2 词缀区域坐标
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS equipment_type (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    gear_pos_x INTEGER,
                    gear_pos_y INTEGER,
                    affix_area_p1_x INTEGER,
                    affix_area_p1_y INTEGER,
                    affix_area_p2_x INTEGER,
                    affix_area_p2_y INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 词缀表
            # 存储词缀名称，供通用的词缀库使用
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS affix (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT UNIQUE,
                    description TEXT
                )
            ''')
            
            # 检查 equipment_type 表是否有 window_title 列（迁移旧数据）
            try:
                cursor.execute('ALTER TABLE equipment_type ADD COLUMN window_title TEXT')
                print("DEBUG: 已添加 window_title 列到 equipment_type 表")
            except sqlite3.OperationalError:
                # 列已存在
                pass
            
            conn.commit()

    def save_equipment_type(self, name, gear_pos, affix_points, window_title=None):
        """
        保存装备类型配置
        :param name: 装备名称 (如 '法杖', '项链')
        :param gear_pos: (x, y) 元组 (如果是相对坐标模式，这里是 offset)
        :param affix_points: ((x1, y1), (x2, y2)) 元组 (相对 offset)
        :param window_title: 绑定的窗口标题，如果为None则表示绝对坐标
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 使用 INSERT OR REPLACE 会导致 ID 变化，如果希望保持 ID 不变应该先 check exists
            # 但这里为了简单，如果名字一样就更新属性
            cursor.execute('''
                INSERT INTO equipment_type 
                (name, gear_pos_x, gear_pos_y, affix_area_p1_x, affix_area_p1_y, affix_area_p2_x, affix_area_p2_y, window_title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    gear_pos_x=excluded.gear_pos_x,
                    gear_pos_y=excluded.gear_pos_y,
                    affix_area_p1_x=excluded.affix_area_p1_x,
                    affix_area_p1_y=excluded.affix_area_p1_y,
                    affix_area_p2_x=excluded.affix_area_p2_x,
                    affix_area_p2_y=excluded.affix_area_p2_y,
                    window_title=excluded.window_title,
                    updated_at=CURRENT_TIMESTAMP
            ''', (
                name, 
                gear_pos[0], gear_pos[1], 
                affix_points[0][0], affix_points[0][1],
                affix_points[1][0], affix_points[1][1],
                window_title
            ))
            conn.commit()

    def get_equipment_type_by_id(self, type_id):
        """通过ID获取配置"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 这里可能会失败如果SELECT * 顺序变了，最好指名字段，但简单起见我们把新列加在最后
            cursor.execute('SELECT * FROM equipment_type WHERE id = ?', (type_id,))
            row = cursor.fetchone()
            if row:
                # row: id, name, gx, gy, ax1, ay1, ax2, ay2, updated_at, [window_title]
                # 注意：updated_at 是第9列(index 8)，新列是第10列(index 9)
                # 因为 sqlite 的 ALTER TABLE ADD COLUMN 是加在末尾
                
                # 稳妥起见，我们重新查询一次带列名的
                cursor.execute('SELECT id, name, gear_pos_x, gear_pos_y, affix_area_p1_x, affix_area_p1_y, affix_area_p2_x, affix_area_p2_y, window_title FROM equipment_type WHERE id = ?', (type_id,))
                specific_row = cursor.fetchone()
                
                return {
                    'id': specific_row[0],
                    'name': specific_row[1],
                    'gear_pos': (specific_row[2], specific_row[3]),
                    'affix_points': ((specific_row[4], specific_row[5]), (specific_row[6], specific_row[7])),
                    'window_title': specific_row[8] if len(specific_row) > 8 else None
                }
            return None

    def get_equipment_type(self, name):
        """
        获取指定装备类型的配置
        :return: {'id':..., 'name':..., 'gear_pos': (x,y), 'affix_points': ((x1,y1), (x2,y2))}
        """
        with sqlite3.connect(self.db_path) as conn:
             cursor = conn.cursor()
             cursor.execute('SELECT * FROM equipment_type WHERE name = ?', (name,))
             row = cursor.fetchone()
             if row:
                 # row: id, name, gx, gy, ax1, ay1, ax2, ay2, updated_at
                 return {
                     'id': row[0],
                     'name': row[1],
                     'gear_pos': (row[2], row[3]),
                     'affix_points': ((row[4], row[5]), (row[6], row[7]))
                 }
             return None

    def add_affix(self, content, description=""):
        """添加词缀组到词缀库，如果存在则更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO affix (content, description) VALUES (?, ?)
                    ON CONFLICT(content) DO UPDATE SET
                    description=excluded.description
                ''', (content, description))
                conn.commit()
                return True
            except Exception as e:
                print(f"Error adding affix: {e}")
                return False

    def update_affix(self, affix_id, content, description):
        """根据ID更新词缀内容和描述"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE affix 
                    SET content = ?, description = ?
                    WHERE id = ?
                ''', (content, description, affix_id))
                if cursor.rowcount == 0:
                    return False
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                print(f"Error: Content '{content}' already exists in another rule.")
                return False
            except Exception as e:
                print(f"Error updating affix: {e}")
                return False

    def get_all_affixes(self):
        """获取所有词缀"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, content, description FROM affix ORDER BY id')
            return cursor.fetchall()

    def list_equipment_types(self):
        """列出所有装备类型 (id, name)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name FROM equipment_type ORDER BY id')
            return cursor.fetchall()
            
    def rename_equipment_type(self, type_id, new_name):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('UPDATE equipment_type SET name = ? WHERE id = ?', (new_name, type_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def delete_equipment_type(self, type_id):
        with sqlite3.connect(self.db_path) as conn:
             cursor = conn.cursor()
             cursor.execute('DELETE FROM equipment_type WHERE id = ?', (type_id,))
             conn.commit()
             
    def rename_affix(self, affix_id, new_name):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE affix SET description = ? WHERE id = ?', (new_name, affix_id))
            conn.commit()
            return True

    def delete_affix(self, affix_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM affix WHERE id = ?', (affix_id,))
            conn.commit()

    def set(self, key, value):
        """保存数据，如果是dict/list/tuple/None会自动转换为json字符串"""
        if value is None or isinstance(value, (dict, list, tuple, bool, int, float)):
            # json.dumps 默认将 tuple 转为 list
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
                    # 尝试处理类似 "(100, 200)" 的字符串（旧数据兼容）
                    if isinstance(val, str) and val.startswith('(') and val.endswith(')'):
                        try:
                            # 简单的元组解析，仅当看起来像 int 元组时
                            # 去掉括号，按逗号分割
                            parts = val[1:-1].split(',')
                            return tuple(int(p.strip()) for p in parts if p.strip())
                        except:
                            pass
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
