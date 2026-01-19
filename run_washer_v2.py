from src.gear_washer.washer import GearWasher
import sys
import os

# 配置区 (你可以在这里"写在代码中")
# -----------------------------------------------------------------------------

# 1. 词缀匹配条件
# 支持以下语法：
#   - 简单文本: "冰霜抗性"
#   - 复杂逻辑: "冰霜 && (攻击速度 || 暴击率)"
#   - 更复杂逻辑: "技能等级+3 && (抗性 || 血量)"
MY_CONDITIONS = "冰霜 && (攻速 || 暴击)"
 
# 2. 是否跳过向导直接使用硬编码坐标？
# 如果你已经确定了坐标，可以将 USE_HARDCODED_CONFIG 设置为 True，并填写下面的坐标
USE_HARDCODED_CONFIG = False

CONFIG = {
    # 词缀区域：现在支持直接填两个对角点 (点A, 点B)
    # 系统会自动计算矩形范围，你可以填 (左上, 右下) 或者 (左下, 右上) 等任意对角
    'affix_points': ((476, 241), (796, 531)), 
    
    'wash_button': (800, 600),             # (x, y)
    'gear_pos': (400, 300)                 # (x, y)
}

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
