import customtkinter as ctk

class RuleTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        self._init_ui()

    def _init_ui(self):
        # 滚动容器
        scroll_rule = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_rule.pack(fill="both", expand=True)

        # 居中容器
        content_frame = ctk.CTkFrame(scroll_rule, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=20)
        content_frame.grid_columnconfigure(0, weight=1)

        # --- 顶部标题 ---
        self.lbl_title = ctk.CTkLabel(
            content_frame, 
            text="规则管理中心", 
            font=("Microsoft YaHei", 20, "bold")
        )
        self.lbl_title.grid(row=0, column=0, pady=(0, 20))


        # --- 功能卡片 1: 选择与新建 ---
        self.card_select = ctk.CTkFrame(content_frame, corner_radius=10)
        self.card_select.grid(row=1, column=0, sticky="ew", pady=10)
        self.card_select.grid_columnconfigure(0, weight=1)
        self.card_select.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            self.card_select, 
            text="当前编辑的规则", 
            font=("Microsoft YaHei", 12, "bold"), 
            text_color="gray"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        self.combo_affix_mgr = ctk.CTkComboBox(
            self.card_select, 
            height=35,
            font=("Microsoft YaHei", 14),
            state="readonly",
            command=self.app.on_affix_mgr_change
        )
        self.combo_affix_mgr.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        # 新建按钮 (右上角)
        self.btn_new_rule = ctk.CTkButton(
            self.card_select, 
            text="✚ 新建规则", 
            command=self.app.create_new_rule,
            fg_color="#2EA043",           # GitHub Green
            hover_color="#238636",
            width=120,
            height=35,
            font=("Microsoft YaHei", 13, "bold")
        )
        self.btn_new_rule.grid(row=1, column=1, padx=15, pady=(0, 15))


        # --- 功能卡片 2: 核心操作 ---
        self.card_ops = ctk.CTkFrame(content_frame, corner_radius=10)
        self.card_ops.grid(row=2, column=0, sticky="ew", pady=10)
        self.card_ops.grid_columnconfigure(0, weight=1)
        self.card_ops.grid_columnconfigure(1, weight=1)

        # 编辑详情 (大按钮)
        self.btn_advanced = ctk.CTkButton(
            self.card_ops, 
            text="📝 编辑规则详情", 
            command=self.app.open_advanced_editor,
            fg_color="#1F6FEB",           # GitHub Blue
            hover_color="#1158C7",
            height=40,
            font=("Microsoft YaHei", 14, "bold")
        )
        self.btn_advanced.grid(row=0, column=0, columnspan=2, padx=15, pady=(20, 10), sticky="ew")

        # 辅助操作行
        self.frame_sub_ops = ctk.CTkFrame(self.card_ops, fg_color="transparent")
        self.frame_sub_ops.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 20))
        self.frame_sub_ops.grid_columnconfigure(0, weight=1)
        self.frame_sub_ops.grid_columnconfigure(1, weight=1)
        self.frame_sub_ops.grid_columnconfigure(2, weight=1)
        
        # 重命名
        self.btn_rename_rule = ctk.CTkButton(
            self.frame_sub_ops, 
            text="✎ 重命名", 
            command=self.app.rename_current_rule,
            fg_color="#6E7681",           # GitHub Gray
            hover_color="#57606A",
            height=35,
            font=("Microsoft YaHei", 12)
        )
        self.btn_rename_rule.grid(row=0, column=0, padx=5, sticky="ew")
        
        # 导入默认
        self.btn_load_def = ctk.CTkButton(
            self.frame_sub_ops, 
            text="📥 导入默认库", 
            command=self.app.load_defaults,
            fg_color="#333333",           # Dark Gray
            hover_color="#222222",
            height=35,
            font=("Microsoft YaHei", 12)
        )
        self.btn_load_def.grid(row=0, column=1, padx=5, sticky="ew")
        
        # 删除
        self.btn_delete_rule = ctk.CTkButton(
            self.frame_sub_ops, 
            text="🗑 删除规则", 
            command=self.app.delete_current_rule,
            fg_color="#DA3633",           # GitHub Red
            hover_color="#B62324",
            height=35,
            font=("Microsoft YaHei", 12)
        )
        self.btn_delete_rule.grid(row=0, column=2, padx=5, sticky="ew")
