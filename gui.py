import customtkinter as ctk
import threading
import sys
import os
import time
import io
import queue
import json
import webbrowser
try:
    import keyboard
except ImportError:
    keyboard = None
from src.gear_washer.washer import GearWasher
from src.gear_washer.db_helper import SimpleDB
from config.affix_config import DEFAULT_CONFIGS
from complex_editor import ComplexRuleEditor

# 引入新的组件
from src.components.run_tab import RunTab
from src.components.equip_tab import EquipTab
from src.components.rule_tab import RuleTab
from src.components.setting_tab import SettingTab

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
        self.geometry("800x600")
        
        # 数据库 & 洗炼核心
        self.db = SimpleDB()
        
        # 获取基础路径 (兼容 IDE 运行和打包后的 Exe)
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe，sys.executable 指向 exe 文件所在目录
            exe_dir = os.path.dirname(sys.executable)
            
            # --- OCR 路径查找逻辑 ---
            # 1. 优先查找 _internal 目录 (PyInstaller 6.0+)
            path_check_1 = os.path.join(exe_dir, '_internal', 'OCR', 'tesseract.exe')
            # 2. 其次查找 exe 同级目录
            path_check_2 = os.path.join(exe_dir, 'OCR', 'tesseract.exe')
            
            if os.path.exists(path_check_1):
                self.ocr_base = os.path.join(exe_dir, '_internal')
                print(f"DEBUG: Found tesseract in _internal: {path_check_1}")
            elif os.path.exists(path_check_2):
                self.ocr_base = exe_dir
                print(f"DEBUG: Found tesseract in root: {path_check_2}")
            else:
                # 都没有找到，默认放在同级，并在后面可以报错提示用户
                self.ocr_base = exe_dir
                print(f"DEBUG: Tesseract not found. Checked: {path_check_1}, {path_check_2}")

            # 配置文件等可能还在 exe 同级目录，所以我们需要区分资源目录和配置目录
            self.base_dir = exe_dir 
        else:
            # 如果是脚本运行
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.ocr_base = self.base_dir # 脚本运行时 OCR 就在同一层级

        base_dir = self.base_dir # 为了兼容旧代码引用

        self.ocr_path = os.path.join(self.ocr_base, 'OCR', 'tesseract.exe')
        
        # 设置 TESSDATA_PREFIX 环境变量，防止 Tesseract 找不到语言包
        # 尤其是在打包后的环境中，必须显式指定
        tessdata_path = os.path.join(self.ocr_base, 'OCR', 'tessdata')
        # 即使是 Windows，Tesseract 依然可能被 POSIX 路径习惯影响，尤其是 MSYS2 编译的版本
        # 确保路径不以反斜杠结尾，并且尝试转换为绝对路径
        tessdata_path = os.path.abspath(tessdata_path)
        
        
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
            
            # 更新状态栏提示
            try:
                self.lbl_status.configure(text=f"就绪 (快捷键: {self.hk_start.upper()}开始 / {self.hk_stop.upper()}停止)")
            except: pass

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
        # 整体布局：左右分栏
        # 设置行权重，让内容垂直填满
        self.grid_rowconfigure(0, weight=1)
        
        # 核心修改：设置列权重比例为 3:2
        # column 0 (左侧功能区): weight=3
        # column 1 (右侧日志区): weight=2
        # uniform="group1" 确保在同一组内的列宽严格按照 weight 分配比例
        self.grid_columnconfigure(0, weight=3, uniform="group1") 
        self.grid_columnconfigure(1, weight=2, uniform="group1") 
        
        # --- 左侧：功能区 (TabView) ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")

        # --- 右侧：日志区 (整合到一个 Frame 中) ---
        self.log_container = ctk.CTkFrame(self, corner_radius=10) 
        self.log_container.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        
        # 右侧布局：头部标题 + 内容 + 底部状态
        self.log_container.grid_rowconfigure(1, weight=1)
        self.log_container.grid_columnconfigure(0, weight=1)

        # 1. 日志标题栏
        self.log_header_frame = ctk.CTkFrame(self.log_container, fg_color="transparent", height=30)
        self.log_header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        self.lbl_log_title = ctk.CTkLabel(
            self.log_header_frame, 
            text="📜 运行日志", 
            font=("Microsoft YaHei", 14, "bold"),
            text_color=("gray30", "gray80")
        )
        self.lbl_log_title.pack(side="left", padx=5)

        # 锁定日志视口 Checkbox
        self.log_lock_var = ctk.BooleanVar(value=False)
        self.chk_lock_log = ctk.CTkSwitch(
            self.log_header_frame, 
            text="锁定滚动", 
            variable=self.log_lock_var,
            width=80, 
            height=20, 
            font=("Microsoft YaHei", 12)
        )
        self.chk_lock_log.pack(side="right", padx=5)

        # 2. 日志内容框
        self.log_box = ctk.CTkTextbox(
            self.log_container, 
            font=("Consolas", 12), 
            state="disabled",
            text_color="#EEEEEE", 
            fg_color="#1E1E1E", 
            border_width=0, 
            corner_radius=6
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # 配置日志颜色标签 (需要访问底层 tkinter.Text 控件)
        try:
            self.log_box._textbox.tag_config("ERROR", foreground="#FF5555")   # 红色
            self.log_box._textbox.tag_config("WARN", foreground="#FFB86C")    # 橙色
            self.log_box._textbox.tag_config("INFO", foreground="#8BE9FD")    # 青色
            self.log_box._textbox.tag_config("SUCCESS", foreground="#50FA7B") # 绿色
            self.log_box._textbox.tag_config("DEBUG", foreground="#6272A4")   # 灰色
        except Exception as e:
            print(f"设置日志颜色失败: {e}")
        
        # 3. 底部简洁状态栏 (移入右侧 log_container 底部)
        self.status_bar_frame = ctk.CTkFrame(self.log_container, fg_color="transparent", height=25)
        self.status_bar_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        self.lbl_status = ctk.CTkLabel(
            self.status_bar_frame, 
            text=f"就绪 ({self.hk_start.upper()} 开始 / {self.hk_stop.upper()} 停止)", 
            text_color="gray", 
            font=("Microsoft YaHei", 12)
        )
        self.lbl_status.pack(side="left") # 靠左对齐

        # 创建 Tabs
        self.tab_run_container = self.tab_view.add("运行控制")
        self.tab_equip_container = self.tab_view.add("装备管理")
        self.tab_rule_container = self.tab_view.add("规则管理")
        self.tab_setting_container = self.tab_view.add("系统设置")
        
        # --- TAB 1: 运行控制 ---
        self.run_tab = RunTab(self.tab_run_container, self)
        self.run_tab.pack(fill="both", expand=True)

        # --- TAB 2: 装备管理 ---
        self.equip_tab = EquipTab(self.tab_equip_container, self)
        self.equip_tab.pack(fill="both", expand=True)
        
        # --- TAB 3: 规则管理 ---
        self.rule_tab = RuleTab(self.tab_rule_container, self)
        self.rule_tab.pack(fill="both", expand=True)
        
        # --- TAB 4: 系统设置 ---
        self.setting_tab = SettingTab(self.tab_setting_container, self)
        self.setting_tab.pack(fill="both", expand=True)

        # 配置日志颜色标签 (需要访问底层 tkinter.Text 控件)
        try:
            self.log_box._textbox.tag_config("ERROR", foreground="#FF5555")   # 红色
            self.log_box._textbox.tag_config("WARN", foreground="#FFB86C")    # 橙色
            self.log_box._textbox.tag_config("INFO", foreground="#8BE9FD")    # 青色
            self.log_box._textbox.tag_config("SUCCESS", foreground="#50FA7B") # 绿色
            self.log_box._textbox.tag_config("DEBUG", foreground="#6272A4")   # 灰色
        except Exception as e:
            print(f"设置日志颜色失败: {e}")

        # 重定向输出
        self.redirector = TextRedirector(self.log_box)
        sys.stdout = self.redirector

    def start_bind_hotkey(self, key_type):
        """开始捕获快捷键，阻塞式但不冻结GUI"""
        
        # 1. 确定目标按钮和原始文本
        if key_type == "start":
            target_btn = self.setting_tab.btn_bind_start
        else:
            target_btn = self.setting_tab.btn_bind_stop
            
        # 2. 更新UI提示
        target_btn.configure(text="请按下组合键...", fg_color="#FFA500")
        self.setting_tab.btn_bind_start.configure(state="disabled")
        self.setting_tab.btn_bind_stop.configure(state="disabled")
        
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
            self.setting_tab.btn_bind_start.configure(state="normal", text=self.hk_start.upper(), fg_color="#555555")
            self.setting_tab.btn_bind_stop.configure(state="normal", text=self.hk_stop.upper(), fg_color="#555555")
        except: pass

    def _show_guide_window(self):
        """显示操作手册 (在浏览器中打开HTML)"""
        try:
            guide_path = os.path.join(self.base_dir, '操作手册.html')
            abs_path = os.path.abspath(guide_path)
            
            if os.path.exists(abs_path):
                # webbrowser.open 最好接收 file:/// 协议的 URL
                url = 'file:///' + abs_path.replace('\\', '/')
                webbrowser.open_new_tab(url)
            else:
                # 兼容性 fallback: 找不到 HTML 就试图找 MD
                md_path = os.path.join(self.base_dir, '操作手册.md')
                if os.path.exists(md_path):
                    self._show_text_window("操作手册", self._read_file(md_path))
                else:
                    # 获取当前目录列表以供调试
                    try:
                        files = os.listdir(self.base_dir)
                        debug_info = f"当前目录 ({self.base_dir}) 内容:\n" + "\n".join(files[:10])
                    except:
                        debug_info = "无法读取目录"
                    
                    err_msg = f"❌ 找不到 '操作手册.html'\n路径: {abs_path}\n\n{debug_info}"
                    self._show_text_window("错误", err_msg)
        except Exception as e:
            print(f"打开操作手册失败: {e}")
            self._show_text_window("错误", f"打开操作手册失败: {e}")

    def _read_file(self, path):
         try:
             with open(path, 'r', encoding='utf-8') as f:
                 return f.read()
         except:
             return "文件读取失败"

    def _show_text_window(self, title, content):
          """后备文本显示窗口"""
          w = ctk.CTkToplevel(self)
          w.title(title)
          w.geometry("800x600")
          tb = ctk.CTkTextbox(w, font=("Consolas", 14))
          tb.pack(fill="both", expand=True, padx=10, pady=10)
          tb.insert("0.0", content)
          tb.configure(state="disabled")

    def on_affix_mgr_change(self, choice):
        """Tab3 规则管理选择变化 - 代理给主逻辑"""
        self.on_affix_change(choice)

    def _check_log_queue(self):
        """定期从队列读取日志更新到界面 (优化版)"""
        try:
            if not self.redirector.queue.empty():
                self.log_box.configure(state="normal")
                
                # 获取底层Text控件
                try:
                    tb = self.log_box._textbox
                except AttributeError:
                    tb = self.log_box # 回退方案
                
                processed_count = 0
                max_lines = 100 # 防止一次写入太多卡顿
                
                while processed_count < max_lines:
                    try:
                        text = self.redirector.queue.get_nowait()
                    except queue.Empty:
                        break
                        
                    lower_text = text.lower()
                    tags = []
                    
                    if "错误" in text or "error" in lower_text or "fail" in lower_text:
                        tags.append("ERROR")
                    elif "警告" in text or "warn" in lower_text:
                        tags.append("WARN")
                    elif "成功" in text or "success" in lower_text or "完成" in text:
                        tags.append("SUCCESS")
                    elif "debug" in lower_text:
                        tags.append("DEBUG")
                    elif "info" in lower_text or "提示" in text:
                        tags.append("INFO")
                    
                    try:
                        # 插入前位置
                        start_idx = tb.index("end-1c")
                        tb.insert("end", text)
                        # 插入后位置(不含最后的换行符)
                        end_idx = tb.index("end-1c")
                        
                        if tags:
                            for t in tags:
                                tb.tag_add(t, start_idx, end_idx)
                    except Exception:
                        # 万一失败直接用普通insert
                        try:
                            self.log_box.insert("end", text)
                        except: pass
                        
                    processed_count += 1
                
                # 滚动到底部
                if not self.log_lock_var.get():
                    self.log_box.see("end")
                    
                self.log_box.configure(state="disabled")
        except Exception as e:
            print(f"日志队列处理异常: {e}")
        finally: 
            self.after(50, self._check_log_queue)

    def _load_data(self):
        """加载数据"""
        # 1. 加载装备
        equips = self.db.list_equipment_types()
        self.equip_map = {name: eid for eid, name in equips}
        equip_names = [name for _, name in equips]
        
        # 更新 Tab1 选择框
        self.run_tab.combo_equip.configure(values=equip_names)
        # 更新 Tab2 管理下拉框
        self.equip_tab.combo_equip_mgr.configure(values=equip_names)

        if equip_names:
            current = self.run_tab.combo_equip.get()
            if current not in equip_names:
                self.run_tab.combo_equip.set(equip_names[0])
                self.equip_tab.combo_equip_mgr.set(equip_names[0])
            else:
                 self.equip_tab.combo_equip_mgr.set(current)
        else:
            self.run_tab.combo_equip.set("无配置")
            self.equip_tab.combo_equip_mgr.set("无配置")

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
        self.run_tab.combo_affix.configure(values=affix_names)
        # 更新 Tab3 管理下拉框
        self.rule_tab.combo_affix_mgr.configure(values=affix_names)
        
        # 尝试恢复
        current = self.run_tab.combo_affix.get()
        if current in affix_names:
             self.on_affix_change(current)
             self.rule_tab.combo_affix_mgr.set(current)
             self.on_affix_mgr_change(current)
        elif affix_names:
            self.run_tab.combo_affix.set(affix_names[0])
            self.on_affix_change(affix_names[0])
            self.rule_tab.combo_affix_mgr.set(affix_names[0])
            self.on_affix_mgr_change(affix_names[0])
        else:
            self.run_tab.combo_affix.set("")
            self.rule_tab.combo_affix_mgr.set("")
            self.current_rule_content = ""

    def on_equip_change(self, choice):
        print(f"已选择装备: {choice}")
        self.equip_tab.combo_equip_mgr.set(choice)

    def on_affix_change(self, choice):
        if choice in self.affix_data_map:
            content = self.affix_data_map[choice]
            if isinstance(content, (list, dict)):
                content = json.dumps(content, ensure_ascii=False)
            
            self.current_rule_content = str(content)
            self.current_affix_id = self.affix_id_map.get(choice)
            self.current_affix_source = self.affix_source_map.get(choice)
            
            # 2. 同步 UI (仅设置值，不触发回调防止死循环)
            if self.rule_tab.combo_affix_mgr.get() != choice:
                self.rule_tab.combo_affix_mgr.set(choice)
            
            if self.run_tab.combo_affix.get() != choice:
                self.run_tab.combo_affix.set(choice)

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
            current_name = self.rule_tab.combo_affix_mgr.get()
            success = self.db.update_affix(self.current_affix_id, json_str, current_name)
            
            if success:
                print(f"规则 [{current_name}] 已成功更新！")
                self._load_data()
                # 恢复选中状态
                self.rule_tab.combo_affix_mgr.set(current_name)
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
                    self.run_tab.combo_affix.set(name)
                    self.on_affix_change(name)
                else:
                    print(f"保存失败，可能是名称重复。")

        ComplexRuleEditor(self, initial_data=None, callback=on_create)


    def rename_current_rule(self):
        choice = self.rule_tab.combo_affix_mgr.get() # 从管理Tab获取
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
        choice = self.rule_tab.combo_affix_mgr.get()
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
            self.equip_tab.btn_new_equip.configure(state="disabled")
            self.equip_tab.btn_edit_equip.configure(state="disabled")
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
            self.equip_tab.btn_new_equip.configure(state="normal")
            self.equip_tab.btn_edit_equip.configure(state="normal")
        except: pass

    def edit_current_equip(self):
        """编辑(覆盖)当前装备定位 - 从Tab2调用"""
        equip_name = self.equip_tab.combo_equip_mgr.get()
        if not equip_name or equip_name == "无配置" or equip_name == "请选择...":
            print("错误：请先在下拉框选择一个配置！")
            return
            
        eid = self.equip_map.get(equip_name)
        if not eid: return

        print(f"=== 准备重新定位: {equip_name} ===")
        self._run_calibrate_logic(equip_name, is_update=True)

    def rename_current_equip(self):
        equip_name = self.equip_tab.combo_equip_mgr.get()
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
        equip_name = self.equip_tab.combo_equip_mgr.get()
        if not equip_name or equip_name == "无配置": return
        eid = self.equip_map.get(equip_name)
        if not eid: return
        
        self.db.delete_equipment_type(eid)
        print(f"装备 [{equip_name}] 已删除。")
        self._load_data()

    def start_washing(self):
        if self.running: return
        
        equip_name = self.run_tab.combo_equip.get()
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
        self.run_tab.btn_start.configure(state="disabled")
        self.run_tab.btn_stop.configure(state="normal")
        self.lbl_status.configure(text=f"运行中... (按 {self.hk_stop.upper()} 停止)", text_color="green")
        self.run_tab.update_status(f"运行中... (按 {self.hk_stop.upper()} 停止)", is_running=True)
        
        self.worker_thread = threading.Thread(target=self._run_washer_loop, daemon=True)
        self.worker_thread.start()
        
    def stop_washing(self):
        if self.washer:
            self.washer.stop()
        self.running = False
        self.run_tab.btn_start.configure(state="normal")
        self.run_tab.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text=f"已停止 (快捷键: {self.hk_start.upper()}开始 / {self.hk_stop.upper()}停止)", text_color="gray")
        self.run_tab.update_status("已手动停止", is_running=False)

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
        self.run_tab.btn_start.configure(state="normal")
        self.run_tab.btn_stop.configure(state="disabled")

        status_text = f"已结束 (快捷键: {self.hk_start.upper()}开始 / {self.hk_stop.upper()}停止)"
        self.lbl_status.configure(text=status_text, text_color="gray")
        self.run_tab.update_status("已结束", is_running=False)

if __name__ == '__main__':
    app = App()
    app.mainloop()
