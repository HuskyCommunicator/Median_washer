import customtkinter as ctk

import customtkinter as ctk

class RunTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        # 让内容在水平方向上自适应
        self.grid_columnconfigure(0, weight=1)
        
        self._init_ui()

    def _init_ui(self):
        # --- 标题 ---
        self.title_label = ctk.CTkLabel(
            self, 
            text="运行控制台", 
            font=("Microsoft YaHei", 24, "bold"),
            text_color=("gray40", "gray80")
        )
        self.title_label.grid(row=0, column=0, pady=(30, 20))

        # --- 配置卡片区域 ---
        # 使用圆角 Frame 包裹配置项，形成卡片效果，并加上一点背景色区分
        # fg_color 具体颜色可以根据主题自适应，这里留空让它跟随主题的一般层级
        self.config_card = ctk.CTkFrame(self, corner_radius=15, width=400)
        self.config_card.grid(row=1, column=0, padx=40, pady=10)
        
        # 让卡片内部两列分布合理
        self.config_card.grid_columnconfigure(0, weight=1) # Label列
        self.config_card.grid_columnconfigure(1, weight=2) # Input列

        # 1. 装备选择
        self.lbl_equip = ctk.CTkLabel(
            self.config_card, 
            text="目标装备:", 
            font=("Microsoft YaHei", 16)
        )
        self.lbl_equip.grid(row=0, column=0, padx=(30, 10), pady=25, sticky="e")

        self.combo_equip = ctk.CTkComboBox(
            self.config_card, 
            state="readonly", 
            width=220,
            height=32,
            font=("Microsoft YaHei", 14),
            command=self.app.on_equip_change
        )
        self.combo_equip.grid(row=0, column=1, padx=(0, 30), pady=25, sticky="w")
        
        # 2. 规则选择
        self.lbl_rule = ctk.CTkLabel(
            self.config_card, 
            text="洗炼规则:", 
            font=("Microsoft YaHei", 16)
        )
        self.lbl_rule.grid(row=1, column=0, padx=(30, 10), pady=(0, 25), sticky="e")

        self.combo_affix = ctk.CTkComboBox(
            self.config_card, 
            state="readonly",
            width=220,
            height=32,
            font=("Microsoft YaHei", 14),
            command=self.app.on_affix_change
        )
        self.combo_affix.grid(row=1, column=1, padx=(0, 30), pady=(0, 25), sticky="w")


        # --- 操作按钮区域 ---
        # 按钮容器
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, pady=40)

        # 开始按钮 - 绿色系 (GitHub Green 风格)，胶囊形状
        self.btn_start = ctk.CTkButton(
            self.action_frame, 
            text="▶ 开始洗炼", 
            command=self.app.start_washing, 
            fg_color="#2EA043",           
            hover_color="#238636", 
            width=160, 
            height=45, 
            corner_radius=22,             
            font=("Microsoft YaHei", 16, "bold")
        )
        self.btn_start.pack(side="left", padx=15)

        # 停止按钮 - 红色系 (GitHub Red 风格)，胶囊形状
        self.btn_stop = ctk.CTkButton(
            self.action_frame, 
            text="⏹ 停止运行", 
            command=self.app.stop_washing, 
            fg_color="#DA3633",           
            hover_color="#B62324", 
            state="disabled",
            width=160, 
            height=45, 
            corner_radius=22,             
            font=("Microsoft YaHei", 16, "bold")
        )
        self.btn_stop.pack(side="left", padx=15)

        # --- 状态信息 ---
        self.lbl_status = ctk.CTkLabel(
            self, 
            text="状态: 就绪", 
            text_color="gray",
            font=("Microsoft YaHei", 13)
        )
        self.lbl_status.grid(row=3, column=0, pady=(5, 20))

    def update_status(self, text, is_running=False):
        self.lbl_status.configure(text=f"状态: {text}")
        if is_running:
            self.lbl_status.configure(text_color="#2EA043")  # 绿色
        elif "停止" in text or "错误" in text:
            self.lbl_status.configure(text_color="#DA3633")  # 红色
        else:
            self.lbl_status.configure(text_color="gray")
