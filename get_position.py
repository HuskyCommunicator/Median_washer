import pyautogui
import time
import keyboard  # 需要 pip install keyboard

def main():
    print("=== 鼠标坐标获取工具 ===")
    print("功能说明: ")
    print("1. 实时显示当前鼠标坐标。")
    print("2. 按下 'Space' (空格键) 记录并打印当前坐标。")
    print("3. 按下 'Esc' 退出程序。")
    print("-" * 30)

    try:
        while True:
            # 获取坐标
            x, y = pyautogui.position()
            
            # 实时刷新显示 (使用 \r 回车符覆盖当前行)
            print(f"当前坐标: X={x}, Y={y}   (按 Space 记录)", end="\r")
            
            # 检测空格键按下
            if keyboard.is_pressed('space'):
                # 打印并换行，避免被下一次刷新覆盖
                print(f"\n[记录点位] -> ({x}, {y})")
                # 防抖动，避免按一下触发多次
                time.sleep(0.3)
            
            # 检测退出
            if keyboard.is_pressed('esc'):
                print("\n\n程序已退出。")
                break
            
            # 降低 CPU 占用
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n用户强制中断。")

if __name__ == "__main__":
    main()
