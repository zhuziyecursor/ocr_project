"""
LLM 服务 - 调用豆包大模型进行 OCR 结果优化排版
"""
import httpx
from typing import Optional
from core.config import settings


class LLMService:
    """豆包大模型服务"""

    def __init__(self):
        self.api_base = "https://ark.cn-beijing.volces.com/api/coding"
        self.api_key = settings.LLM_API_KEY
        self.model = "doubao-seed-2-0-code-preview-260215"
        self.timeout = 120.0  # 2分钟超时

    def _build_prompt(self, ocr_text: str, page_info: str = "") -> list:
        """构建提示词"""
        system_prompt = """你是一个专业的文档排版优化助手。你的任务是对 OCR 识别的文档内容进行智能排版优化。

要求：
1. 识别文档的语义结构（标题、段落、表格、列表等）
2. 保持原文内容不变，只优化排版和格式
3. 对于表格内容，用 Markdown 表格格式呈现
4. 对于标题层级，使用合适的 Markdown 标题标记（# ## ###）
5. 对于列表内容，使用 - 或 1. 2. 3. 等 Markdown 列表格式
6. 保持原有的段落结构和换行
7. 如果有编号或项目符号，保留它们
8. 输出纯 Markdown 格式，不要有额外的解释文字

注意：
- 不要添加不存在的内容
- 不要删除原文中的任何实质性信息
- 保持专业术语的准确性
- 表格要有清晰的表头和边框

请直接输出优化后的 Markdown 内容，不要有"以下是优化结果"之类的前缀。"""

        user_prompt = f"{page_info}\n\n原始 OCR 内容：\n{ocr_text}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    async def optimize_layout(self, ocr_text: str, page_info: str = "") -> str:
        """
        调用大模型优化 OCR 内容的排版

        Args:
            ocr_text: OCR 识别的原始文本内容
            page_info: 页码信息（如 "第 4 页"）

        Returns:
            优化后的 Markdown 格式内容
        """
        if not ocr_text or not ocr_text.strip():
            return ""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": self._build_prompt(ocr_text, page_info),
            "temperature": 0.3,  # 低温度，保证输出稳定
            "max_tokens": 8192
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_base}/v3/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
            else:
                raise ValueError(f"API 返回格式异常: {data}")


# 全局单例
llm_service = LLMService()


async def optimize_ocr_layout(ocr_text: str, page_info: str = "") -> str:
    """快捷调用函数"""
    return await llm_service.optimize_layout(ocr_text, page_info)