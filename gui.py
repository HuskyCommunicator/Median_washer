import customtkinter as ctk
import threading
import sys
import os
import time
import io
import queue
from src.gear_washer.washer import GearWasher
from src.gear_washer.db_helper import SimpleDB
from config.affix_config import DEFAULT_CONFIGS

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
        
        # 获取 Tesseract 路径 (假设和 run_washer_v2.py 同级结构)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ocr_path = os.path.join(base_dir, 'OCR', 'tesseract.exe')
        
        self.washer = None # 将在运行时实例化
        self.running = False
        self.worker_thread = None

        # 布局配置
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1) # 日志区域自适应高度

        self._init_ui()
        self._load_data()
        
        # 定时检查日志输出
        self.after(100, self._check_log_queue)

    def _init_ui(self):
        # 1. 装备选择区域
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.lbl_equip = ctk.CTkLabel(self.frame_top, text="选择装备配置:", font=("Microsoft YaHei", 14, "bold"))
        self.lbl_equip.grid(row=0, column=0, padx=10, pady=10)
        
        self.combo_equip = ctk.CTkComboBox(self.frame_top, width=250, command=self.on_equip_change)
        self.combo_equip.grid(row=0, column=1, padx=10, pady=10)
        self.combo_equip.set("请选择...")

        self.btn_new_equip = ctk.CTkButton(self.frame_top, text="新建/定位", width=100, command=self.create_new_equip)
        self.btn_new_equip.grid(row=0, column=2, padx=10, pady=10)

        # 2. 词缀选择区域
        self.frame_mid = ctk.CTkFrame(self)
        self.frame_mid.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.lbl_affix = ctk.CTkLabel(self.frame_mid, text="选择目标词缀:", font=("Microsoft YaHei", 14, "bold"))
        self.lbl_affix.grid(row=0, column=0, padx=10, pady=10)

        self.combo_affix = ctk.CTkComboBox(self.frame_mid, width=250, command=self.on_affix_change)
        self.combo_affix.grid(row=0, column=1, padx=10, pady=10)
        
        self.btn_save_affix = ctk.CTkButton(self.frame_mid, text="保存当前词缀", width=100, command=self.save_current_affix)
        self.btn_save_affix.grid(row=0, column=2, padx=10, pady=10)
        
        # 手动输入框 (放在下一行)
        self.lbl_manual = ctk.CTkLabel(self.frame_mid, text="词缀逻辑内容:")
        self.lbl_manual.grid(row=1, column=0, padx=10, pady=5)
        
        self.entry_affix = ctk.CTkEntry(self.frame_mid, width=400, placeholder_text="例如: 冰霜抗性 && 智力")
        self.entry_affix.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        # 3. 控制按钮
        self.frame_ctrl = ctk.CTkFrame(self)
        self.frame_ctrl.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.btn_start = ctk.CTkButton(self.frame_ctrl, text="开始洗炼", command=self.start_washing, 
                                       fg_color="green", hover_color="darkgreen", height=40, font=("Microsoft YaHei", 16))
        self.btn_start.pack(side="left", expand=True, fill="x", padx=20, pady=10)

        self.btn_stop = ctk.CTkButton(self.frame_ctrl, text="停止", command=self.stop_washing, 
                                      fg_color="red", hover_color="darkred", height=40, font=("Microsoft YaHei", 16), state="disabled")
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=20, pady=10)

        # 4. 日志区域
        self.log_box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.log_box.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        # 状态栏
        self.lbl_status = ctk.CTkLabel(self, text="就绪", text_color="gray")
        self.lbl_status.grid(row=4, column=0, columnspan=2, sticky="w", padx=10)

        # 重定向输出
        self.redirector = TextRedirector(self.log_box)
        sys.stdout = self.redirector

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
        """加载下拉框数据"""
        # 1. 加载装备
        equips = self.db.list_equipment_types() # [(id, name), ...]
        self.equip_map = {name: eid for eid, name in equips}
        equip_names = [name for _, name in equips]
        
        if equip_names:
            self.combo_equip.configure(values=equip_names)
            self.combo_equip.set(equip_names[0])
        else:
            self.combo_equip.set("无配置")
            
        # 2. 加载词缀
        self.affix_data_map = {} # name -> content
        affix_names = []
        
        # 2.1 文件默认
        if DEFAULT_CONFIGS:
            for name, content in DEFAULT_CONFIGS.items():
                display = f"[文件] {name}"
                self.affix_data_map[display] = content
                affix_names.append(display)
                
        # 2.2 数据库
        db_affixes = self.db.get_all_affixes() # [(id, content, desc), ...]
        for _, content, desc in db_affixes:
            display = f"[DB] {desc}"
            self.affix_data_map[display] = content
            affix_names.append(display)
            
        self.combo_affix.configure(values=affix_names)
        if affix_names:
            self.combo_affix.set(affix_names[0])
            self.entry_affix.delete(0, "end")
            self.entry_affix.insert(0, self.affix_data_map[affix_names[0]])

    def on_equip_change(self, choice):
        print(f"如果你选择了: {choice}，点击【开始】时将加载对应坐标。")

    def on_affix_change(self, choice):
        if choice in self.affix_data_map:
            content = self.affix_data_map[choice]
            self.entry_affix.delete(0, "end")
            self.entry_affix.insert(0, content)

    def create_new_equip(self):
        """打开新窗口进行定位向导 (为了简单，暂时用弹窗模拟逻辑)"""
        import tkinter
        dialog = ctk.CTkInputDialog(text="请输入新装备名称:", title="新建配置")
        name = dialog.get_input()
        if not name: return
        
        print(f"=== 开始定位: {name} ===")
        print("请在控制台/日志查看定位提示，并按【空格键】确认坐标...")
        
        # 在子线程运行定位，防止界面卡死
        def run_calibrate():
            self.btn_new_equip.configure(state="disabled")
            try:
                temp_washer = GearWasher(tesseract_cmd=self.ocr_path)
                pos_data = temp_washer.calibrate_ui() # 这一步是阻塞的，会等用户按空格
                
                # 保存
                self.db.save_equipment_type(
                    name=name,
                    gear_pos=pos_data['gear_pos'],
                    affix_points=pos_data['affix_points']
                )
                self.db.set("global_wash_button_pos", pos_data['wash_button'])
                
                print(f"配置 [{name}] 保存成功！请手动重启程序或刷新列表。")
                self.after(0, self._load_data) # 刷新UI
            except Exception as e:
                print(f"定位失败: {e}")
            finally:
                self.after(0, lambda: self.btn_new_equip.configure(state="normal"))
                
        threading.Thread(target=run_calibrate, daemon=True).start()

    def save_current_affix(self):
        content = self.entry_affix.get().strip()
        if not content:
            print("错误：词缀内容为空")
            return
            
        dialog = ctk.CTkInputDialog(text="请输入词缀方案名称:", title="保存词缀")
        name = dialog.get_input()
        if name:
            self.db.add_affix(content, name)
            print(f"词缀 [{name}] 已保存。")
            self._load_data() # 刷新下拉框

    def start_washing(self):
        if self.running: return
        
        equip_name = self.combo_equip.get()
        if not equip_name or equip_name == "无配置" or equip_name == "请选择...":
            print("错误：请先选择或新建装备配置！")
            return
            
        affix_rule = self.entry_affix.get().strip()
        if not affix_rule:
            print("错误：词缀规则为空！")
            return

        # 准备数据
        try:
            cfg = self.db.get_equipment_type(equip_name)
            if not cfg:
                print(f"错误：找不到装备 [{equip_name}] 的数据库记录")
                return
                
            wash_btn = self.db.get("global_wash_button_pos")
            if not wash_btn:
                print("错误：未找到全局洗炼按钮坐标，请尝试【新建/定位】一次")
                return
                
            # 初始化 Washer
            self.washer = GearWasher(tesseract_cmd=self.ocr_path)
            self.washer.gear_pos = cfg['gear_pos']
            self.washer.wash_button_pos = tuple(wash_btn)
            
            p1, p2 = cfg['affix_points']
            # 这里简单算一下 rect，复用之前 run_washer_v2 的逻辑
            x = min(p1[0], p2[0])
            y = min(p1[1], p2[1])
            w = abs(p2[0] - p1[0])
            h = abs(p2[1] - p1[1])
            self.washer.affix_region = (x, y, w, h)
            
            self.washer.conditions = affix_rule
            
        except Exception as e:
            print(f"初始化失败: {e}")
            return

        # 启动线程
        self.running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="运行中...", text_color="green")
        
        self.worker_thread = threading.Thread(target=self._run_washer_loop, daemon=True)
        self.worker_thread.start()

    def _run_washer_loop(self):
        print("=== 洗炼开始 ===")
        try:
            self.washer.run()
        except Exception as e:
            print(f"运行时错误: {e}")
        finally:
            self.running = False
            print("=== 洗炼结束 ===")
            # 只有在主线程才能更新UI
            self.after(0, self._on_process_finish)

    def _on_process_finish(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="已停止", text_color="gray")

    def stop_washing(self):
        if self.washer:
            print(">>> 正在请求停止... <<<")
            self.washer.stop_requested = True # 利用 washer 已有的停止标志

if __name__ == "__main__":
    app = App()
    app.mainloop()
