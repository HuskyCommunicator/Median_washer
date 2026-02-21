import customtkinter as ctk

class SettingTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        self._init_ui()

    def _init_ui(self):
        # 滚动容器
        scroll_settings = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_settings.pack(fill="both", expand=True)
        
        # 居中内容区
        content_frame = ctk.CTkFrame(scroll_settings, fg_color="transparent")
        content_frame.pack(fill="x", padx=20, pady=20)
        content_frame.grid_columnconfigure(0, weight=1)

        # --- 顶部标题 ---
        self.lbl_title = ctk.CTkLabel(
            content_frame, 
            text="系统设置中心", 
            font=("Microsoft YaHei", 20, "bold")
        )
        self.lbl_title.grid(row=0, column=0, pady=(0, 20))


        # --- 卡片 1: 运行模式 ---
        self.card_mode = ctk.CTkFrame(content_frame, corner_radius=10)
        self.card_mode.grid(row=1, column=0, sticky="ew", pady=10)
        self.card_mode.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.card_mode, 
            text="运行模式配置", 
            font=("Microsoft YaHei", 12, "bold"), 
            text_color="gray"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        # 调试模式
        if not hasattr(self.app, 'debug_mode_var'):
            self.app.debug_mode_var = ctk.BooleanVar(value=False)
            
        self.check_debug = ctk.CTkSwitch(
            self.card_mode, 
            text="调试模式 (保存OCR截图)", 
            variable=self.app.debug_mode_var,
            font=("Microsoft YaHei", 13),
            command=self._on_debug_change # Optional: print log
        )
        self.check_debug.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # 后台模式 - 强制开启且不可修改
        if not hasattr(self.app, 'background_mode_var'):
            self.app.background_mode_var = ctk.BooleanVar(value=True)
        else:
            self.app.background_mode_var.set(True)



        # --- 卡片 2: 快捷键设置 ---
        self.card_hotkey = ctk.CTkFrame(content_frame, corner_radius=10)
        self.card_hotkey.grid(row=2, column=0, sticky="ew", pady=10)
        self.card_hotkey.grid_columnconfigure(1, weight=1) # 按钮列自适应

        ctk.CTkLabel(
            self.card_hotkey, 
            text="全局快捷键 (点击按钮后按下新按键)", 
            font=("Microsoft YaHei", 12, "bold"), 
            text_color="gray"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 15))
        
        # Start Key
        ctk.CTkLabel(self.card_hotkey, text="开始脚本:", font=("Microsoft YaHei", 13)).grid(row=1, column=0, sticky="e", padx=(20, 10), pady=10)
        self.btn_bind_start = ctk.CTkButton(
            self.card_hotkey, 
            text=self.app.hk_start.upper(), 
            command=lambda: self.app.start_bind_hotkey("start"),
            fg_color="#333333", border_color="gray", border_width=1,
            hover_color="#555555",
            width=150, height=35
        )
        self.btn_bind_start.grid(row=1, column=1, sticky="w", padx=10, pady=10)
        
        # Stop Key
        ctk.CTkLabel(self.card_hotkey, text="停止脚本:", font=("Microsoft YaHei", 13)).grid(row=2, column=0, sticky="e", padx=(20, 10), pady=10)
        self.btn_bind_stop = ctk.CTkButton(
            self.card_hotkey, 
            text=self.app.hk_stop.upper(), 
            command=lambda: self.app.start_bind_hotkey("stop"),
            fg_color="#333333", border_color="gray", border_width=1,
            hover_color="#555555",
            width=150, height=35
        )
        self.btn_bind_stop.grid(row=2, column=1, sticky="w", padx=10, pady=(10, 20))


        # --- 卡片 3: 帮助与关于 ---
        self.card_about = ctk.CTkFrame(content_frame, corner_radius=10)
        self.card_about.grid(row=3, column=0, sticky="ew", pady=10)
        self.card_about.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.card_about, 
            text="关于软件", 
            font=("Microsoft YaHei", 12, "bold"), 
            text_color="gray"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        self.btn_guide = ctk.CTkButton(
            self.card_about, 
            text="📖 查看操作指南", 
            command=self.app._show_guide_window,
            fg_color="#1F6FEB",
            hover_color="#1158C7",
            height=40,
            font=("Microsoft YaHei", 13, "bold")
        )
        self.btn_guide.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        text_ver = "Median Washer Pro v2.0\nDesigned for Median XL Sigma"
        ctk.CTkLabel(self.card_about, text=text_ver, text_color="#666666", font=("Consolas", 10)).grid(row=2, column=0, pady=(0, 15))

    def _on_debug_change(self):
        print(f"调试模式已切换: {self.app.debug_mode_var.get()}")
