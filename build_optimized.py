import os
import shutil
import subprocess
import sys

def build():
    # 1. 清理旧构建
    print(">>>正在清理旧构建文件...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # 2. 确定 OCR 路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ocr_source = os.path.join(base_dir, 'OCR')
    
    # 3. 运行 PyInstaller
    # --noconsole: 不显示黑框
    # --name: 名字
    # --clean: 清理缓存
    print(">>> 正在运行 PyInstaller...")
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        'gui.py',
        '--name=MedianWasher_Pro',
        '--noconsole',
        '--clean',
        '--collect-all=customtkinter', # 确保 customtkinter 资源被包含
        # 如果有图标，可以加 --icon=icon.ico
    ]
    
    subprocess.check_call(cmd)
    
    # 4. 后处理：精简并复制 OCR 目录
    print(">>> 正在复制并精简 OCR 目录...")
    dist_dir = os.path.join(base_dir, 'dist', 'MedianWasher_Pro')
    dist_ocr_dir = os.path.join(dist_dir, 'OCR')
    
    if not os.path.exists(dist_ocr_dir):
        os.makedirs(dist_ocr_dir)
        
    # 4.1 复制必要的 DLL 和 EXE
    needed_extensions = ['.dll', '.exe']
    # 不需要打包的 exe (训练工具等)
    exclude_exes = [
        'ambiguous_words.exe', 'classifier_tester.exe', 'cntraining.exe', 
        'combine_lang_model.exe', 'combine_tessdata.exe', 'dawg2wordlist.exe', 
        'lstmeval.exe', 'lstmtraining.exe', 'merge_unicharsets.exe', 
        'mftraining.exe', 'set_unicharset_properties.exe', 'shapeclustering.exe', 
        'text2image.exe', 'unicharset_extractor.exe', 'wordlist2dawg.exe',
        'tesseract-uninstall.exe', 'winpath.exe'
    ]
    
    for item in os.listdir(ocr_source):
        src_path = os.path.join(ocr_source, item)
        if os.path.isfile(src_path):
            ext = os.path.splitext(item)[1].lower()
            if ext in needed_extensions:
                if item in exclude_exes:
                    continue
                shutil.copy2(src_path, os.path.join(dist_ocr_dir, item))
                
    # 4.2 复制 tessdata (只复制中文和英文)
    print(">>> 正在处理语言包 (只保留 chi_sim 和 eng)...")
    tess_src = os.path.join(ocr_source, 'tessdata')
    tess_dst = os.path.join(dist_ocr_dir, 'tessdata')
    if not os.path.exists(tess_dst):
        os.makedirs(tess_dst)
    
    # 必要的语言文件前缀
    needed_langs = ['chi_sim', 'eng', 'chi_sim_vert', 'osd'] # osd 是方向检测，通常最好带上
    
    for item in os.listdir(tess_src):
        src_item = os.path.join(tess_src, item)
        dst_item = os.path.join(tess_dst, item)

        # 如果是目录 (如 configs, tessconfigs, script)，递归复制
        if os.path.isdir(src_item):
            print(f"   [+] Copying folder {item}")
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item)
            shutil.copytree(src_item, dst_item)
            continue

        # 如果是文件
        if not item.endswith('.traineddata'):
            # 复制配置文件 (pdf.ttf, jars等，虽然可能用不到，但为了安全起见保留非数据大文件)
            # jars 都挺小的，ttf 也小。
            shutil.copy2(src_item, dst_item)
            continue
            
        # 检查是否是需要的语言
        is_needed = False
        for lang in needed_langs:
            if item.startswith(lang):
                is_needed = True
                break
        
        if is_needed:
            print(f"   [+] Copying {item}")
            shutil.copy2(src_item, dst_item)

    # 5. 创建调试目录
    debug_dir = os.path.join(dist_dir, 'ocr_debug')
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
        
    print(f"\n>>> 打包完成！输出目录: {dist_dir}")
    print(">>> 你可以直接压缩该文件夹分享给朋友。")

if __name__ == '__main__':
    build()
