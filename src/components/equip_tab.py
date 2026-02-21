import customtkinter as ctk

class EquipTab(ctk.CTkFrame):
    def __init__(self, master, app_context):
        super().__init__(master, fg_color="transparent")
        self.app = app_context
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # 内容区自适应

        self._init_ui()

    def _init_ui(self):
        # 顶部提示
        ctk.CTkLabel(self, text="管理已保存的装备定位配置", font=("Microsoft YaHei", 14, "bold"), text_color="silver").pack(pady=10)

        # 列表代替 ComboBox，更直观
        # 这里为了美观，我们简化为：上方是一个装备详情卡片，下方是操作按钮
        
        self.frame_equip_card = ctk.CTkFrame(self)
        self.frame_equip_card.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.frame_equip_card, text="在下拉框中选择要操作的装备:").pack(pady=5)
        self.combo_equip_mgr = ctk.CTkComboBox(self.frame_equip_card, state="readonly", width=300, command=None) # 这里只需要同步数据
        self.combo_equip_mgr.pack(pady=10)
        
        # 操作按钮区
        self.frame_equip_ops = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_equip_ops.pack(fill="x", padx=20, pady=20)
        
        # 第一排：主要操作
        self.btn_new_equip = ctk.CTkButton(self.frame_equip_ops, text="✚ 新建配置", width=120, height=35, command=self.app.new_equip_flow)
        self.btn_new_equip.grid(row=0, column=0, padx=10, pady=10)

        self.btn_edit_equip = ctk.CTkButton(self.frame_equip_ops, text="🎯 重新定位", width=120, height=35, fg_color="#555555", command=self.app.edit_current_equip)
        self.btn_edit_equip.grid(row=0, column=1, padx=10, pady=10)
        
        # 第二排：次要操作
        self.btn_rename_equip = ctk.CTkButton(self.frame_equip_ops, text="✎ 重命名", width=120, height=35, fg_color="#FFA500", command=self.app.rename_current_equip)
        self.btn_rename_equip.grid(row=1, column=0, padx=10, pady=10)
        
        self.btn_delete_equip = ctk.CTkButton(self.frame_equip_ops, text="🗑 删除配置", width=120, height=35, fg_color="darkred", command=self.app.delete_current_equip)
        self.btn_delete_equip.grid(row=1, column=1, padx=10, pady=10)
        
        # 底部说明
        text = "说明：\n1. 【新建】创建一个新的装备配置。\n2. 【重新定位】将重新录制坐标（支持游戏窗口移动）。\n3. 录制时请确保游戏窗口处于激活状态。"
        ctk.CTkLabel(self, text=text, justify="left", text_color="gray").pack(pady=20)
