from src.gear_washer.washer import GearWasher
import sys
import os
from config.affix_config import MY_CONDITIONS  # 从词缀配置文件导入
from config.position_config import CONFIG, USE_HARDCODED_CONFIG  # 从坐标配置文件导入

# 配置区 (你可以在这里"写在代码中")
# -----------------------------------------------------------------------------

# 1. 词缀匹配条件：已移至 config/affix_config.py 文件中配置
# 2. 坐标配置：已移至 config/position_config.py 文件中配置
 
# 3. Tesseract 路径
# 优先使用当前目录下的 OCR，方便打包或迁移
base_dir = os.path.dirname(os.path.abspath(__file__))
OCR_CMD = os.path.join(base_dir, 'OCR', 'tesseract.exe')
print(f"OCR 路径: {OCR_CMD}")

# -----------------------------------------------------------------------------

def calculate_rect(p1, p2):
    """根据两个对角点计算 (x, y, w, h)"""
    x1, y1 = p1
    x2, y2 = p2
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    return (x, y, w, h)

def main():
    print("正在启动装备洗炼助手...")
    
    washer = GearWasher(tesseract_cmd=OCR_CMD)
    
    # 应用代码中的配置
    washer.conditions = MY_CONDITIONS
    
    if USE_HARDCODED_CONFIG:
        print("使用硬编码配置，跳过向导...")
        # 自动计算矩形区域
        washer.affix_region = calculate_rect(CONFIG['affix_points'][0], CONFIG['affix_points'][1])
        washer.wash_button_pos = CONFIG['wash_button']
        washer.gear_pos = CONFIG['gear_pos']
    else:
        # 使用向导交互设置
        washer.setup_wizard()
        
    
    confirm = input(f"当前匹配规则: [{washer.conditions}]\n是否开始执行洗炼？(y/n): ")
    if confirm.lower() == 'y':
        try:
            washer.run()
        except KeyboardInterrupt:
            print("\n用户停止。")

if __name__ == "__main__":
    main()
