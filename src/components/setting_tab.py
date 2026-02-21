import customtkinter as ctk

class SettingTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        self._init_ui()

    def _init_ui(self):
        self.frame_settings = ctk.CTkScrollableFrame(self)
        self.frame_settings.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 1. 调试模式
        self.app.debug_mode_var = ctk.BooleanVar(value=False)
        self.check_debug = ctk.CTkSwitch(self.frame_settings, text="调试模式 (保存OCR图片到 ocr_debug/)", variable=self.app.debug_mode_var)
        self.check_debug.pack(anchor="w", padx=20, pady=20)

        # 1.5 后台模式
        self.app.background_mode_var = ctk.BooleanVar(value=False)
        self.check_background = ctk.CTkSwitch(self.frame_settings, text="后台模式 (实验性, 窗口可被遮挡但不能最小化)", variable=self.app.background_mode_var)
        self.check_background.pack(anchor="w", padx=20, pady=10)
        
        # 3. 快捷键设置
        ctk.CTkLabel(self.frame_settings, text="全局快捷键设置:", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        hk_frame = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        hk_frame.pack(fill="x", padx=20)
        
        # Start Key
        ctk.CTkLabel(hk_frame, text="开始脚本:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.btn_bind_start = ctk.CTkButton(hk_frame, text=self.app.hk_start.upper(), width=120, fg_color="#555555", command=lambda: self.app.start_bind_hotkey("start"))
        self.btn_bind_start.grid(row=0, column=1, padx=5, pady=5)
        
        # Stop Key
        ctk.CTkLabel(hk_frame, text="停止脚本:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.btn_bind_stop = ctk.CTkButton(hk_frame, text=self.app.hk_stop.upper(), width=120, fg_color="#555555", command=lambda: self.app.start_bind_hotkey("stop"))
        self.btn_bind_stop.grid(row=1, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(hk_frame, text="点击按钮后按下任意键 (支持组合键)", text_color="gray", font=("Consolas", 10)).grid(row=2, column=0, columnspan=2, pady=5)

        # 4. 帮助与关于
        ctk.CTkLabel(self.frame_settings, text="帮助:", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        btn_guide = ctk.CTkButton(self.frame_settings, text="📖 查看操作指南", command=self.app._show_guide_window, fg_color="#444444")
        btn_guide.pack(anchor="w", padx=20, pady=5)
        
        # 版本信息
        ctk.CTkLabel(self.frame_settings, text="\n\nMedian Washer Pro v2.0\nOptimized for Game Experience", text_color="#555555").pack(side="bottom", pady=20)
