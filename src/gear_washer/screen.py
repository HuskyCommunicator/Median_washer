import pyautogui
import pytesseract
import tempfile
import os
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
        # Ensure region has valid dimensions
        x, y, w, h = region
        if w <= 0 or h <= 0:
             # Use a 1x1 dummy image or raise error to avoid crashing later
             print(f"Warning: Invalid capture region: {region}, defaulting to 1x1")
             return Image.new('RGB', (1, 1), color='black')
             
        try:
            return pyautogui.screenshot(region=region)
        except Exception as e:
            print(f"Screenshot failed for region {region}: {e}")
            return Image.new('RGB', (1, 1), color='black')

    def read_text(self, region: Tuple[int, int, int, int], lang: str = 'chi_sim') -> str:
        """
        读取指定区域的文字
        :param region: (left, top, width, height)
        :param lang: 语言代码，默认为简体中文 'chi_sim' (需要安装对应的 tesseract 语言包)
        """
        image = self.capture_region(region)
        
        # Temporary workaround for PIL saving issue (SystemError: tile cannot extend outside image)
        # We manually save to a BMP file and pass the path to pytesseract
        with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp_file:
            temp_filename = tmp_file.name
            
        try:
            # Save as BMP (lossless, uncompressed, usually robust)
            image.save(temp_filename)
            text = pytesseract.image_to_string(temp_filename, lang=lang)
        except Exception as e:
            print(f"OCR Error: {e}")
            text = ""
        finally:
             if os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                except OSError:
                    pass
                    
        return text

    @staticmethod
    def get_mouse_position() -> Tuple[int, int]:
        """获取当前鼠标位置，用于辅助设置坐标"""
        return pyautogui.position()
