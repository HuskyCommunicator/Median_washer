import re
from typing import List, Union, Dict
import difflib

class AffixMatcher:
    """
    处理词缀匹配逻辑。
    支持简单的字符串匹配，以及 AND/OR 逻辑组合。
    """
    
    # 默认相似度阈值 (0.0 - 1.0)，建议 0.7 左右
    DEFAULT_THRESHOLD = 0.7

    @staticmethod
    def normalize_text(text: str) -> str:
        """简单的文本标准化，去除标点和多余空格，转小写"""
        text = text.lower()
        # 将特殊字符替换为空格，而不是直接删除，防止 "法术伤害+10%" 变成 "法术伤害10" 导致的粘连
        text = re.sub(r'[^\w\s]', ' ', text)
        # 合并多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _fuzzy_contains(self, haystack: str, needle: str, threshold: float = None) -> bool:
        """
        检查 haystack (长文本) 中是否模糊包含 needle (关键词)。
        使用滑动窗口 + SequenceMatcher。
        """
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD

        if not needle:
            return True
        if not haystack:
            return False
            
        # 如果是精确包含，直接返回 True (性能优化)
        if needle in haystack:
            return True

        n_len = len(needle)
        h_len = len(haystack)
        
        # 如果关键词比文本还长，直接算两个字符串的相似度
        if n_len > h_len:
             return difflib.SequenceMatcher(None, haystack, needle).ratio() >= threshold

        # 滑动窗口匹配
        # 窗口大小允许一定的浮动，例如 +/- 2 个字符，应对 OCR 多字/少字的情况
        window_sizes = [n_len, n_len + 1, n_len - 1]
        
        # 优化: 只在特定步长滑动，减少计算量
        step = 1 if n_len < 10 else 2
        
        for w_len in window_sizes:
            if w_len <= 0: continue
            for i in range(0, h_len - w_len + 1, step):
                # 截取窗口
                sub_str = haystack[i : i + w_len]
                # 计算相似度
                ratio = difflib.SequenceMatcher(None, sub_str, needle).ratio()
                if ratio >= threshold:
                    return True
                    
        return False

    def _extract_number_after(self, text: str, keyword: str) -> Union[float, None]:
        """
        在 text 中找到 keyword 后，提取紧随其后的数值。
        支持整数和小数，支持 % 号（虽然通常只提取数字部分）。
        
        [重要修复] 这里不仅要向后找，如果向后找的紧邻内容是换行符或无关内容，
        而数字其实是在关键词的前面（例如 "+75% 法术伤害"），
        那么需要尝试向前提取数字。
        
        [最新修复] OCR 有时会有竖线 | 作为边缘噪点或其他分割符，
        如果提取到的数字跨越了 | 那肯定是错的。
        """
        if not text or not keyword:
            return None

        # 1. 找到关键词位置
        idx = text.find(keyword)
        if idx == -1:
            return None
        
        kw_len = len(keyword)
        
        # --- 策略 A: 尝试向后提取 (适用于 "力量 +50" 这种格式) ---
        # 截取关键词后面的一小段，比如 20 个字符
        start_search = idx + kw_len
        # 先找到第一个换行符或者 | 符号，作为硬性边界
        stop_chars = ['\n', '|']
        snippet_end = start_search + 20
        
        for char in stop_chars:
            stop_idx = text.find(char, start_search)
            if stop_idx != -1 and stop_idx < snippet_end:
                snippet_end = stop_idx
                
        snippet_after = text[start_search : snippet_end]
        
        # 简单的正则: 允许少量空格或冒号或加号，紧接着数字
        regex_after = r'^[:\+\s=\-]*(\d+\.?\d*)' 
        match_after = re.search(regex_after, snippet_after)
        
        val_after = None
        if match_after:
            try:
                val_str = match_after.group(1)
                # 再次校验：如果匹配到的数字后面紧跟着就是 | (虽然 snippet 截断了，但为了保险)
                # 其实不用，因为 snippet 已经截断了
                if val_str: 
                     val_after = float(val_str)
            except: pass

        if val_after is not None:
            return val_after

        # --- 策略 B: 尝试向前提取 (适用于 "+75% 法术伤害" 这种格式) ---
        # 截取关键词前面的一小段
        end_search = idx
        start_search = max(0, idx - 20)
        
        # 同样需要截断，如果前面有换行符或 |
        # 我们要找的是离 end_search 最近的的那个阻断符
        # 因为是从左往右找，所以要找 snippet 里的 *最后一个* 阻断符
        snippet_before_raw = text[start_search : end_search]
        
        last_stop_idx = -1
        for char in stop_chars:
            # 在片段里找最后一次出现的位置
            p = snippet_before_raw.rfind(char)
            if p > last_stop_idx:
                last_stop_idx = p
                
        if last_stop_idx != -1:
            # 只保留阻断符之后的内容
            snippet_before = snippet_before_raw[last_stop_idx+1:]
        else:
            snippet_before = snippet_before_raw
            
        # 正则: 找结尾处的数字
        regex_before = r'(\d+\.?\d*)[%\s\+\-]*$'
        match_before = re.search(regex_before, snippet_before)
        
        if match_before:
            try:
                val_str = match_before.group(1)
                return float(val_str)
            except: pass
            
        # --- 策略 C: 尝试行首提取 (适用于 "97 冰冻系法术伤害" 但关键词只是 "系法术伤害" 这种情况) ---
        # 如果前两种都没找到，且这一整行本来就是为了这个属性服务的，
        # 那么数值很有可能就在行的最开头（绝大多数暗黑装备属性都是这样：数值 + 描述）
        
        # 必须确保我们是在处理单行文本（通过判断 text 是否包含换行符来简单猜测，或者直接试）
        # 用于 lines 模式下的 line_norm
        regex_head = r'^[:\+\s=\-]*(\d+\.?\d*)'
        match_head = re.search(regex_head, text)
        
        if match_head:
            try:
                val_str = match_head.group(1)
                return float(val_str)
            except: pass
            
        return None

    def check(self, screen_text: str, conditions: Union[str, List, Dict]) -> bool:
        """
        检查屏幕文本是否满足条件。
        
        :param screen_text: OCR 识别出的整段文本
        :param conditions: 匹配条件
        """
        # --- [重大架构升级] 基于行的分割策略 ---
        # 既然 OCR 返回的文本混杂在一起容易串行，我们先按换行符和竖线强制分割成独立的小段。
        # 每一个小段作为一个独立的检测单元 (line_segment)。
        # 只有当某个小段里同时包含关键词和符合要求的数值时，才算匹配成功。
        
        # 1. 预处理：按 \n 或 | 分割
        # 先统一换行符
        screen_text_clean = screen_text.replace('\r\n', '\n').replace('|', '\n')
        lines = [line.strip() for line in screen_text_clean.split('\n') if line.strip()]
        
        # 2. 为了兼容旧逻辑（如果用户只给了一个大字符串查模糊匹配），
        # 我们同时也保留一份整段的 normalized 文本。
        # 但对于数值检查，我们必须强制使用 lines 逻辑。
        full_normalized_text = self.normalize_text(screen_text)

        # 1. 复杂规则组 (List of Dicts with 'idx', 'type' etc.)
        if isinstance(conditions, list) and len(conditions) > 0 and isinstance(conditions[0], dict) and 'type' in conditions[0]:
            return self._check_complex_groups_v2(lines, full_normalized_text, conditions)

        if isinstance(conditions, str):
            # 检查是否包含逻辑运算符
            if '&&' in conditions or '||' in conditions or ('(' in conditions and ')' in conditions):
                return self._check_expression(full_normalized_text, conditions)
            
            # 简单单词匹配 (如果不涉及数值，还是查全文最稳，防止 OCR 意外断行把一个词切断)
            keyword = self.normalize_text(conditions)
            return self._fuzzy_contains(full_normalized_text, keyword)

        elif isinstance(conditions, list):
            return all(self.check(screen_text, cond) for cond in conditions)

        return False

    def _check_complex_groups_v2(self, lines: List[str], full_text_norm: str, groups: List[Dict]) -> bool:
        """
        [新版] 复杂规则检查，基于行 (lines) 来做数值提取的上下文隔离。
        """
        for group in groups:
            g_type = group.get('type', 'AND')
            affixes = group.get('affixes', [])
            
            # 计算当前组里有多少个词缀匹配上了
            matched_count = 0
            
            for affix_item in affixes:
                affix_text = ""
                min_val = None
                max_val = None
                
                if isinstance(affix_item, dict):
                    affix_text = affix_item.get('name', '')
                    min_val = affix_item.get('min_value') 
                    max_val = affix_item.get('max_value')
                elif isinstance(affix_item, str):
                    affix_text = affix_item
                
                if not affix_text.strip(): continue
                
                kw_normalized = self.normalize_text(affix_text.strip())
                affix_match_found = False
                
                # --- 分支 1: 如果是复杂逻辑表达式 (&& ||) ---
                if '&&' in affix_text or '||' in affix_text:
                     # 表达式无法简单对应到单行，只能查全文
                     if self._check_expression(full_text_norm, affix_text):
                         affix_match_found = True

                # --- 分支 2: 需要数值检查 ---
                elif min_val is not None or max_val is not None:
                    # [关键改变] 必须在【同一行】里既找到关键词，又找到数值
                    # 遍历每一行寻找匹配
                    for line in lines:
                        # 1. 先看这行有没有关键词 (模糊匹配)
                        line_norm = self.normalize_text(line)
                        kw_normalized = self.normalize_text(affix_text.strip())
                        
                        if self._fuzzy_contains(line_norm, kw_normalized):
                            val = self._extract_number_after(line_norm, kw_normalized)
                            if val is not None:
                                is_min_ok = True
                                is_max_ok = True
                                if min_val is not None and val < float(min_val): is_min_ok = False
                                if max_val is not None and val > float(max_val): is_max_ok = False
                                
                                if is_min_ok and is_max_ok:
                                    affix_match_found = True
                                    break

                # --- 分支 3: 纯文本检查 (不需要数值) ---
                else:
                    kw_normalized = self.normalize_text(affix_text.strip())
                    if self._fuzzy_contains(full_text_norm, kw_normalized):
                         affix_match_found = True
                
                if affix_match_found:
                    matched_count += 1
            
            # (后半部分逻辑不变: 判断 group 是否满足)
            if g_type == 'AND':
                total_valid = 0
                for a in affixes:
                    if isinstance(a, str):
                         if a.strip(): total_valid += 1
                    elif isinstance(a, dict):
                         if a.get('name', '').strip(): total_valid += 1
                if matched_count < total_valid: return False
                    
            elif g_type == 'NOT':
                if matched_count > 0: return False
                    
            elif g_type == 'COUNT':
                min_v = group.get('min')
                max_v = group.get('max')
                if min_v is not None and matched_count < int(min_v): return False
                if max_v is not None and matched_count > int(max_v): return False
                    
        return True

    def _check_complex_groups(self, raw_text: str, groups: List[Dict]) -> bool:
         # 保留这个空壳方法或者直接删除，现在 logic 转移到了 _check_complex_groups_v2
         return False

    def _check_expression(self, raw_text: str, expression: str) -> bool:
        """
        解析并执行复杂逻辑表达式
        例如: "冰霜抗性 && (攻速 || 暴击)"
        支持 ! 符号表示非，例如 "!冰冻"
        """
        # 1. 预处理表达式：将 && || ! 转换为 python 的 and or not
        # 同时为了避免 eval 安全问题和变量名问题，我们采用“提取-替换-计算”的策略
        # 注意替换顺序
        python_expr = expression.replace('&&', ' and ').replace('||', ' or ').replace('!', ' not ')
        
        # 2. 提取所有可能的关键词（假设关键词是非特殊符号的连续串）
        # 排除 Python 关键字
        reserved = {'and', 'or', 'not', 'True', 'False'}
        # 匹配中英文、数字组合的关键词
        potential_keywords = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', python_expr))
        keywords = potential_keywords - reserved
        
        # 3. 计算每个关键词是否存在
        context = {}
        for kw in keywords:
            # 归一化关键词进行比对
            normalized_kw = self.normalize_text(kw)
            is_exist = self._fuzzy_contains(raw_text, normalized_kw)
            context[kw] = is_exist

        # 4. 执行求值
        try:
            # 使用 eval 在受限上下文中执行
            return eval(python_expr, {"__builtins__": None}, context)
        except Exception as e:
            print(f"表达式解析失败: {expression}, 错误: {e}")
            return False
