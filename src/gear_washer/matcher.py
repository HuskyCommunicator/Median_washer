import re
from typing import List, Union, Dict

class AffixMatcher:
    """
    处理词缀匹配逻辑。
    支持简单的字符串匹配，以及 AND/OR 逻辑组合。
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """简单的文本标准化，去除标点和多余空格，转小写"""
        text = text.lower()
        # 去除特殊字符，只保留文字数字
        text = re.sub(r'[^\w\s]', '', text)
        return text

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
            return keyword in raw_text

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
            for affix in affixes:
                if not affix.strip(): continue # 忽略空行
                kw = self.normalize_text(affix.strip())
                if kw in raw_text:
                    matched_count += 1
            
            # 根据类型判定
            if g_type == 'AND':
                # AND: 必须全部存在
                # 实际上 affixes 里所有词缀都必须找到
                if matched_count < len([a for a in affixes if a.strip()]):
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
        """
        # 1. 预处理表达式：将 && || 转换为 python 的 and or
        # 同时为了避免 eval 安全问题和变量名问题，我们采用“提取-替换-计算”的策略
        python_expr = expression.replace('&&', ' and ').replace('||', ' or ')
        
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
            is_exist = normalized_kw in raw_text
            context[kw] = is_exist

        # 4. 执行求值
        try:
            # 使用 eval 在受限上下文中执行
            return eval(python_expr, {"__builtins__": None}, context)
        except Exception as e:
            print(f"表达式解析失败: {expression}, 错误: {e}")
            return False
