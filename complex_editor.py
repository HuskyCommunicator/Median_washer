import customtkinter as ctk
import json

class ComplexRuleEditor(ctk.CTkToplevel):
    def __init__(self, parent, initial_data=None, callback=None):
        """
        :param initial_data: 初始数据 (list of dicts) 或 None
        :param callback: 保存时的回调函数，接收 (json_data_list)
        """
        super().__init__(parent)
        self.title("高级规则编辑器")
        self.geometry("600x700")
        
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
        
        # 顶部栏: 类型选择 + 数量限制 + 删除按钮
        header = ctk.CTkFrame(group_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=5)
        
        lbl_type = ctk.CTkLabel(header, text="逻辑类型:")
        lbl_type.pack(side="left", padx=5)
        
        type_var = ctk.StringVar(value=data.get("type", "AND"))
        combo_type = ctk.CTkComboBox(header, values=["AND", "COUNT", "NOT"], variable=type_var, width=80)
        combo_type.pack(side="left", padx=5)
        
        # 数量限制区域 (仅 COUNT 模式有效，这里为了简单都显示，或者动态显示)
        lbl_min = ctk.CTkLabel(header, text="Min:")
        lbl_min.pack(side="left", padx=2)
        entry_min = ctk.CTkEntry(header, width=40, placeholder_text="0")
        entry_min.pack(side="left", padx=2)
        if data.get("min") is not None: entry_min.insert(0, str(data.get("min")))
        
        lbl_max = ctk.CTkLabel(header, text="Max:")
        lbl_max.pack(side="left", padx=2)
        entry_max = ctk.CTkEntry(header, width=40, placeholder_text="9")
        entry_max.pack(side="left", padx=2)
        if data.get("max") is not None: entry_max.insert(0, str(data.get("max")))

        # 删除按钮
        btn_del = ctk.CTkButton(header, text="X", width=30, fg_color="red", command=lambda: self.remove_group(group_frame))
        btn_del.pack(side="right", padx=5)

        # 词缀输入区
        lbl_affix = ctk.CTkLabel(group_frame, text="词缀列表 (每行一条):")
        lbl_affix.pack(anchor="w", padx=10)
        
        txt_affixes = ctk.CTkTextbox(group_frame, height=100)
        txt_affixes.pack(fill="x", padx=10, pady=5)
        
        # 填充词缀
        if "affixes" in data and isinstance(data["affixes"], list):
            txt_affixes.insert("0.0", "\n".join(data["affixes"]))

        # 保存引用以便后续读取
        self.groups.append({
            "frame": group_frame,
            "type_var": type_var,
            "entry_min": entry_min,
            "entry_max": entry_max,
            "txt_affixes": txt_affixes
        })

    def remove_group(self, frame):
        # 从 UI 移除
        frame.destroy()
        # 从列表移除引用
        self.groups = [g for g in self.groups if g["frame"] != frame]

    def save_data(self):
        result = []
        for g in self.groups:
            g_type = g["type_var"].get()
            
            # 解析 min/max
            min_v = g["entry_min"].get().strip()
            max_v = g["entry_max"].get().strip()
            
            # 解析词缀
            raw_affixes = g["txt_affixes"].get("0.0", "end").strip().split('\n')
            affixes = [a.strip() for a in raw_affixes if a.strip()]
            
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
