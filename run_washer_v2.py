from src.gear_washer.washer import GearWasher
import sys
import os
import time
from config.affix_config import DEFAULT_CONFIGS
from src.gear_washer.db_helper import SimpleDB

# Tesseract 路径
base_dir = os.path.dirname(os.path.abspath(__file__))
OCR_CMD = os.path.join(base_dir, 'OCR', 'tesseract.exe')
print(f"OCR 路径: {OCR_CMD}")

def calculate_rect(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    return (x, y, w, h)

def clear_screen():
    print("\n" * 2)

def main():
    # 检查是否启用调试模式
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    if debug_mode:
        print(">>> 调试模式已启用：OCR图片将保存到 ocr_debug/ 目录 <<<\n")
    
    # 检查OCR放大倍数参数
    scale_factor = 5.0  # 默认5倍
    for arg in sys.argv:
        if arg.startswith("--scale="):
            try:
                scale_factor = float(arg.split("=")[1])
                print(f">>> OCR放大倍数设置为：{scale_factor}x <<<\n")
            except:
                print(f"警告：无法解析放大倍数参数 {arg}，使用默认5.0倍")
    
    db = SimpleDB()
    washer = GearWasher(tesseract_cmd=OCR_CMD, debug_mode=debug_mode, ocr_scale_factor=scale_factor)
    
    # ---------------------------------------------------------
    # 第一步：选择物品类型 (Item Position)
    # ---------------------------------------------------------
    clear_screen()
    print("=== 第一步：选择物品类型 (位置配置) ===")
    
    # 从数据库的新表中获取列表
    # item_options: list of (id, name)
    item_options = db.list_equipment_types()
    
    print("已有配置:")
    for idx, (type_id, name) in enumerate(item_options):
        print(f"  [{idx + 1}] {name}")
    print(f"  [{len(item_options) + 1}] + 新建/手动定位")
    
    choice = input("\n请选择 (输入序号): ").strip()
    
    selected_type_id = None
    selected_item_name = None
    pos_data = None
    need_calibrate = False
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(item_options):
            selected_type_id, selected_item_name = item_options[idx]
            print(f"已选择: {selected_item_name}")
            
            # 加载配置
            cfg = db.get_equipment_type_by_id(selected_type_id)
            if cfg:
                pos_data = {
                    'gear_pos': cfg['gear_pos'],
                    'affix_points': cfg['affix_points'],
                    'window_title': cfg.get('window_title')
                }
            else:
                print("读取错误，需重新定位。")
                need_calibrate = True
        else:
            # 新建模式
            print("您选择了新建配置。")
            selected_item_name = input("请输入新物品的名称 (例如 '火法杖'): ").strip()
            if not selected_item_name:
                selected_item_name = f"Item_{int(time.time())}"
            need_calibrate = True
    else:
        # 默认新建
        print("您选择了新建配置。")
        selected_item_name = input("请输入新物品的名称 (例如 '火法杖'): ").strip()
        if not selected_item_name:
                selected_item_name = f"Item_{int(time.time())}"
        need_calibrate = True

    if need_calibrate:
        # 调用交互式定位，获取 装备位置、词缀区域
        pos_data = washer.calibrate_ui()
        
        # 存入数据库
        db.save_equipment_type(
            name=selected_item_name,
            gear_pos=pos_data['gear_pos'],
            affix_points=pos_data['affix_points'],
            window_title=pos_data.get('window_title')
        )
        
        print(f"已保存配置: [{selected_item_name}]")
    
    # 应用位置配置
    if pos_data:
        washer.gear_pos = pos_data['gear_pos']
        washer.window_title = pos_data.get('window_title')
        # 计算 affix_region
        p1, p2 = pos_data['affix_points']
        washer.affix_region = calculate_rect(p1, p2)
    
    # ---------------------------------------------------------
    # 第三步：选择词缀 (Affix)
    # ---------------------------------------------------------
    clear_screen()
    print("=== 第三步：选择洗炼词缀 ===")
    
    # 从数据库的新Affix表中获取
    affix_list = db.get_all_affixes()
    
    # 构建所有选项列表: (display_name, content)
    all_options = []
    
    # 0. 尝试导入默认配置 (如果需要)
    # 命令行版本也移除自动导入，防止干扰GUI操作
    # if DEFAULT_CONFIGS:
    #    db.migrate_defaults(DEFAULT_CONFIGS)

    # 2. 来自数据库的配置
    for aff_id, content, desc in affix_list:
        display = desc if desc else f"词缀组_{aff_id}"
        all_options.append((f"[DB] {display}", content))
    
    # 打印选项
    for idx, (name, content) in enumerate(all_options):
        print(f"  [{idx + 1}] {name} (内容: {str(content)[:30]}...)")
        
    print(f"  [{len(all_options) + 1}] + 手动输入新词缀")

    choice_aff = input("\n请选择 (输入序号): ").strip()
    
    final_conditions = None
    
    if choice_aff.isdigit():
        idx = int(choice_aff) - 1
        if 0 <= idx < len(all_options):
            final_conditions = all_options[idx][1]
            print(f"已选择: {all_options[idx][0]}")
            
    if final_conditions is None:
        # 手动输入模式 (这里逻辑保持不变，只是入口变了)
        print("\n请输入目标词缀逻辑 (支持 &&, || 等, 例如 '冰冻伤害 && 智力'):")
        raw_input = input("> ").strip()
        if raw_input:
            final_conditions = raw_input
            # 询问是否保存
            save_yn = input("是否保存此词缀为预设? (y/n) [y]: ").strip().lower()
            if save_yn != 'n':
                preset_desc = input("请输入预设描述名称 (例如 '冰法通用'): ").strip()
                if not preset_desc:
                    preset_desc = f"自定义_{int(time.time())}"
                
                # 保存到新表
                db.add_affix(content=final_conditions, description=preset_desc)
                print(f"已保存词缀预设: [{preset_desc}]")
        else:
            # 如果也没输入，默认 fallback
            # 如果 all_options 不为空，默认选第一个，否则给个硬编码默认
            if all_options:
                final_conditions = all_options[0][1]
                print(f"未输入，自动选择第一个配置: {all_options[0][0]}")
            else:
                print("未输入，将使用系统硬编码 '冰霜抗性' 防止报错")
                final_conditions = "冰霜抗性"

    washer.conditions = final_conditions
    
    # ---------------------------------------------------------
    # 第四步：确认并开始
    # ---------------------------------------------------------
    clear_screen()
    print("=== 第四步：确认执行 ===")
    print(f"物品配置: {selected_item_name}")
    print(f"词缀要求: {washer.conditions}")
    print(f"装备位置: {washer.gear_pos}")
    print("-" * 30)
    
    confirm = input("是否开始洗炼？(y/n) [y]: ").strip().lower()
    if confirm == 'n':
        print("已取消。")
        return
    washer.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已终止")
