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

    def check(self, screen_text: str, conditions: Union[str, List, Dict]) -> bool:
        """
        检查屏幕文本是否满足条件。
        
        :param screen_text: OCR 识别出的整段文本
        :param conditions: 匹配条件
        """
        raw_text = self.normalize_text(screen_text)

        # 1. 复杂规则组 (List of Dicts with 'idx', 'type' etc.)
        # 识别特征: 是列表，且元素是字典，且字典里有 'type' 字段
        if isinstance(conditions, list) and len(conditions) > 0 and isinstance(conditions[0], dict) and 'type' in conditions[0]:
            return self._check_complex_groups(raw_text, conditions)

        if isinstance(conditions, str):
            # 检查是否包含逻辑运算符，如果是，走复杂表达式逻辑
            if '&&' in conditions or '||' in conditions or ('(' in conditions and ')' in conditions):
                return self._check_expression(raw_text, conditions)
            
            # 否则走简单单词匹配
            keyword = self.normalize_text(conditions)
            return self._fuzzy_contains(raw_text, keyword)

        elif isinstance(conditions, list):
            # 普通字符串列表默认是 AND 关系 (旧逻辑兼容)
            return all(self.check(screen_text, cond) for cond in conditions)

        return False

    def _check_complex_groups(self, raw_text: str, groups: List[Dict]) -> bool:
        """
        处理高级规则组逻辑
        所有 group 之间默认是 AND 关系 (必须全部满足)
        """
        for group in groups:
            g_type = group.get('type', 'AND')
            affixes = group.get('affixes', [])
            
            # 计算当前组里有多少个词缀匹配上了
            matched_count = 0
            for affix_item in affixes:
                # 兼容旧格式(str)和新格式(dict: {name: 'xxx', exact: true})
                affix_str = ""
                
                if isinstance(affix_item, dict):
                    affix_str = affix_item.get('name', '')
                elif isinstance(affix_item, str):
                    affix_str = affix_item
                
                if not affix_str.strip(): continue

                kw_normalized = self.normalize_text(affix_str.strip())
                
                # 模糊匹配 或 表达式匹配
                # 如果 affix_str 包含逻辑符号 && ||，则作为表达式处理
                if '&&' in affix_str or '||' in affix_str:
                        # 这里调用 _check_expression 而不是递归调用 check，
                        # 因为我们已经有了 normailzed 的 raw_text，不需要再次 normalize
                        if self._check_expression(raw_text, affix_str):
                            matched_count += 1
                else:
                    # 普通包含匹配 (使用模糊匹配)
                    if self._fuzzy_contains(raw_text, kw_normalized):
                        matched_count += 1
            
            # 根据类型判定
            if g_type == 'AND':
                # AND: 必须全部存在
                # 计算有效词缀总数 (需兼容 str 和 dict)
                total_valid = 0
                for a in affixes:
                    if isinstance(a, str):
                        if a.strip(): total_valid += 1
                    elif isinstance(a, dict):
                        if a.get('name', '').strip(): total_valid += 1
                        
                if matched_count < total_valid:
                    return False
                    
            elif g_type == 'NOT':
                # NOT: 必须全部不存在 (count == 0)
                if matched_count > 0:
                    return False
                    
            elif g_type == 'COUNT':
                # COUNT: 数量限制
                min_val = group.get('min')
                max_val = group.get('max')
                
                if min_val is not None and matched_count < int(min_val):
                    return False
                if max_val is not None and matched_count > int(max_val):
                    return False
                    
        # e.g. 所有组都通过
        return True

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
