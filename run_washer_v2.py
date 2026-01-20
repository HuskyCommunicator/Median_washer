from src.gear_washer.washer import GearWasher
import sys
import os
import time
from config.affix_config import MY_CONDITIONS as FILE_DEFAULT_CONDITIONS
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
    db = SimpleDB()
    washer = GearWasher(tesseract_cmd=OCR_CMD)
    
    # ---------------------------------------------------------
    # 第一步：选择物品类型 (Item Position)
    # ---------------------------------------------------------
    clear_screen()
    print("=== 第一步：选择物品类型 (位置配置) ===")
    
    # 查找所有以 'preset_' 或 'item_' 开头的配置
    # 兼容之前的 'preset_' 前缀
    item_keys = db.list_keys("preset_") + db.list_keys("item_")
    # 去重并去掉前缀显示
    item_options = []
    seen = set()
    for k in item_keys:
        if k in seen: continue
        seen.add(k)
        display_name = k.replace("preset_", "").replace("item_", "")
        item_options.append((display_name, k))
    
    # 排序，保证顺序稳定
    item_options.sort(key=lambda x: x[0])

    print("已有配置:")
    for idx, (name, key) in enumerate(item_options):
        print(f"  [{idx + 1}] {name}")
    print(f"  [{len(item_options) + 1}] + 新建/手动定位")
    
    choice = input("\n请选择 (输入序号): ").strip()
    
    selected_item_key = None
    selected_item_name = None
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(item_options):
            selected_item_name, selected_item_key = item_options[idx]
            print(f"已选择: {selected_item_name}")
    
    # ---------------------------------------------------------
    # 第二步：使用位置 or 重新定位
    # ---------------------------------------------------------
    clear_screen()
    print("=== 第二步：位置配置确认 ===")
    
    pos_data = None
    need_calibrate = False
    
    if selected_item_key:
        pos_data = db.get(selected_item_key)
        if pos_data:
            print(f"加载配置数据成功。")
            re_cal = input("是否需要重新定位此物品? (y/n) [n]: ").strip().lower()
            if re_cal == 'y':
                need_calibrate = True
        else:
            print("数据读取错误，需要重新定位。")
            need_calibrate = True
    else:
        # 新建模式
        print("您选择了新建配置。")
        selected_item_name = input("请输入新物品的名称 (例如 '火法杖'): ").strip()
        if not selected_item_name:
            selected_item_name = f"Item_{int(time.time())}"
        selected_item_key = f"preset_{selected_item_name}"
        need_calibrate = True

    if need_calibrate:
        # 调用交互式定位
        pos_data = washer.calibrate_ui()
        # 存储
        db.set(selected_item_key, pos_data)
        print(f"已将新位置保存为: [{selected_item_name}]")
    
    # 应用位置配置
    washer.gear_pos = pos_data['gear_pos']
    washer.wash_button_pos = pos_data['wash_button']
    # 计算 affix_region
    p1, p2 = pos_data['affix_points']
    washer.affix_region = calculate_rect(p1, p2)
    
    # ---------------------------------------------------------
    # 第三步：选择词缀 (Affix)
    # ---------------------------------------------------------
    clear_screen()
    print("=== 第三步：选择洗炼词缀 ===")
    
    affix_keys = db.list_keys("affix_")
    affix_options = []
    # 总是把配置文件作为第一个选项
    print("  [1] 使用配置文件默认 (affix_config.py)")
    print(f"      内容: {str(FILE_DEFAULT_CONDITIONS)[:40]}...")
    
    for idx, k in enumerate(affix_keys):
        name = k.replace("affix_", "")
        val = db.get(k)
        preview = str(val)[:20]
        print(f"  [{idx + 2}] {name} (内容: {preview}...)")
        affix_options.append((name, k, val))
        
    print(f"  [{len(affix_options) + 2}] + 手动输入新词缀")

    choice_aff = input("\n请选择 (输入序号): ").strip()
    
    final_conditions = None
    
    if choice_aff == '1' or choice_aff == '':
        final_conditions = FILE_DEFAULT_CONDITIONS
        print("已使用配置文件默认词缀。")
    elif choice_aff.isdigit():
        idx = int(choice_aff) - 2 # 偏移量 (选项1是文件)
        if 0 <= idx < len(affix_options):
            name, key, val = affix_options[idx]
            final_conditions = val
            print(f"已选择预设词缀: {name}")
        else:
            # 手动输入 (fallthrough)
            pass
            
    if final_conditions is None:
        # 手动输入模式
        print("\n请输入目标词缀逻辑 (支持 &&, || 等):")
        raw_input = input("> ").strip()
        if raw_input:
            final_conditions = raw_input
            # 询问是否保存
            save_yn = input("是否保存此词缀为预设? (y/n) [y]: ").strip().lower()
            if save_yn != 'n':
                preset_name = input("请输入预设名称 (例如 '冰法通用'): ").strip()
                if not preset_name:
                    preset_name = "未命名"
                db.set(f"affix_{preset_name}", final_conditions)
                print(f"已保存词缀预设: [{preset_name}]")
        else:
            print("未输入，将使用默认 '冰霜抗性' 防止报错")
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
