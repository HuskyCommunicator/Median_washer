import time
import pyautogui
import json
try:
    import keyboard
except ImportError:
    keyboard = None

from .matcher import AffixMatcher
from .screen import ScreenReader

class GearWasher:
    def __init__(self, tesseract_cmd=None):
        self.matcher = AffixMatcher()
        self.screen = ScreenReader(tesseract_cmd)
        
        # 默认配置
        self.gear_pos = None     # (x, y) 装备悬停位置
        self.affix_region = None  # (x, y, w, h) 词缀识别区域
        self.wash_button_pos = None # (x, y) 洗炼按钮位置
        self.conditions = None
        self.max_attempts = 1000
        self.interval = 1.0 # 每次洗炼间隔(秒)

    def _wait_for_key(self):
        """等待按键确认坐标"""
        while True:
             if keyboard.is_pressed('space'):
                 # 防抖动
                 time.sleep(0.3)
                 return pyautogui.position()
             time.sleep(0.05)

    def _wait_for_limit(self):
        """倒计时等待坐标"""
        for i in range(3, 0, -1):
            print(f"倒计时 {i}...", end="\r")
            time.sleep(1)
        print(" " * 20, end="\r") # 清除倒计时文字
        return pyautogui.position()

    def setup_wizard(self):
        """
        交互式设置向导，辅助用户确定屏幕坐标
        """
        print("=== 装备洗炼脚本设置向导 ===")
        
        # 检查是否可以使用键盘触发
        if keyboard:
            print("说明：将鼠标移动到目标位置，然后按下 【Space 空格键】 确认记录。")
            wait_func = self._wait_for_key
        else:
            print("提示：未安装 keyboard 库，将使用倒计时模式。")
            print("说明：无需按键，倒计时结束时会自动记录当前鼠标位置。")
            wait_func = self._wait_for_limit
        
        # 1. 设置装备悬停位置
        print("\n[1/4] 请将鼠标移动到【装备图标】上（用于触发属性浮窗）...")
        gx, gy = wait_func()
        self.gear_pos = (gx, gy)
        print(f"记录装备位置: {self.gear_pos}")

        # 2. 设置词缀识别区域
        print("\n[2/4] 即将设置词缀区域 (OCR范围)。")
        print("提示：请确保浮窗可见。")
        
        print("请将鼠标移动到【词缀文字区域】的【左上角】...")
        x1, y1 = wait_func()
        print(f"记录左上角: ({x1}, {y1})")
        
        print("\n请将鼠标移动到【词缀文字区域】的【右下角】...")
        x2, y2 = wait_func()
        print(f"记录右下角: ({x2}, {y2})")
        
        # 自动纠正左上/右下，防止用户选反
        x = min(x1, x2)
        y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        self.affix_region = (x, y, width, height)
        print(f"词缀区域已设置为: {self.affix_region}")

        # 3. 设置洗炼按钮位置
        print("\n[3/4] 请将鼠标移动到【洗炼按钮中心】...")
        bx, by = wait_func()
        self.wash_button_pos = (bx, by)
        print(f"洗炼按钮位置已设置为: {self.wash_button_pos}")

        # 4. 设置目标词缀
        print("\n[4/4] 设置目标词缀逻辑")
        # 4. 设置目标词缀
        print("\n[4/4] 设置目标词缀逻辑")
        print("提示：支持复杂表达式，例如: 冰霜 || (火焰 && 攻速)")
        
        raw_input = input("请输入目标词缀 (直接回车保持默认): ").strip()
        if raw_input:
            self.conditions = raw_input
        elif not self.conditions:
            self.conditions = "冰霜抗性"

        print(f"当前匹配条件: {self.conditions}")
        print("\n设置完成！")

    def run(self):
        if not self.affix_region or not self.wash_button_pos or not self.gear_pos:
            print("错误: 未配置区域，请先运行 setup_wizard()")
            return

        print(f"开始执行洗炼，最大尝试次数: {self.max_attempts}")
        print("请在该窗口激活游戏/应用，然后不要移动鼠标干扰操作...")
        time.sleep(3) # 给用户一点时间切换窗口

        for i in range(self.max_attempts):
            print(f"\n--- 第 {i+1} 次尝试 ---")
            
            # 1. 移动到装备位置，显示浮窗
            # 使用 moveTo 移动鼠标，duration 防止移动过快游戏未响应
            pyautogui.moveTo(self.gear_pos[0], self.gear_pos[1], duration=0.2)
            # 等待浮窗显示
            time.sleep(0.5) 

            # 2. 识别当前属性
            text = self.screen.read_text(self.affix_region)
            clean_text = text.replace("\n", " | ")
            print(f"识别到的文本: {clean_text}")

            # 3. 判断是否满足条件
            if self.matcher.check(text, self.conditions):
                print(">>> 成功匹配到目标属性！停止洗炼。 <<<")
                
                # 尝试强制前台并置顶
                # 0x1000 (MB_SYSTEMMODAL) + 0x40000 (MB_TOPMOST)
                import ctypes
                try:
                    # 先尝试让当前进程转到前台（有时候不生效，但值得一试）
                    ctypes.windll.user32.SwitchToThisWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)
                except:
                    pass
                
                # 弹窗标志位：MB_ICONINFORMATION (0x40) | MB_SYSTEMMODAL (0x1000)
                # SYSTEMMODAL 比 TOPMOST 更强，会强制所有窗口响应
                ctypes.windll.user32.MessageBoxW(0, f'洗炼完成！\n已匹配到目标属性:\n{self.conditions}', '装备洗炼助手', 0x40 | 0x1000)
                break
            
            # 4. 不满足，点击洗炼
            print("未匹配，继续洗炼...")
            pyautogui.click(self.wash_button_pos[0], self.wash_button_pos[1])
            
            # 5. 等待动画或刷新
            time.sleep(self.interval)
            
            # --- 检测中止逻辑 ---
            if keyboard and keyboard.is_pressed('f5'):
                print("\n\n>>> 用户按下 F5，强制停止脚本。 <<<")
                break
            # --------------------

        else:
             print("已达到最大尝试次数，停止执行。")

if __name__ == "__main__":
    # 示例用法
    washer = GearWasher()
    
    # 你可以在这里硬编码配置，或者使用向导
    # washer.affix_region = (100, 100, 200, 300)
    # washer.wash_button_pos = (500, 500)
    # washer.conditions = {'OR': ['冰霜抗性', '火焰抗性']}
    
    # 启动向导
    washer.setup_wizard()
    
    # 确认执行
    confirm = input("是否开始执行？(y/n): ")
    if confirm.lower() == 'y':
        washer.run()
