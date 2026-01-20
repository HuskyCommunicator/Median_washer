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

    def add_affix_row(self, container, rows_list, data=""):
        row_frame = ctk.CTkFrame(container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        
        text_val = ""
        is_exact_val = False
        
        if isinstance(data, dict):
            text_val = data.get("name", "")
            if data.get("exact") is True:
                is_exact_val = True
        elif isinstance(data, str):
            text_val = data
        
        entry = ctk.CTkEntry(row_frame, placeholder_text="输入词缀名称")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        if text_val:
            entry.insert(0, text_val)
            
        btn_del = ctk.CTkButton(row_frame, text="-", width=30, height=24, fg_color="darkred", 
                                command=lambda: self.remove_affix_row(row_frame, rows_list))
        btn_del.pack(side="right")

        # 精准匹配复选框
        chk_var = ctk.IntVar(value=1 if is_exact_val else 0)
        chk_exact = ctk.CTkCheckBox(row_frame, text="精准", variable=chk_var, width=50, checkbox_width=18, checkbox_height=18)
        chk_exact.pack(side="right", padx=5)
        
        rows_list.append({"frame": row_frame, "entry": entry, "exact_var": chk_var})

    def remove_affix_row(self, row_frame, rows_list):
        row_frame.destroy()
        # 从列表移除
        for i, item in enumerate(rows_list):
            if item["frame"] == row_frame:
                del rows_list[i]
                break

    def remove_group(self, frame):
        # 从 UI 移除
        frame.destroy()
        # 从列表移除引用
        self.groups = [g for g in self.groups if g["frame"] != frame]

    def save_data(self):
        result = []
        for g in self.groups:
            display_type = g["type_var"].get()
            g_type = REVERSE_TYPE_MAP.get(display_type, "AND")
            
            # 解析 min/max
            min_v = g["entry_min"].get().strip()
            max_v = g["entry_max"].get().strip()
            
            # 解析词缀
            affixes = []
            for row in g["affix_rows"]:
                val = row["entry"].get().strip()
                if val:
                    is_exact = bool(row["exact_var"].get())
                    # 如果勾选精准，我们存成 {"name": "xxx", "exact": true}
                    # 否则存成字符串（保持兼容性）
                    if is_exact:
                        affixes.append({"name": val, "exact": True})
                    else:
                        affixes.append(val)
            
            item = {
                "type": g_type,
                "affixes": affixes
            }
            
            if g_type == 'COUNT':
                if min_v.isdigit(): item['min'] = int(min_v)
                if max_v.isdigit(): item['max'] = int(max_v)
                
            result.append(item)
            
        if self.callback:
            self.callback(result)
        self.destroy()
