"""
数字标准化引擎

根据技术方案手册2.2，处理审计场景中的多种数字格式：
- 千分位: 1,234,567
- 中文单位: 123.4万、1.2亿
- 小数点: 1234567.89
- 负数表示: (1234567) 或 -1234567
"""

import re
from typing import Union


class NumberNormalizer:
    """
    数字标准化引擎

    用于统一数字格式以支持准确比对
    """

    # 中文单位
    CHINESE_UNITS = {
        '万': 10000,
        '亿': 100000000,
        '千': 1000,
        '百': 100,
    }

    def normalize(self, text: str) -> float:
        """
        统一数字格式标准化

        参数：
            text: 数字字符串，如 "1,234,567" 或 "123.4万"

        返回：
            float: 标准化后的数值
        """
        if not text:
            return 0.0

        text = text.strip()

        # 处理千分位（去除逗号）
        if ',' in text:
            text = text.replace(',', '')

        # 处理中文单位
        for unit, multiplier in self.CHINESE_UNITS.items():
            if unit in text:
                try:
                    num = float(text.replace(unit, ''))
                    return num * multiplier
                except ValueError:
                    pass

        # 处理括号表示负数
        if text.startswith('(') and text.endswith(')'):
            try:
                num = float(text[1:-1])
                return -num
            except ValueError:
                pass

        # 处理普通负数
        if text.startswith('-'):
            try:
                return float(text)
            except ValueError:
                pass

        # 处理普通数字
        try:
            return float(text)
        except ValueError:
            return 0.0

    def compare_numbers(
        self,
        num_a: Union[str, float, int],
        num_b: Union[str, float, int],
        tolerance: float = 0.01
    ) -> bool:
        """
        数字比对（支持容差）

        参数：
            num_a: 第一个数字（字符串或数值）
            num_b: 第二个数字（字符串或数值）
            tolerance: 容差，默认0.01

        返回：
            bool: 是否相等（在容差范围内）
        """
        normalized_a = self.normalize(str(num_a)) if isinstance(num_a, str) else float(num_a)
        normalized_b = self.normalize(str(num_b)) if isinstance(num_b, str) else float(num_b)