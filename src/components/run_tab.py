import customtkinter as ctk

class RunTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        self.grid_columnconfigure(1, weight=1)
        
        self._init_ui()

    def _init_ui(self):
        # 选择装备
        ctk.CTkLabel(self, text="当前装备:", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=20, pady=20, sticky="e")
        self.combo_equip = ctk.CTkComboBox(self, state="readonly", width=250, command=self.app.on_equip_change)
        self.combo_equip.grid(row=0, column=1, padx=20, pady=20, sticky="w")
        
        # 选择规则
        ctk.CTkLabel(self, text="当前规则:", font=("Microsoft YaHei", 14)).grid(row=1, column=0, padx=20, pady=20, sticky="e")
        self.combo_affix = ctk.CTkComboBox(self, state="readonly", width=250, command=self.app.on_affix_change)
        self.combo_affix.grid(row=1, column=1, padx=20, pady=20, sticky="w")
        
        # 开始/停止 按钮区
        self.frame_run_btns = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_run_btns.grid(row=2, column=0, columnspan=2, pady=30)
        
        self.btn_start = ctk.CTkButton(self.frame_run_btns, text="▶ 开始洗炼", command=self.app.start_washing, 
                                       fg_color="green", hover_color="darkgreen", width=140, height=50, font=("Microsoft YaHei", 16, "bold"))
        self.btn_start.pack(side="left", padx=20)

        self.btn_stop = ctk.CTkButton(self.frame_run_btns, text="⏹ 停止运行", command=self.app.stop_washing, 
                                      fg_color="red", hover_color="darkred", width=140, height=50, font=("Microsoft YaHei", 16, "bold"), state="disabled")
        self.btn_stop.pack(side="left", padx=20)
