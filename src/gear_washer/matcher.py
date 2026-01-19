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
               - 字符串: 
                   1. 简单关键词: "冰霜抗性"
                   2. 复杂表达式: "冰霜抗性 && (攻击速度 || 暴击率)" (包含 && || 符号时自动启用表达式模式)
               - 列表: 默认视为 AND 关系
               - 字典: {'AND': [...], 'OR': [...]}
        """
        raw_text = self.normalize_text(screen_text)

        if isinstance(conditions, str):
            # 检查是否包含逻辑运算符，如果是，走复杂表达式逻辑
            if '&&' in conditions or '||' in conditions or ('(' in conditions and ')' in conditions):
                return self._check_expression(raw_text, conditions)
            
            # 否则走简单单词匹配
            keyword = self.normalize_text(conditions)
            return keyword in raw_text

        elif isinstance(conditions, list):
            # 列表默认是 AND 关系
            return all(self.check(screen_text, cond) for cond in conditions)

        elif isinstance(conditions, dict):
            # 字典支持 AND / OR
            if 'OR' in conditions:
                res = any(self.check(screen_text, cond) for cond in conditions['OR'])
                if not res: return False
            
            if 'AND' in conditions:
                res = all(self.check(screen_text, cond) for cond in conditions['AND'])
                if not res: return False
            
            return True
        
        return False

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
