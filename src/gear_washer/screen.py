import pyautogui
import pytesseract
from PIL import Image
from typing import Tuple, Optional

class ScreenReader:
    def __init__(self, tesseract_cmd: str = None):
        """
        :param tesseract_cmd: tesseract 可执行文件的路径，如果不在 PATH 中需要指定
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def capture_region(self, region: Tuple[int, int, int, int]) -> Image.Image:
        """
        截取指定区域的屏幕
        region: (left, top, width, height)
        """
        return pyautogui.screenshot(region=region)

    def read_text(self, region: Tuple[int, int, int, int], lang: str = 'chi_sim') -> str:
        """
        读取指定区域的文字
        :param region: (left, top, width, height)
        :param lang: 语言代码，默认为简体中文 'chi_sim' (需要安装对应的 tesseract 语言包)
        """
        image = self.capture_region(region)
        # 这里可以加入图像预处理代码，比如二值化，以提高识别率
        # image = image.convert('L') ...
        text = pytesseract.image_to_string(image, lang=lang)
        return text

    @staticmethod
    def get_mouse_position() -> Tuple[int, int]:
        """获取当前鼠标位置，用于辅助设置坐标"""
        return pyautogui.position()
