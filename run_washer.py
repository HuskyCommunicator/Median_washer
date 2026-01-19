import sys
import os

# 将 src 加入 Python 路径，确保可以导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from gear_washer.washer import GearWasher
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    sys.exit(1)

def main():
    print("正在启动装备洗炼助手...")
    
    # 可以在这里指定 tesseract 路径，例如：
    # tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    tesseract_cmd = r'C:\tool\OCR\tesseract.exe' 
    
    washer = GearWasher(tesseract_cmd=tesseract_cmd)
    
    try:
        washer.setup_wizard()
        confirm = input("配置完成，是否开始执行洗炼？(y/n): ")
        if confirm.lower() == 'y':
            washer.run()
    except KeyboardInterrupt:
        print("\n用户中断执行。")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
