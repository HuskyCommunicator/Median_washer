import customtkinter as ctk

class EquipTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # 居中

        self._init_ui()

    def _init_ui(self):
        # 主容器 - 居中卡片
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.center_frame.grid_columnconfigure(0, weight=1)
        
        # --- 顶部标题 ---
        self.lbl_title = ctk.CTkLabel(
            self.center_frame, 
            text="装备配置管理", 
            font=("Microsoft YaHei", 20, "bold")
        )
        self.lbl_title.grid(row=0, column=0, pady=(10, 20))

        # --- 功能卡片 1: 选择与新建 ---
        self.card_select = ctk.CTkFrame(self.center_frame, corner_radius=10)
        self.card_select.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.card_select.grid_columnconfigure(0, weight=1)
        self.card_select.grid_columnconfigure(1, weight=0)

        # 标签
        ctk.CTkLabel(
            self.card_select, 
            text="当前选择的装备", 
            font=("Microsoft YaHei", 12, "bold"), 
            text_color="gray"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # 组合框
        self.combo_equip_mgr = ctk.CTkComboBox(
            self.card_select, 
            height=35,
            font=("Microsoft YaHei", 14),
            state="readonly",
            # command=self._on_combo_change # 暂时不绑定，外部可能有联动
        )
        self.combo_equip_mgr.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        # 新建按钮 (放右边)
        self.btn_new_equip = ctk.CTkButton(
            self.card_select, 
            text="✚ 新建配置", 
            command=self.app.new_equip_flow,
            fg_color="#2EA043",           # GitHub Green
            hover_color="#238636",
            width=120,
            height=35,
            font=("Microsoft YaHei", 13, "bold")
        )
        self.btn_new_equip.grid(row=1, column=1, padx=15, pady=(0, 15))


        # --- 功能卡片 2: 操作 ---
        self.card_ops = ctk.CTkFrame(self.center_frame, corner_radius=10)
        self.card_ops.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        # 3列均分
        self.card_ops.grid_columnconfigure(0, weight=1)
        self.card_ops.grid_columnconfigure(1, weight=1)
        self.card_ops.grid_columnconfigure(2, weight=1)


        # 重新定位
        self.btn_edit_equip = ctk.CTkButton(
            self.card_ops, 
            text="🎯 重新定位", 
            command=self.app.edit_current_equip,
            fg_color="#1F6FEB",           # GitHub Blue
            hover_color="#1158C7",
            height=40,
            font=("Microsoft YaHei", 13, "bold")
        )
        self.btn_edit_equip.grid(row=0, column=0, padx=10, pady=20, sticky="ew")
        
        # 重命名
        self.btn_rename_equip = ctk.CTkButton(
            self.card_ops, 
            text="✎ 重命名", 
            command=self.app.rename_current_equip,
            fg_color="#6E7681",           # GitHub Gray
            hover_color="#57606A",
            height=40,
            font=("Microsoft YaHei", 13, "bold")
        )
        self.btn_rename_equip.grid(row=0, column=1, padx=10, pady=20, sticky="ew")
        
        # 删除
        self.btn_delete_equip = ctk.CTkButton(
            self.card_ops, 
            text="🗑 删除配置", 
            command=self.app.delete_current_equip,
            fg_color="#DA3633",           # GitHub Red
            hover_color="#B62324",
            height=40,
            font=("Microsoft YaHei", 13, "bold")
        )
        self.btn_delete_equip.grid(row=0, column=2, padx=10, pady=20, sticky="ew")
        
        # --- 底部说明 ---
        self.lbl_tip = ctk.CTkLabel(
            self.center_frame, 
            text="说明：\n1. 【新建】创建一个新的装备配置。\n2. 【重新定位】将重新录制坐标（支持游戏窗口移动）。\n3. 录制时请确保游戏窗口处于激活状态。",
            justify="left", 
            text_color="gray",
            font=("Microsoft YaHei", 12)
        )
        self.lbl_tip.grid(row=3, column=0, pady=20)
