"""
Markdown 导出服务

根据 CLAUDE.md 第八节：
- 导出的 Markdown 文件包含核验记录
- 若含未核验内容，文件头部必须标注警告
"""

from datetime import datetime
from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document, RecognitionResult
from models.review_record import ReviewRecord


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_markdown(self, document_id: str) -> Tuple[str, str]:
        """
        导出文档识别结果为 Markdown

        返回：(markdown_content, filename)
        """
        # 查文档
        doc_result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise ValueError(f"文档 {document_id} 不存在")

        # 查识别结果
        result_query = await self.db.execute(
            select(RecognitionResult).where(RecognitionResult.document_id == document_id)
        )
        rec = result_query.scalar_one_or_none()
        if not rec:
            raise ValueError(f"文档 {document_id} 的识别结果不存在")

        result_json = rec.result_json

        # 查已核验的 block_id 集合
        review_query = await self.db.execute(
            select(ReviewRecord).where(ReviewRecord.document_id == document_id)
        )
        review_records = review_query.scalars().all()
        reviewed_block_ids = {r.block_id for r in review_records if r.block_id}

        # 收集所有 need_review=True 的 block
        unreviewed_blocks = []
        pages = result_json.get("pages", [])
        for page in pages:
            for block in page.get("blocks", []):
                if block.get("need_review") and block.get("id") not in reviewed_block_ids:
                    unreviewed_blocks.append(block)

        lines = []

        # 文件头
        lines.append(f"# {document.file_name}")
        lines.append(f"\n> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 文档状态：{document.status}")
        lines.append(f"> 总页数：{document.total_pages or len(pages)}")

        # 未核验警告
        if unreviewed_blocks:
            lines.append("\n---")
            lines.append("\n> ⚠️ **警告：本文档含有未核验内容**")
            lines.append(f"> 共 {len(unreviewed_blocks)} 处内容尚未经过人工核验，请核验后再使用本导出文件。")
            lines.append("\n---")

        # 已核验记录汇总
        if review_records:
            lines.append("\n## 核验记录")
            for r in review_records:
                lines.append(f"\n- **Block {r.block_id}**（第 {r.page_no} 页）")
                if r.original_content:
                    lines.append(f"  - 原始内容：{r.original_content}")
                if r.modified_content:
                    lines.append(f"  - 修改为：{r.modified_content}")
                lines.append(f"  - 核验人：{r.reviewed_by or '未知'}  时间：{r.reviewed_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # 正文内容（按页）
        lines.append("\n## 识别内容")
        for page in pages:
            page_no = page.get("page_no", page.get("page", "?"))
            lines.append(f"\n### 第 {page_no} 页")

            for block in page.get("blocks", []):
                block_type = block.get("type", "text")
                content = block.get("content") or block.get("text") or ""
                need_review = block.get("need_review", False)
                is_reviewed = block.get("id") in reviewed_block_ids

                if block_type in ("table",):
                    lines.append(self._render_table(block))
                elif block_type in ("image", "chart"):
                    desc = block.get("description") or "[图片/图表]"
                    lines.append(f"\n![{desc}]({block.get('image_url', '')})")
                    lines.append(f"\n> {desc}")
                else:
                    if need_review and not is_reviewed:
                        lines.append(f"\n> 🔵 **[待核验]** {content}")
                    elif need_review and is_reviewed:
                        lines.append(f"\n{content} *(已核验)*")
                    else:
                        lines.append(f"\n{content}")

        markdown = "\n".join(lines)
        safe_name = document.file_name.rsplit(".", 1)[0]
        filename = f"{safe_name}_识别结果.md"
        return markdown, filename

    def _render_table(self, block: dict) -> str:
        """把 table block 渲染为 Markdown 表格"""
        rows = block.get("rows", [])
        if not rows:
            return "\n[空表格]"

        lines = []
        for i, row in enumerate(rows):
            cells = row.get("cells", [])
            cell_texts = [str(c.get("content") or c.get("text") or "") for c in cells]
            lines.append("| " + " | ".join(cell_texts) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * len(cell_texts)) + " |")

        return "\n" + "\n".join(lines)
