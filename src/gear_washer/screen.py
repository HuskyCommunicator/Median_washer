import pyautogui
import pytesseract
import tempfile
import os
from PIL import Image, ImageOps, ImageChops
from typing import Tuple, Optional

class ScreenReader:
    def __init__(self, tesseract_cmd: str = None, debug_mode: bool = False):
        """
        :param tesseract_cmd: tesseract 可执行文件的路径，如果不在 PATH 中需要指定
        :param debug_mode: 是否启用调试模式，保存OCR识别的图片
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.debug_mode = debug_mode
        self.debug_counter = 0  # 用于给调试图片编号

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

    def read_text(self, region: Tuple[int, int, int, int], lang: str = 'chi_sim', scale_factor: float = 2.5) -> str:
        """
        读取指定区域的文字
        :param region: (left, top, width, height)
        :param lang: 语言代码，默认为简体中文 'chi_sim' (需要安装对应的 tesseract 语言包)
        :param scale_factor: 图片放大倍数，默认放大2.5倍以提高OCR准确度
        """
        image = self.capture_region(region)
        
        # 放大图片以提高OCR识别准确度
        if scale_factor > 1.0:
            original_size = image.size
            new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
            # 使用 LANCZOS 高质量缩放算法
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # === 图像预处理增强 (针对黑底彩字优化 V2) ===
        # 之前的强制二值化可能导致边缘锯齿和模糊。
        # 这里改用 HSV 的 V 通道（亮度）提取，这是处理"黑底任何亮色字"的通用解法。
        # 原理：HSV中的V代表亮度。
        #  - 黑色背景 (0,0,0) -> V=0
        #  - 蓝色文字 (0,0,255) -> V=255 (最大亮度)
        #  - 只有在普通的灰度转换中，蓝色才会变暗。在V通道里，它是最亮的。
        
        try:
            # 1. 转换为 HSV 模式
            if image.mode != 'HSV':
                # 注意：如果 convert 之前是 paletted 模式，可能需要先转 RGB
                image = image.convert('RGB').convert('HSV')
            
            # 2. 提取 V 通道 (此时图片是：黑底、高亮白字)
            # split 返回 (H, S, V)
            _, _, v = image.split()
            
            # 3. 反色 (变成 Tesseract 最喜欢的：白底、深黑字)
            # 此时蓝色文字变成了黑色，黑色背景变成了白色。
            # 我们不再做二值化(thresholding)，保留抗锯齿边缘，防止字体破碎或模糊。
            image = ImageOps.invert(v)
            
        except Exception as e:
            print(f"Image preprocessing failed: {e}, falling back to grayscale.")
            image = image.convert('L') # 降级处理
        # ====================
        
        # 调试模式：保存OCR识别的图片
        if self.debug_mode:
            debug_dir = "ocr_debug"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            self.debug_counter += 1
            debug_path = os.path.join(debug_dir, f"ocr_capture_{self.debug_counter}.png")
            image.save(debug_path)
            print(f"[调试] OCR图片已保存: {debug_path} (原始区域: {region}, 放大倍数: {scale_factor}x)")
        
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
