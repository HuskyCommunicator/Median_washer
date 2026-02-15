import customtkinter as ctk
import threading
import sys
import os
import time
import io
import queue
import json
try:
    import keyboard
except ImportError:
    keyboard = None
from src.gear_washer.washer import GearWasher
from src.gear_washer.db_helper import SimpleDB
from config.affix_config import DEFAULT_CONFIGS
from complex_editor import ComplexRuleEditor

# 设置主题
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TextRedirector:
    """重定向 stdout 到 GUI 的文本框"""
    def __init__(self, text_widget, tag="stdout"):
        self.text_widget = text_widget
        self.tag = tag
        self.queue = queue.Queue()

    def write(self, str_val):
        self.queue.put(str_val)

    def flush(self):
        pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("洗炼助手 Pro")
        self.geometry("700x550")
        
        # 数据库 & 洗炼核心
        self.db = SimpleDB()
        
        # 获取基础路径 (兼容 IDE 运行和打包后的 Exe)
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe，sys.executable 指向 exe 文件所在目录
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # 如果是脚本运行
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        base_dir = self.base_dir # 为了兼容旧代码引用

        self.ocr_path = os.path.join(base_dir, 'OCR', 'tesseract.exe')
        
        # 设置 TESSDATA_PREFIX 环境变量，防止 Tesseract 找不到语言包
        # 尤其是在打包后的环境中，必须显式指定
        tessdata_path = os.path.join(base_dir, 'OCR', 'tessdata')
        # 即使是 Windows，Tesseract 依然可能被 POSIX 路径习惯影响，尤其是 MSYS2 编译的版本
        # 确保路径不以反斜杠结尾，并且尝试转换为绝对路径
        tessdata_path = os.path.abspath(tessdata_path)
        
        # 关键修正：有些版本的 Tesseract 期望 TESSDATA_PREFIX 指向 tessdata 的*父目录*，
        # 而有些期望指向 tessdata *本身*。
        # 报错信息 "Warning: TESSDATA_PREFIX ...tessdata does not exist" 非常奇怪，
        # 因为我们刚才确认它存在。这通常暗示 Tesseract 内部可能再次拼接了 'tessdata'。
        # 比如：我们设了 C:\...\tessdata，它去找 C:\...\tessdata\tessdata
        
        # 策略：如果目录存在，我们设为它的父目录试一下，或者保持原样。
        # 看到报错 "Error opening data file .../tessdata/chi_sim.traineddata"
        # 它的默认搜索路径是写死的 /home/debian/... 这是一个典型的 MSYS2/MinGW 编译路径泄露。
        
        # 强制设置环境变量
        os.environ['TESSDATA_PREFIX'] = tessdata_path
        
        # 二次确认：有些 tesseract 版本如果不灵，试试指向父目录
        # os.environ['TESSDATA_PREFIX'] = os.path.dirname(tessdata_path) 
        
        print(f"DEBUG: TESSDATA_PREFIX set to: {os.environ['TESSDATA_PREFIX']}")
        print(f"DEBUG: Checking if path exists: {os.path.exists(tessdata_path)}")
        
        self.washer = None # 将在运行时实例化
        self.running = False
        self.worker_thread = None
        self.current_rule_content = "" # 存储当前选择/编辑的规则内容(JSON string 或普通 string)
        self.current_affix_id = None   # 存储当前选择的规则ID (如果是DB类型)
        self.current_affix_source = None # 'FILE' or 'DB'

        # 布局配置
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1) # 日志区域自适应高度
        
        # 从数据库加载快捷键配置
        self.hk_start = self.db.get("hotkey_start", "end")
        self.hk_stop = self.db.get("hotkey_stop", "home")

        self._init_ui()
        self._load_data()
        
        # 注册全局快捷键
        self._register_hotkeys()
        
        # 定时检查日志输出
        self.after(100, self._check_log_queue)

    def _register_hotkeys(self):
        """注册全局快捷键"""
        if not keyboard:
            print("警告: 键盘库未安装，快捷键不可用")
            return
            
        try:
            # 先清除旧的热键
            try:
                keyboard.unhook_all_hotkeys()
            except: pass
            
            keyboard.add_hotkey(self.hk_start, self._on_start_hotkey)
            keyboard.add_hotkey(self.hk_stop, self._on_stop_hotkey)
            
            print(f"全局快捷键已注册: 按 [{self.hk_start}] 开始, 按 [{self.hk_stop}] 停止")
        except Exception as e:
            print(f"快捷键注册失败 (可能是键名无效): {e}")

    def _on_start_hotkey(self):
        """处理 Start 键按下"""
        if not self.running:
            # 在主线程调用 start, 避免线程安全问题
            self.after(0, self.start_washing)

    def _on_stop_hotkey(self):
        """处理 Stop 键按下"""
        if self.running:
            print(">>> 检测到停止快捷键 <<<")
            self.after(0, self.stop_washing)

    def _init_ui(self):
        # 使用 TabView 进行主要布局
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.grid_rowconfigure(0, weight=1) # TabView 区域自适应高度
        self.grid_rowconfigure(1, weight=0) # 状态栏高度固定

        # 创建 Tabs
        self.tab_run = self.tab_view.add("运行控制")
        self.tab_equip = self.tab_view.add("装备管理")
        self.tab_rule = self.tab_view.add("规则管理")
        self.tab_setting = self.tab_view.add("系统设置")
        
        # --- TAB 1: 运行控制 ---
        self._init_tab_run()

        # --- TAB 2: 装备管理 ---
        self._init_tab_equip()
        
        # --- TAB 3: 规则管理 ---
        self._init_tab_rule()
        
        # --- TAB 4: 系统设置 ---
        self._init_tab_setting()

        # 公共日志区域 (放在 TabView 下方)
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.grid_rowconfigure(1, weight=1) # 增加日志区域权重

        self.lbl_log_title = ctk.CTkLabel(self.log_frame, text="运行日志", font=("Microsoft YaHei", 12))
        self.lbl_log_title.pack(anchor="w", padx=5, pady=2)

        self.log_box = ctk.CTkTextbox(self.log_frame, font=("Consolas", 12), height=150)
        self.log_box.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 底部状态栏
        self.status_bar = ctk.CTkFrame(self, height=25)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=2)
        
        self.lbl_status = ctk.CTkLabel(self.status_bar, text="就绪 (快捷键: END开始 / HOME停止)", text_color="gray", font=("Microsoft YaHei", 12))
        self.lbl_status.pack(side="left", padx=10)

        # 重定向输出
        self.redirector = TextRedirector(self.log_box)
        sys.stdout = self.redirector

    def _init_tab_run(self):
        """初始化运行 Tab"""
        tr = self.tab_run
        tr.grid_columnconfigure(1, weight=1)
        
        # 选择装备
        ctk.CTkLabel(tr, text="当前装备:", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=20, pady=20, sticky="e")
        self.combo_equip = ctk.CTkComboBox(tr, state="readonly", width=250, command=self.on_equip_change)
        self.combo_equip.grid(row=0, column=1, padx=20, pady=20, sticky="w")
        
        # 选择规则
        ctk.CTkLabel(tr, text="当前规则:", font=("Microsoft YaHei", 14)).grid(row=1, column=0, padx=20, pady=20, sticky="e")
        self.combo_affix = ctk.CTkComboBox(tr, state="readonly", width=250, command=self.on_affix_change)
        self.combo_affix.grid(row=1, column=1, padx=20, pady=20, sticky="w")
        
        # 开始/停止 按钮区
        self.frame_run_btns = ctk.CTkFrame(tr, fg_color="transparent")
        self.frame_run_btns.grid(row=2, column=0, columnspan=2, pady=30)
        
        self.btn_start = ctk.CTkButton(self.frame_run_btns, text="▶ 开始洗炼", command=self.start_washing, 
                                       fg_color="green", hover_color="darkgreen", width=140, height=50, font=("Microsoft YaHei", 16, "bold"))
        self.btn_start.pack(side="left", padx=20)

        self.btn_stop = ctk.CTkButton(self.frame_run_btns, text="⏹ 停止运行", command=self.stop_washing, 
                                      fg_color="red", hover_color="darkred", width=140, height=50, font=("Microsoft YaHei", 16, "bold"), state="disabled")
        self.btn_stop.pack(side="left", padx=20)
        
        # 提示信息
        ctk.CTkLabel(tr, text="提示: 开始后请不要操作鼠标，按 HOME 键可紧急停止", text_color="gray").grid(row=3, column=0, columnspan=2, pady=10)

    def _init_tab_equip(self):
        """初始化装备管理 Tab"""
        te = self.tab_equip
        te.grid_columnconfigure(0, weight=1)
        te.grid_rowconfigure(0, weight=1) # 内容区自适应
        
        # 顶部提示
        ctk.CTkLabel(te, text="管理已保存的装备定位配置", font=("Microsoft YaHei", 14, "bold"), text_color="silver").pack(pady=10)

        # 列表代替 ComboBox，更直观
        # 由于 CustomTkinter 没有 Listbox，我们用 ScrollableFrame + Buttons 模拟，或者复用 ComboBox 逻辑方便点
        # 这里为了美观，我们简化为：上方是一个装备详情卡片，下方是操作按钮
        
        self.frame_equip_card = ctk.CTkFrame(te)
        self.frame_equip_card.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.frame_equip_card, text="在下拉框中选择要操作的装备:").pack(pady=5)
        self.combo_equip_mgr = ctk.CTkComboBox(self.frame_equip_card, state="readonly", width=300, command=None) # 这里只需要同步数据
        self.combo_equip_mgr.pack(pady=10)
        
        # 操作按钮区
        self.frame_equip_ops = ctk.CTkFrame(te, fg_color="transparent")
        self.frame_equip_ops.pack(fill="x", padx=20, pady=20)
        
        # 第一排：主要操作
        self.btn_new_equip = ctk.CTkButton(self.frame_equip_ops, text="✚ 新建配置", width=120, height=35, command=self.new_equip_flow)
        self.btn_new_equip.grid(row=0, column=0, padx=10, pady=10)

        self.btn_edit_equip = ctk.CTkButton(self.frame_equip_ops, text="🎯 重新定位", width=120, height=35, fg_color="#555555", command=self.edit_current_equip)
        self.btn_edit_equip.grid(row=0, column=1, padx=10, pady=10)
        
        # 第二排：次要操作
        self.btn_rename_equip = ctk.CTkButton(self.frame_equip_ops, text="✎ 重命名", width=120, height=35, fg_color="#FFA500", command=self.rename_current_equip)
        self.btn_rename_equip.grid(row=1, column=0, padx=10, pady=10)
        
        self.btn_delete_equip = ctk.CTkButton(self.frame_equip_ops, text="🗑 删除配置", width=120, height=35, fg_color="darkred", command=self.delete_current_equip)
        self.btn_delete_equip.grid(row=1, column=1, padx=10, pady=10)
        
        # 底部说明
        text = "说明：\n1. 【新建】创建一个新的装备配置。\n2. 【重新定位】将重新录制坐标（支持游戏窗口移动）。\n3. 录制时请确保游戏窗口处于激活状态。"
        ctk.CTkLabel(te, text=text, justify="left", text_color="gray").pack(pady=20)

    def _init_tab_rule(self):
        """初始化规则管理 Tab"""
        tr = self.tab_rule
        
        # 添加滚动容器以适应小窗口
        scroll_rule = ctk.CTkScrollableFrame(tr)
        scroll_rule.pack(fill="both", expand=True, padx=5, pady=5)

        # 顶部标题
        ctk.CTkLabel(scroll_rule, text="词缀规则管理中心", font=("Microsoft YaHei", 16, "bold"), text_color="silver").pack(pady=(15, 5))
        
        # 1. 规则选择区
        self.frame_rule_card = ctk.CTkFrame(scroll_rule)
        self.frame_rule_card.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(self.frame_rule_card, text="当前编辑的规则:").pack(pady=(10, 2))
        self.combo_affix_mgr = ctk.CTkComboBox(self.frame_rule_card, state="readonly", width=320, command=self.on_affix_mgr_change)
        self.combo_affix_mgr.pack(pady=5)
        
        # 简易预览
        self.lbl_rule_preview = ctk.CTkLabel(self.frame_rule_card, text="规则内容预览...", text_color="gray", font=("Consolas", 10))
        self.lbl_rule_preview.pack(pady=(0, 10))

        # 2. 核心操作区
        self.frame_rule_ops = ctk.CTkFrame(scroll_rule, fg_color="transparent")
        self.frame_rule_ops.pack(fill="x", padx=15, pady=5)
        
        # 使用 grid 布局，2列
        self.frame_rule_ops.grid_columnconfigure(0, weight=1)
        self.frame_rule_ops.grid_columnconfigure(1, weight=1)
        
        # 第1行：主要编辑
        self.btn_advanced = ctk.CTkButton(self.frame_rule_ops, text="📝 编辑详情(JSON)", height=40, fg_color="#555555", command=self.open_advanced_editor)
        self.btn_advanced.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # 第2行：新建与重命名
        self.btn_new_rule = ctk.CTkButton(self.frame_rule_ops, text="➕ 新增规则", height=35, command=self.create_new_rule)
        self.btn_new_rule.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        self.btn_rename_rule = ctk.CTkButton(self.frame_rule_ops, text="✎ 重命名", height=35, fg_color="#FFA500", command=self.rename_current_rule)
        self.btn_rename_rule.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # 第3行：删除与导入 (一行显示，节省纵向空间防止遮挡)
        self.btn_delete_rule = ctk.CTkButton(self.frame_rule_ops, text="🗑 删除规则", height=35, fg_color="darkred", command=self.delete_current_rule)
        self.btn_delete_rule.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        self.btn_load_def = ctk.CTkButton(self.frame_rule_ops, text="📥 导入默认库", height=35, fg_color="#333333", command=self.load_defaults)
        self.btn_load_def.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # 移除单独的 frame_tools，原本的按钮已整合进 grid
        # self.frame_tools = ctk.CTkFrame(tr, fg_color="transparent") ...

    def _init_tab_setting(self):
        """初始化系统设置 Tab"""
        ts = self.tab_setting
        
        self.frame_settings = ctk.CTkScrollableFrame(ts)
        self.frame_settings.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 1. 调试模式
        self.debug_mode_var = ctk.BooleanVar(value=False)
        self.check_debug = ctk.CTkSwitch(self.frame_settings, text="调试模式 (保存OCR图片到 ocr_debug/)", variable=self.debug_mode_var)
        self.check_debug.pack(anchor="w", padx=20, pady=20)

        # 1.5 后台模式
        self.background_mode_var = ctk.BooleanVar(value=False)
        self.check_background = ctk.CTkSwitch(self.frame_settings, text="后台模式 (实验性, 窗口可被遮挡但不能最小化)", variable=self.background_mode_var)
        self.check_background.pack(anchor="w", padx=20, pady=10)
        
        # 3. 快捷键设置
        ctk.CTkLabel(self.frame_settings, text="全局快捷键设置:", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        hk_frame = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        hk_frame.pack(fill="x", padx=20)
        
        # Start Key
        ctk.CTkLabel(hk_frame, text="开始脚本:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.btn_bind_start = ctk.CTkButton(hk_frame, text=self.hk_start.upper(), width=120, fg_color="#555555", command=lambda: self.start_bind_hotkey("start"))
        self.btn_bind_start.grid(row=0, column=1, padx=5, pady=5)
        
        # Stop Key
        ctk.CTkLabel(hk_frame, text="停止脚本:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.btn_bind_stop = ctk.CTkButton(hk_frame, text=self.hk_stop.upper(), width=120, fg_color="#555555", command=lambda: self.start_bind_hotkey("stop"))
        self.btn_bind_stop.grid(row=1, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(hk_frame, text="点击按钮后按下任意键 (支持组合键)", text_color="gray", font=("Consolas", 10)).grid(row=2, column=0, columnspan=2, pady=5)

        # 4. 帮助与关于
        ctk.CTkLabel(self.frame_settings, text="帮助:", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        btn_guide = ctk.CTkButton(self.frame_settings, text="📖 查看操作指南", command=self._show_guide_window, fg_color="#444444")
        btn_guide.pack(anchor="w", padx=20, pady=5)
        
        # 版本信息
        ctk.CTkLabel(self.frame_settings, text="\n\nMedian Washer Pro v2.0\nOptimized for Game Experience", text_color="#555555").pack(side="bottom", pady=20)

    def start_bind_hotkey(self, key_type):
        """开始捕获快捷键，阻塞式但不冻结GUI"""
        
        # 1. 确定目标按钮和原始文本
        if key_type == "start":
            target_btn = self.btn_bind_start
        else:
            target_btn = self.btn_bind_stop
            
        # 2. 更新UI提示
        target_btn.configure(text="请按下组合键...", fg_color="#FFA500")
        self.btn_bind_start.configure(state="disabled")
        self.btn_bind_stop.configure(state="disabled")
        
        # 3. 启动监听线程
        def listening_thread():
            try:
                # 简单防抖，防止立刻捕获到这就点击的 Enter
                time.sleep(0.3)
                
                print(f"正在等待输入 {key_type} 快捷键...")
                
                # 核心：使用 keyboard.read_hotkey() 阻塞等待
                # suppress=False 表示按键依然会传递给系统，不会被吞掉
                hotkey = keyboard.read_hotkey(suppress=False)
                
                # 捕获完成后，在主线程更新
                self.after(0, lambda: self._on_hotkey_captured(key_type, hotkey))
                
            except Exception as e:
                print(f"快捷键捕获异常: {e}")
                self.after(0, self._reset_bind_ui)

        threading.Thread(target=listening_thread, daemon=True).start()

    def _on_hotkey_captured(self, key_type, hotkey_str):
        """捕获完成后的回调"""
        if not hotkey_str:
            print("捕获到的快捷键为空")
            self._reset_bind_ui()
            return
            
        final_hk = hotkey_str.lower()
        print(f"捕获成功: {final_hk}")

        # 保存到数据库和内存
        if key_type == "start":
            self.hk_start = final_hk
            self.db.set("hotkey_start", final_hk)
        else:
            self.hk_stop = final_hk
            self.db.set("hotkey_stop", final_hk)
            
        # 恢复UI 并 重新注册
        self._reset_bind_ui()
        self._register_hotkeys()

    def _reset_bind_ui(self, *args):
        """恢复按钮状态"""
        try:
            self.btn_bind_start.configure(state="normal", text=self.hk_start.upper(), fg_color="#555555")
            self.btn_bind_stop.configure(state="normal", text=self.hk_stop.upper(), fg_color="#555555")
        except: pass

    def _show_guide_window(self):
        """显示操作手册窗口"""
        try:
            guide_path = os.path.join(self.base_dir, '操作手册.md')
            if not os.path.exists(guide_path):
                guide_content = "找不到操作手册.md 文件，请检查路径。"
            else:
                with open(guide_path, 'r', encoding='utf-8') as f:
                    guide_content = f.read()
        except Exception as e:
            guide_content = f"读取操作手册失败: {e}"

        # 创建新窗口
        guide_window = ctk.CTkToplevel(self)
        guide_window.title("操作指南 - Median Washer Pro")
        guide_window.geometry("800x600")
        
        # 总是置顶
        guide_window.attributes("-topmost", True)
        
        # 文本显示区域
        textbox = ctk.CTkTextbox(guide_window, font=("Consolas", 14))
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        textbox.insert("0.0", guide_content)
        textbox.configure(state="disabled") # 只读

        # 聚焦窗口
        guide_window.focus()

        
    def on_speed_change(self, value):
        self.speed_val_label.configure(text=f"{value:.1f} 秒")

    def on_affix_mgr_change(self, choice):
        """Tab3 规则管理选择变化 - 代理给主逻辑"""
        self.on_affix_change(choice)

    def _check_log_queue(self):
        """定期从队列读取日志更新到界面"""
        try:
            while True:
                text = self.redirector.queue.get_nowait()
                self.log_box.insert("end", text)
                self.log_box.see("end")
        except queue.Empty:
            pass
        self.after(100, self._check_log_queue)

    def _load_data(self):
        """加载数据"""
        # 1. 加载装备
        equips = self.db.list_equipment_types()
        self.equip_map = {name: eid for eid, name in equips}
        equip_names = [name for _, name in equips]
        
        # 更新 Tab1 选择框
        self.combo_equip.configure(values=equip_names)
        # 更新 Tab2 管理下拉框
        self.combo_equip_mgr.configure(values=equip_names)

        if equip_names:
            current = self.combo_equip.get()
            if current not in equip_names:
                self.combo_equip.set(equip_names[0])
                self.combo_equip_mgr.set(equip_names[0])
            else:
                 self.combo_equip_mgr.set(current)
        else:
            self.combo_equip.set("无配置")
            self.combo_equip_mgr.set("无配置")

        # 2. 规则数据
        self.affix_data_map = {} # name -> content
        self.affix_id_map = {}   # name -> id (for DB items)
        self.affix_source_map = {} # name -> 'DB'
        affix_names = []
        
        db_affixes = self.db.get_all_affixes()
        for aid, content, desc in db_affixes:
            display = desc if desc else f"规则_{aid}"
            orig_display = display
            idx = 1
            while display in self.affix_data_map:
                display = f"{orig_display} ({idx})"
                idx += 1
                
            self.affix_data_map[display] = content
            self.affix_id_map[display] = aid
            self.affix_source_map[display] = 'DB'
            affix_names.append(display)
            
        # 更新 Tab1 选择框
        self.combo_affix.configure(values=affix_names)
        # 更新 Tab3 管理下拉框
        self.combo_affix_mgr.configure(values=affix_names)
        
        # 尝试恢复
        current = self.combo_affix.get()
        if current in affix_names:
             self.on_affix_change(current)
             self.combo_affix_mgr.set(current)
             self.on_affix_mgr_change(current)
        elif affix_names:
            self.combo_affix.set(affix_names[0])
            self.on_affix_change(affix_names[0])
            self.combo_affix_mgr.set(affix_names[0])
            self.on_affix_mgr_change(affix_names[0])
        else:
            self.combo_affix.set("")
            self.combo_affix_mgr.set("")
            self.current_rule_content = ""
            self.lbl_rule_preview.configure(text="")

    def on_equip_change(self, choice):
        print(f"已选择装备: {choice}")
        self.combo_equip_mgr.set(choice)

    def on_affix_change(self, choice):
        if choice in self.affix_data_map:
            content = self.affix_data_map[choice]
            if isinstance(content, (list, dict)):
                content = json.dumps(content, ensure_ascii=False)
            
            self.current_rule_content = str(content)
            self.current_affix_id = self.affix_id_map.get(choice)
            self.current_affix_source = self.affix_source_map.get(choice)
            
            # 1. 更新预览 (原Tab3逻辑移动到这里)
            preview = str(content)
            if len(preview) > 50: preview = preview[:47] + "..."
            try:
                self.lbl_rule_preview.configure(text=preview)
            except: pass

            # 2. 同步 UI (仅设置值，不触发回调防止死循环)
            if self.combo_affix_mgr.get() != choice:
                self.combo_affix_mgr.set(choice)
            
            if self.combo_affix.get() != choice:
                self.combo_affix.set(choice)

    def open_advanced_editor(self):
        current_text = self.current_rule_content.strip()
        initial_data = None
        if current_text.startswith("[") and current_text.endswith("]"):
            try:
                initial_data = json.loads(current_text)
            except:
                pass
        
        def on_save(data):
            if self.current_affix_id is None:
                print("错误: 无法保存，因为未关联到数据库ID (可能是内置规则或尚未保存)")
                return
                
            json_str = json.dumps(data, ensure_ascii=False)
            
            # 直接更新数据库
            # 注意: 这里使用 self.combo_affix_mgr.get() 获取当前名称，保持名称不变
            current_name = self.combo_affix_mgr.get()
            success = self.db.update_affix(self.current_affix_id, json_str, current_name)
            
            if success:
                print(f"规则 [{current_name}] 已成功更新！")
                self._load_data()
                # 恢复选中状态
                self.combo_affix_mgr.set(current_name)
                self.on_affix_mgr_change(current_name)
            else:
                print("保存失败。")
            
        ComplexRuleEditor(self, initial_data=initial_data, callback=on_save)


    def create_new_rule(self):
        """新建规则"""
        def on_create(data):
            if not data: return
            
            import customtkinter as ctk 
            dialog = ctk.CTkInputDialog(text="请输入新规则名称:", title="保存新规则")
            name = dialog.get_input()
            if name:
                json_str = json.dumps(data, ensure_ascii=False)
                success = self.db.add_affix(json_str, name)
                if success:
                    print(f"新规则 [{name}] 已保存。")
                    self._load_data() 
                    self.combo_affix.set(name)
                    self.on_affix_change(name)
                else:
                    print(f"保存失败，可能是名称重复。")

        ComplexRuleEditor(self, initial_data=None, callback=on_create)


    def rename_current_rule(self):
        choice = self.combo_affix_mgr.get() # 从管理Tab获取
        # ... 逻辑基本同前

        if not choice: return
        if self.current_affix_id is None: return

        import customtkinter as ctk 
        dialog = ctk.CTkInputDialog(text=f"重命名 '{choice}' 为:", title="重命名规则")
        new_name = dialog.get_input()
        if new_name and new_name != choice:
            try:
                success = self.db.rename_affix(self.current_affix_id, new_name)
                if success:
                    print(f"规则已重命名为: {new_name}")
                    self._load_data()
                else:
                    print("重命名失败。")
            except Exception as e:
                print(f"重命名出错: {e}")

    def delete_current_rule(self):
        choice = self.combo_affix_mgr.get()
        if not choice: return
        if self.current_affix_id is None: return

        try:
            self.db.delete_affix(self.current_affix_id)
            print(f"规则 [{choice}] 已删除。")
            self._load_data()
        except Exception as e:
            print(f"删除失败: {e}")

    def load_defaults(self):
        """手动导入默认规则"""
        if not DEFAULT_CONFIGS:
            print("错误：配置文件中没有默认规则。")
            return
            
        print("正在导入默认规则到数据库...")
        self.db.migrate_defaults(DEFAULT_CONFIGS)
        print("导入完成！")
        self._load_data()

    def new_equip_flow(self):
        """新建装备流程"""
        import customtkinter as ctk 
        dialog = ctk.CTkInputDialog(text="请输入新装备名称:", title="新建配置")
        name = dialog.get_input()
        if not name: return
        
        self._run_calibrate_logic(name, is_update=False)

    def _run_calibrate_logic(self, name, is_update=False):
        """通用的定位逻辑"""
        print(f"=== 开始定位: {name} ===")
        print("请在控制台/日志查看定位提示，并按【空格键】确认坐标...")
        
        try:
            self.btn_new_equip.configure(state="disabled")
            self.btn_edit_equip.configure(state="disabled")
        except: pass
        
        def run_calibrate():
            try:
                # 使用默认配置
                temp_washer = GearWasher(tesseract_cmd=self.ocr_path, 
                                        debug_mode=self.debug_mode_var.get())
                pos_data = temp_washer.calibrate_ui() 
                
                self.db.save_equipment_type(
                    name=name,
                    gear_pos=pos_data['gear_pos'],
                    affix_points=pos_data['affix_points'],
                    window_title=pos_data.get('window_title')
                )
                
                print(f"配置 [{name}] 保存成功！")
                self.after(0, self._load_data) 
            except Exception as e:
                print(f"定位失败: {e}")
            finally:
                self.after(0, lambda: self._enable_equip_buttons())
                
        threading.Thread(target=run_calibrate, daemon=True).start()

    def _enable_equip_buttons(self):
        try:
            self.btn_new_equip.configure(state="normal")
            self.btn_edit_equip.configure(state="normal")
        except: pass

    def edit_current_equip(self):
        """编辑(覆盖)当前装备定位 - 从Tab2调用"""
        equip_name = self.combo_equip_mgr.get()
        if not equip_name or equip_name == "无配置" or equip_name == "请选择...":
            print("错误：请先在下拉框选择一个配置！")
            return
            
        eid = self.equip_map.get(equip_name)
        if not eid: return

        print(f"=== 准备重新定位: {equip_name} ===")
        self._run_calibrate_logic(equip_name, is_update=True)

    def rename_current_equip(self):
        equip_name = self.combo_equip_mgr.get()
        if not equip_name or equip_name == "无配置": return
        eid = self.equip_map.get(equip_name)
        if not eid: return

        import customtkinter as ctk 
        dialog = ctk.CTkInputDialog(text=f"重命名 '{equip_name}' 为:", title="重命名装备")
        new_name = dialog.get_input()
        if new_name and new_name != equip_name:
            if self.db.rename_equipment_type(eid, new_name):
                print(f"装备已重命名为: {new_name}")
                self._load_data()
            else:
                print("重命名失败。")
    
    def delete_current_equip(self):
        equip_name = self.combo_equip_mgr.get()
        if not equip_name or equip_name == "无配置": return
        eid = self.equip_map.get(equip_name)
        if not eid: return
        
        self.db.delete_equipment_type(eid)
        print(f"装备 [{equip_name}] 已删除。")
        self._load_data()

    def start_washing(self):
        if self.running: return
        
        # update interval from slider
        # ... logic inside ...
        
        equip_name = self.combo_equip.get()
        if not equip_name or equip_name == "无配置":
             print("错误：请先选择装备配置！")
             return

        affix_rule_str = self.current_rule_content
        if not affix_rule_str:
            print("错误：当前未加载任何词缀规则！")
            return
        
        # ... (rest of start_washing logic) ...

        try:
            eid = self.equip_map.get(equip_name)
            if not eid:
                print(f"错误：内部映射错误，找不到装备 [{equip_name}] 的ID")
                return
                 
            cfg = self.db.get_equipment_type_by_id(eid)
            
            if not cfg:
                print(f"错误：找不到装备 [{equip_name}] 的数据库记录")
                return
                
            debug_mode = self.debug_mode_var.get()
            bg_mode = self.background_mode_var.get()
            
            print(f"正在启动... 调试: {debug_mode}, 后台模式: {bg_mode}, 停止键: {self.hk_stop}")
                
            self.washer = GearWasher(tesseract_cmd=self.ocr_path, 
                                    debug_mode=debug_mode,
                                    background_mode=bg_mode,
                                    stop_key=self.hk_stop)
            
            self.washer.gear_pos = cfg['gear_pos']
            self.washer.window_title = cfg.get('window_title')
            # 使用极速模式: 0.05-0.1s
            self.washer.interval = 0.1 
            
            p1, p2 = cfg['affix_points']
            x = min(p1[0], p2[0])
            y = min(p1[1], p2[1])
            w = abs(p2[0] - p1[0])
            h = abs(p2[1] - p1[1])
            self.washer.affix_region = (x, y, w, h)
            
            # Parsing JSON rule
            final_conditions = affix_rule_str
            if affix_rule_str.startswith("[") or affix_rule_str.startswith("{"):
                try:
                    final_conditions = json.loads(affix_rule_str)
                except json.JSONDecodeError:
                    pass
            self.washer.conditions = final_conditions
            
        except Exception as e:
            print(f"初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return

        self.running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="运行中... (按HOME停止)", text_color="green")
        
        self.worker_thread = threading.Thread(target=self._run_washer_loop, daemon=True)
        self.worker_thread.start()
        
    def stop_washing(self):
        if self.washer:
            self.washer.stop()
        self.running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="已停止", text_color="gray")

    def _run_washer_loop(self):
        print("=== 洗炼开始 ===")
        try:
            self.washer.run()
        except Exception as e:
            print(f"运行时错误: {e}")
        finally:
            self.running = False
            print("=== 洗炼结束 ===")
            self.after(0, self._on_process_finish)

    def _on_process_finish(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="已结束", text_color="gray")

if __name__ == '__main__':
    app = App()
    app.mainloop()
