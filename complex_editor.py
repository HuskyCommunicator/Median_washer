import customtkinter as ctk
import json

TYPE_MAP = {
    "AND": "和",
    "COUNT": "数量",
    "NOT": "非"
}
REVERSE_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}

class ComplexRuleEditor(ctk.CTkToplevel):
    def __init__(self, parent, initial_data=None, callback=None):
        """
        :param initial_data: 初始数据 (list of dicts) 或 None
        :param callback: 保存时的回调函数，接收 (json_data_list)
        """
        super().__init__(parent)
        self.title("高级规则编辑器")
        self.geometry("600x500")
        
        # 强制置顶并聚焦
        self.lift() 
        self.focus_force()
        # 设为模态窗口 (可选: grab_set 会阻止用户操作主窗口，直到关闭此窗口)
        self.grab_set() 
        
        self.callback = callback
        self.groups = [] # 存储 UI 组件引用

        # 底部按钮区
        self.frame_actions = ctk.CTkFrame(self)
        self.frame_actions.pack(side="bottom", fill="x", padx=10, pady=10)

        self.btn_reset = ctk.CTkButton(self.frame_actions, text="↺ 重置", width=100, fg_color="gray", command=self.reset_groups)
        self.btn_reset.pack(side="left", padx=10)

        self.btn_save = ctk.CTkButton(self.frame_actions, text="保存并应用", fg_color="green", command=self.save_data)
        self.btn_save.pack(side="right", padx=10)

        # 列表头部区域（标题 + 添加按钮）
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(side="top", fill="x", padx=10, pady=(10, 0))

        self.lbl_title = ctk.CTkLabel(self.frame_header, text="条件组列表", font=("Microsoft YaHei", 12, "bold"))
        self.lbl_title.pack(side="left", padx=5)

        self.btn_add = ctk.CTkButton(self.frame_header, text="+ 新建条件组", width=100, height=28, command=self.add_group)
        self.btn_add.pack(side="right", padx=5)

        # 主滚动区域
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        # 初始化数据
        if initial_data and isinstance(initial_data, list):
            for g_data in initial_data:
                self.add_group(g_data)
        else:
            self.add_group() # 默认加一个空组

    def reset_groups(self):
        for g in self.groups:
            g["frame"].destroy()
        self.groups.clear()
        self.add_group()

    def add_group(self, data=None):
        if data is None:
            data = {"type": "AND", "affixes": [], "min": "", "max": ""}
        
        # 组容器
        group_frame = ctk.CTkFrame(self.scroll_frame, border_width=1, border_color="gray")
        group_frame.pack(fill="x", pady=5, padx=5)
        
        # 顶部栏
        header = ctk.CTkFrame(group_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=5)
        
        # 逻辑类型
        lbl_type = ctk.CTkLabel(header, text="逻辑类型:")
        lbl_type.pack(side="left", padx=5)
        
        initial_type_code = data.get("type", "AND")
        initial_display = TYPE_MAP.get(initial_type_code, "和")
        
        type_var = ctk.StringVar(value=initial_display)
        
        # Min/Max 容器 (提前创建)
        min_max_frame = ctk.CTkFrame(header, fg_color="transparent")

        def on_type_change(choice):
            if choice == "数量":
                min_max_frame.pack(side="left", padx=5)
            else:
                min_max_frame.pack_forget()

        combo_type = ctk.CTkComboBox(header, values=list(TYPE_MAP.values()), variable=type_var, width=80, command=on_type_change)
        combo_type.pack(side="left", padx=5)
        
        # 数量限制组件
        lbl_min = ctk.CTkLabel(min_max_frame, text="Min:")
        lbl_min.pack(side="left", padx=2)
        entry_min = ctk.CTkEntry(min_max_frame, width=40, placeholder_text="0")
        entry_min.pack(side="left", padx=2)
        if data.get("min") is not None: entry_min.insert(0, str(data.get("min")))
        
        lbl_max = ctk.CTkLabel(min_max_frame, text="Max:")
        lbl_max.pack(side="left", padx=2)
        entry_max = ctk.CTkEntry(min_max_frame, width=40, placeholder_text="9")
        entry_max.pack(side="left", padx=2)
        if data.get("max") is not None: entry_max.insert(0, str(data.get("max")))

        # 初始化显示状态
        on_type_change(initial_display)

        # 删除按钮
        btn_del = ctk.CTkButton(header, text="X", width=30, fg_color="red", command=lambda: self.remove_group(group_frame))
        btn_del.pack(side="right", padx=5)

        # 分割线
        sep = ctk.CTkFrame(group_frame, height=2, fg_color="gray")
        sep.pack(fill="x", padx=5, pady=2)

        # 词缀列表区域
        lbl_affix = ctk.CTkLabel(group_frame, text="词缀列表:", font=("Microsoft YaHei", 12))
        lbl_affix.pack(anchor="w", padx=10, pady=(5,0))
        
        affix_container = ctk.CTkFrame(group_frame, fg_color="transparent")
        affix_container.pack(fill="x", padx=10, pady=5)
        
        affix_rows = []
        
        # 填充初始词缀
        existing_affixes = data.get("affixes", [])
        if existing_affixes and isinstance(existing_affixes, list):
            for item in existing_affixes:
                self.add_affix_row(affix_container, affix_rows, item)
        
        # 默认至少有一条，如果为空
        if not affix_rows:
            self.add_affix_row(affix_container, affix_rows, "")
             
        # 添加词缀按钮
        btn_add_affix = ctk.CTkButton(group_frame, text="+ 添加词缀", height=24, fg_color="#444444", 
                                      command=lambda: self.add_affix_row(affix_container, affix_rows))
        btn_add_affix.pack(anchor="w", padx=10, pady=(0, 10))

        # 保存引用以便后续读取
        self.groups.append({
            "frame": group_frame,
            "type_var": type_var,
            "entry_min": entry_min,
            "entry_max": entry_max,
            "affix_rows": affix_rows
        })


    def add_affix_row(self, container, rows_list, data=None):
        """添加一行词缀输入框，支持数值范围"""
        if data is None: data = ""
        
        row_frame = ctk.CTkFrame(container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        
        # 1. 解析初始数据
        text_val = ""
        min_val = ""
        max_val = ""
        
        if isinstance(data, dict):
            text_val = data.get("name", "")
            min_val = str(data.get("min_value", ""))
            max_val = str(data.get("max_value", ""))
        elif isinstance(data, str):
            text_val = data
        
        # 2. 词缀名称输入
        entry_name = ctk.CTkEntry(row_frame, placeholder_text="词缀名 (如: 力量)", width=200)
        entry_name.pack(side="left", fill="x", expand=True, padx=(0, 5))
        if text_val: entry_name.insert(0, text_val)
        
        # 3. 数值范围输入 (Min/Max)
        # 用 Label 提示 "值 >="
        ctk.CTkLabel(row_frame, text="值>=", text_color="gray", width=30).pack(side="left")
        entry_min = ctk.CTkEntry(row_frame, width=50, placeholder_text="-∞")
        entry_min.pack(side="left", padx=2)
        if min_val: entry_min.insert(0, min_val)
        
        ctk.CTkLabel(row_frame, text="且<=", text_color="gray", width=30).pack(side="left")
        entry_max = ctk.CTkEntry(row_frame, width=50, placeholder_text="+∞")
        entry_max.pack(side="left", padx=2)
        if max_val: entry_max.insert(0, max_val)

        # 4. 删除按钮
        btn_del = ctk.CTkButton(row_frame, text="🗑", width=30, height=28, fg_color="#333", hover_color="#555",
                                command=lambda: self._remove_affix_row_helper(row_frame, rows_list))
        btn_del.pack(side="right", padx=(5, 0))

        # 保存引用
        rows_list.append({
            "frame": row_frame, 
            "entry_name": entry_name,
            "entry_min": entry_min,
            "entry_max": entry_max
        })

    def _remove_affix_row_helper(self, row_frame, rows_list):
        """辅助删除函数，确保从列表正确移除"""
        row_frame.destroy()
        # 从列表移除引用
        # 注意: 不能直接 remove row_frame，因为列表存的是 dict
        target_idx = -1
        for i, item in enumerate(rows_list):
            if item["frame"] == row_frame:
                target_idx = i
                break
        if target_idx != -1:
            del rows_list[target_idx]

    def remove_group(self, frame_or_dict):
        # 找到对应的 dict
        target_g = None
        target_frame = None
        
        if isinstance(frame_or_dict, dict):
            target_g = frame_or_dict
            target_frame = target_g["frame"]
        else:
            target_frame = frame_or_dict
            # 遍历列表找到对应 dict
            for g in self.groups:
                if g["frame"] == target_frame:
                    target_g = g
                    break
        
        if target_g:
            target_frame.destroy()
            self.groups = [g for g in self.groups if g != target_g]
        else:
            # 兜底
            try:
                target_frame.destroy()
            except: pass

    def save_data(self):
        result = []
        # 遍历所有大组
        for g in self.groups:
            # 1. 获取组类型 (AND/OR/COUNT/NOT)
            display_type = ""
            if hasattr(g["type_var"], 'get'): # StringVar
                display_type = g["type_var"].get()
            else:
                display_type = g["type_var"] # 可能已经是 str?
                
            g_type = REVERSE_TYPE_MAP.get(display_type, "AND")
            
            # 2. 获取组的全局限制 (COUNT min/max)
            group_min = g["entry_min"].get().strip()
            group_max = g["entry_max"].get().strip()
            
            # 3. 获取组内的所有词缀
            affixes = []
            for row in g["affix_rows"]:
                name = row["entry_name"].get().strip()
                min_v = row["entry_min"].get().strip()
                max_v = row["entry_max"].get().strip()
                
                if not name:
                    continue
                    
                # 构造词缀对象
                # 如果没有数值限制，存为字符串(保持简洁)；否则存为字典
                if not min_v and not max_v:
                    affixes.append(name)
                else:
                    affix_obj = {"name": name}
                    if min_v: affix_obj["min_value"] = float(min_v)
                    if max_v: affix_obj["max_value"] = float(max_v)
                    affixes.append(affix_obj)
            
            # 构造组对象
            group_item = {
                "type": g_type,
                "affixes": affixes
            }
            
            # 如果是 COUNT 类型，补充 limit
            if g_type == 'COUNT':
                if group_min and group_min.isdigit(): group_item['min'] = int(group_min)
                if group_max and group_max.isdigit(): group_item['max'] = int(group_max)
                
            result.append(group_item)
            
        if self.callback:
            self.callback(result)
        self.destroy()
