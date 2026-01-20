"""
测试 OCR 调试模式功能
"""
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gear_washer.screen import ScreenReader

# 获取 Tesseract 路径
base_dir = os.path.dirname(os.path.abspath(__file__))
OCR_CMD = os.path.join(base_dir, 'OCR', 'tesseract.exe')

print("=" * 60)
print("OCR 调试模式测试")
print("=" * 60)
print(f"OCR 路径: {OCR_CMD}")
print(f"当前工作目录: {os.getcwd()}")
print()

# 创建 ScreenReader 实例，启用调试模式
print("创建 ScreenReader (调试模式已启用, 放大5倍)...")
reader = ScreenReader(tesseract_cmd=OCR_CMD, debug_mode=True)

print(f"调试模式状态: {reader.debug_mode}")
print(f"调试计数器: {reader.debug_counter}")
print()

# 测试不同的放大倍数
test_regions = [
    ((100, 100, 200, 100), 3.0, "3倍放大"),
    ((100, 100, 200, 100), 5.0, "5倍放大"),
    ((100, 100, 200, 100), 8.0, "8倍放大"),
]

for region, scale, desc in test_regions:
    print(f"测试 {desc} - 区域: {region}")
    try:
        text = reader.read_text(region, lang='chi_sim', scale_factor=scale)
        print(f"  OCR 识别结果: {repr(text[:50]) if text else '(空)'}")
    except Exception as e:
        print(f"  错误: {e}")
    print()

print("检查 ocr_debug/ 目录中的文件:")
if os.path.exists("ocr_debug"):
    files = os.listdir("ocr_debug")
    print(f"  共 {len(files)} 个文件: {files}")
else:
    print("  警告: ocr_debug/ 目录不存在！")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
