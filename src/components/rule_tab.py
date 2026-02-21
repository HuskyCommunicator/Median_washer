import customtkinter as ctk

class RuleTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        self._init_ui()

    def _init_ui(self):
        # 添加滚动容器以适应小窗口
        scroll_rule = ctk.CTkScrollableFrame(self)
        scroll_rule.pack(fill="both", expand=True, padx=5, pady=5)

        # 顶部标题
        ctk.CTkLabel(scroll_rule, text="词缀规则管理中心", font=("Microsoft YaHei", 16, "bold"), text_color="silver").pack(pady=(15, 5))
        
        # 1. 规则选择区
        self.frame_rule_card = ctk.CTkFrame(scroll_rule)
        self.frame_rule_card.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(self.frame_rule_card, text="当前编辑的规则:").pack(pady=(10, 2))
        self.combo_affix_mgr = ctk.CTkComboBox(self.frame_rule_card, state="readonly", width=320, command=self.app.on_affix_mgr_change)
        self.combo_affix_mgr.pack(pady=5)
        
        # 2. 核心操作区
        self.frame_rule_ops = ctk.CTkFrame(scroll_rule, fg_color="transparent")
        self.frame_rule_ops.pack(fill="x", padx=15, pady=5)
        
        # 使用 grid 布局，2列
        self.frame_rule_ops.grid_columnconfigure(0, weight=1)
        self.frame_rule_ops.grid_columnconfigure(1, weight=1)
        
        # 第1行：主要操作
        self.btn_new_rule = ctk.CTkButton(self.frame_rule_ops, text="✚ 新建规则", height=40, command=self.app.create_new_rule)
        self.btn_new_rule.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # 第2行：编辑详情与重命名
        self.btn_advanced = ctk.CTkButton(self.frame_rule_ops, text="📝 编辑详情(JSON)", height=35, fg_color="#555555", command=self.app.open_advanced_editor)
        self.btn_advanced.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_rename_rule = ctk.CTkButton(self.frame_rule_ops, text="✎ 重命名", height=35, fg_color="#FFA500", command=self.app.rename_current_rule)
        self.btn_rename_rule.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # 第3行：删除与导入
        self.btn_delete_rule = ctk.CTkButton(self.frame_rule_ops, text="🗑 删除规则", height=35, fg_color="darkred", command=self.app.delete_current_rule)
        self.btn_delete_rule.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # 第4行: 导入默认库 (单独放最下)
        self.btn_load_def = ctk.CTkButton(self.frame_rule_ops, text="📥 导入默认库", height=30, fg_color="#333333", command=self.app.load_defaults)
        self.btn_load_def.grid(row=3, column=0, columnspan=2, padx=5, pady=(15, 5), sticky="ew")
