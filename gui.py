import customtkinter as ctk
import threading
import sys
import os
import time
import io
import queue
import json
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
        
        # 获取 Tesseract 路径 (假设和 run_washer_v2.py 同级结构)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ocr_path = os.path.join(base_dir, 'OCR', 'tesseract.exe')
        
        self.washer = None # 将在运行时实例化
        self.running = False
        self.worker_thread = None
        self.current_rule_content = "" # 存储当前选择/编辑的规则内容(JSON string 或普通 string)
        self.current_affix_id = None   # 存储当前选择的规则ID (如果是DB类型)
        self.current_affix_source = None # 'FILE' or 'DB'

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
        
        # Row 0: Label + ComboBox
        self.lbl_equip = ctk.CTkLabel(self.frame_top, text="选择装备配置:", font=("Microsoft YaHei", 14, "bold"))
        self.lbl_equip.grid(row=0, column=0, padx=10, pady=10)
        
        self.combo_equip = ctk.CTkComboBox(self.frame_top, width=300, command=self.on_equip_change)
        self.combo_equip.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Row 1: Buttons
        self.frame_top_btns = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        self.frame_top_btns.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.btn_new_equip = ctk.CTkButton(self.frame_top_btns, text="新建", width=80, command=self.new_equip_flow)
        self.btn_new_equip.pack(side="left", padx=5)

        self.btn_edit_equip = ctk.CTkButton(self.frame_top_btns, text="编辑/定位", width=100, fg_color="#555555", command=self.edit_current_equip)
        self.btn_edit_equip.pack(side="left", padx=5)
        
        self.btn_rename_equip = ctk.CTkButton(self.frame_top_btns, text="重命名", width=80, fg_color="#FFA500", command=self.rename_current_equip)
        self.btn_rename_equip.pack(side="left", padx=5)
        
        self.btn_delete_equip = ctk.CTkButton(self.frame_top_btns, text="删除", width=80, fg_color="darkred", command=self.delete_current_equip)
        self.btn_delete_equip.pack(side="left", padx=5)

        # 2. 词缀选择区域
        self.frame_mid = ctk.CTkFrame(self)
        self.frame_mid.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # 修改 label
        self.lbl_affix = ctk.CTkLabel(self.frame_mid, text="选择规则:", font=("Microsoft YaHei", 14, "bold"))
        self.lbl_affix.grid(row=0, column=0, padx=10, pady=10)

        self.combo_affix = ctk.CTkComboBox(self.frame_mid, width=300, command=self.on_affix_change)
        self.combo_affix.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # 操作按钮区 (Row 1)
        self.frame_btns = ctk.CTkFrame(self.frame_mid, fg_color="transparent")
        self.frame_btns.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # 按钮布局优化：编辑 -> 覆盖 -> 另存 -> 重命名 -> 删除
        self.btn_advanced = ctk.CTkButton(self.frame_btns, text="编辑规则详情", width=120, fg_color="#555555", command=self.open_advanced_editor)
        self.btn_advanced.pack(side="left", padx=5)

        self.btn_save_overwrite = ctk.CTkButton(self.frame_btns, text="覆盖保存", width=100, fg_color="#FFA500", command=self.save_overwrite_rule)
        self.btn_save_overwrite.pack(side="left", padx=5)

        self.btn_save_new = ctk.CTkButton(self.frame_btns, text="另存为新规则", width=100, command=self.save_new_rule)
        self.btn_save_new.pack(side="left", padx=5)
        
        self.btn_rename_rule = ctk.CTkButton(self.frame_btns, text="重命名", width=100, fg_color="#FFA500", command=self.rename_current_rule)
        self.btn_rename_rule.pack(side="left", padx=5)

        self.btn_delete_rule = ctk.CTkButton(self.frame_btns, text="删除本规则", width=100, fg_color="darkred", command=self.delete_current_rule)
        self.btn_delete_rule.pack(side="left", padx=5)

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
            # 尝试恢复选择
            current = self.combo_equip.get()
            if current not in equip_names:
                self.combo_equip.set(equip_names[0])
        else:
            self.combo_equip.set("无配置")
            
        # 2. 加载词缀
        self.affix_data_map = {} # name -> content
        self.affix_id_map = {}   # name -> id (for DB items)
        self.affix_source_map = {} # name -> 'FILE' or 'DB'
        affix_names = []
        
        # 2.1 文件默认 (去掉前缀，处理重名)
        if DEFAULT_CONFIGS:
            for name, content in DEFAULT_CONFIGS.items():
                display = name
                # 如果数据库里有叫 "默认_项链" 的，这里就会冲突。
                # 简单处理：如果已存在，加后缀。
                orig_display = display
                idx = 1
                while display in self.affix_data_map:
                    display = f"{orig_display} ({idx})"
                    idx += 1
                    
                self.affix_data_map[display] = content
                self.affix_source_map[display] = 'FILE'
                affix_names.append(display)
                
        # 2.2 数据库 (去掉前缀，处理重名)
        db_affixes = self.db.get_all_affixes() # [(id, content, desc), ...]
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
            
        self.combo_affix.configure(values=affix_names)
        
        # 尝试恢复之前选中的
        current = self.combo_affix.get()
        if current in affix_names:
             self.on_affix_change(current)
        elif affix_names:
            self.combo_affix.set(affix_names[0])
            self.on_affix_change(affix_names[0])
        else:
            self.combo_affix.set("")
            self.current_rule_content = ""

    def on_equip_change(self, choice):
        print(f"如果你选择了: {choice}，点击【开始】时将加载对应坐标。")

    def on_affix_change(self, choice):
        if choice in self.affix_data_map:
            content = self.affix_data_map[choice]
            # 如果是复杂对象(list/dict)，转成json字符串存到内存
            if isinstance(content, (list, dict)):
                content = json.dumps(content, ensure_ascii=False)
            
            self.current_rule_content = str(content)
            self.current_affix_id = self.affix_id_map.get(choice) # 获取ID，如果不是DB的则为None
            self.current_affix_source = self.affix_source_map.get(choice)
            print(f"已加载规则: {choice} ({self.current_affix_source})")

    def open_advanced_editor(self):
        # 使用内存中的 content
        current_text = self.current_rule_content.strip()
        initial_data = None
        if current_text.startswith("[") and current_text.endswith("]"):
            try:
                initial_data = json.loads(current_text)
            except:
                pass
        
        # 回调函数：编辑器保存 update self.current_rule_content
        def on_save(data):
            json_str = json.dumps(data, ensure_ascii=False)
            self.current_rule_content = json_str
            print("规则详情已更新至内存（尚未保存到数据库，请点击保存按钮）。")
            
        ComplexRuleEditor(self, initial_data=initial_data, callback=on_save)

    def save_overwrite_rule(self):
        """保存并覆盖"""
        if not self.current_rule_content:
            print("错误：当前无规则内容")
            return
            
        choice = self.combo_affix.get()
        source = self.current_affix_source
        
        if source == 'FILE':
            print("错误：文件默认配置无法覆盖，请使用【另存为新规则】")
            return
            
        # DB 配置
        if self.current_affix_id is not None:
            # 这里的 choice 已经是纯名称
            desc = choice 
            
            success = self.db.update_affix(self.current_affix_id, self.current_rule_content, desc)
            if success:
                print(f"成功更新规则: {desc}")
                self._load_data() 
            else:
                print("更新失败，可能是内容冲突或数据库错误。")
        else:
            print("无法确定规则来源，无法覆盖。")

    def save_new_rule(self):
        """保存为新规则"""
        if not self.current_rule_content:
            print("错误：当前无规则内容")
            return
            
        import customtkinter as ctk 
        dialog = ctk.CTkInputDialog(text="请输入新规则名称:", title="保存新规则")
        name = dialog.get_input()
        if name:
            success = self.db.add_affix(self.current_rule_content, name)
            if success:
                print(f"新规则 [{name}] 已保存。")
                self._load_data() 
                # 尝试选中新添加的
                self.combo_affix.set(name)
                self.on_affix_change(name)
            else:
                print("保存失败，可能该规则内容已存在。")

    def rename_current_rule(self):
        """重命名当前规则"""
        choice = self.combo_affix.get()
        if not choice: return
        
        source = self.current_affix_source
        if source == 'FILE':
            print("错误：无法重命名文件默认配置，请使用【另存为新规则】。")
            return
            
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
                    self.combo_affix.set(new_name)
                    self.on_affix_change(new_name)
                else:
                    print("重命名失败。")
            except Exception as e:
                print(f"重命名出错: {e}")

    def delete_current_rule(self):
        """删除当前选中的规则"""
        choice = self.combo_affix.get()
        if not choice: return
        
        source = self.current_affix_source
        if source == 'FILE':
            print("错误：无法删除默认的文件配置。")
            return
            
        if self.current_affix_id is None:
            return

        # 使用 db_helper 的方法 (需要先确认 db_helper 是否有 delete_affix)
        # 上一步我们添加了，这里可以直接调用
        try:
            self.db.delete_affix(self.current_affix_id)
            print(f"规则 [{choice}] 已删除。")
            self._load_data()
        except Exception as e:
            print(f"删除失败: {e}")

    # ================= 装备相关操作 =================

    def new_equip_flow(self):
        """新建装备流程"""
        import customtkinter as ctk 
        dialog = ctk.CTkInputDialog(text="请输入新装备名称:", title="新建配置")
        name = dialog.get_input()
        if not name: return
        
        self._run_calibrate_logic(name, is_update=False)

    def edit_current_equip(self):
        """编辑(覆盖)当前装备定位"""
        equip_name = self.combo_equip.get()
        if not equip_name or equip_name == "无配置" or equip_name == "请选择...":
            print("错误：请先选择一个配置！")
            return
            
        # 确认一下ID是否存在
        eid = self.equip_map.get(equip_name)
        if not eid:
            return

        print(f"=== 准备重新定位: {equip_name} ===")
        # 逻辑是一样的，只是名字不变，存的时候会自动 update
        self._run_calibrate_logic(equip_name, is_update=True)

    def rename_current_equip(self):
        """重命名当前装备"""
        equip_name = self.combo_equip.get()
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
                self.combo_equip.set(new_name)
            else:
                print("重命名失败，可能名称已存在。")

    def delete_current_equip(self):
        """删除当前装备"""
        equip_name = self.combo_equip.get()
        if not equip_name or equip_name == "无配置": return
        
        eid = self.equip_map.get(equip_name)
        if not eid: return
        
        self.db.delete_equipment_type(eid)
        print(f"装备 [{equip_name}] 已删除。")
        self._load_data()


    def create_new_equip(self):
        """(旧接口保留) 代理到 new_equip_flow"""
        self.new_equip_flow()

    def _run_calibrate_logic(self, name, is_update=False):
        """通用的定位逻辑"""
        print(f"=== 开始定位: {name} ===")
        print("请在控制台/日志查看定位提示，并按【空格键】确认坐标...")
        
        # 禁用相关按钮
        self.btn_new_equip.configure(state="disabled")
        self.btn_edit_equip.configure(state="disabled")
        
        def run_calibrate():
            try:
                temp_washer = GearWasher(tesseract_cmd=self.ocr_path)
                pos_data = temp_washer.calibrate_ui() 
                
                # save_equipment_type 内部用了 INSERT ... ON CONFLICT UPDATE
                # 所以只要 name 相同，就会覆盖
                self.db.save_equipment_type(
                    name=name,
                    gear_pos=pos_data['gear_pos'],
                    affix_points=pos_data['affix_points']
                )
                self.db.set("global_wash_button_pos", pos_data['wash_button'])
                
                print(f"配置 [{name}] 保存成功！请手动重启程序或刷新列表。")
                self.after(0, self._load_data) 
                # 如果是新建，可能需要选中... _load_data 默认选第一个，或者我可以手动set
                # 简单起见 _load_data 后由用户选
            except Exception as e:
                print(f"定位失败: {e}")
            finally:
                self.after(0, lambda: self._enable_equip_buttons())
                
        threading.Thread(target=run_calibrate, daemon=True).start()

    def _enable_equip_buttons(self):
        self.btn_new_equip.configure(state="normal")
        self.btn_edit_equip.configure(state="normal")

    def start_washing(self):
        if self.running: return
        
        equip_name = self.combo_equip.get()
        if not equip_name or equip_name == "无配置" or equip_name == "请选择...":
            print("错误：请先选择或新建装备配置！")
            return
            
        affix_rule_str = self.current_rule_content
        if not affix_rule_str:
            print("错误：当前未加载任何词缀规则！")
            return
            
        # 尝试解析 JSON
        final_conditions = affix_rule_str
        if affix_rule_str.startswith("[") or affix_rule_str.startswith("{"):
            try:
                final_conditions = json.loads(affix_rule_str)
            except json.JSONDecodeError:
                pass

        try:
            eid = self.equip_map.get(equip_name)
            if not eid:
                print(f"错误：内部映射错误，找不到装备 [{equip_name}] 的ID")
                return
                 
            cfg = self.db.get_equipment_type_by_id(eid)
            
            if not cfg:
                print(f"错误：找不到装备 [{equip_name}] 的数据库记录")
                return
                
            wash_btn = self.db.get("global_wash_button_pos")
            if not wash_btn:
                print("错误：未找到全局洗炼按钮坐标，请尝试【新建/定位】一次")
                return
                
            self.washer = GearWasher(tesseract_cmd=self.ocr_path)
            self.washer.gear_pos = cfg['gear_pos']
            self.washer.wash_button_pos = tuple(wash_btn)
            
            p1, p2 = cfg['affix_points']
            x = min(p1[0], p2[0])
            y = min(p1[1], p2[1])
            w = abs(p2[0] - p1[0])
            h = abs(p2[1] - p1[1])
            self.washer.affix_region = (x, y, w, h)
            
            self.washer.conditions = final_conditions
            
        except Exception as e:
            print(f"初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return

        self.running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="运行中...", text_color="green")
        
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
