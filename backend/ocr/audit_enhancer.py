"""
审计增强层

根据MVP手册4.2简化版置信度规则：
1. 来自OCR层（hidden_text）→ 置信度 *= 0.88
2. 内容包含手写特征（字体非标准）→ 强制 need_review: true
3. 印章类型 → 强制 need_review: true

confidence < 0.85 时自动设置 need_review: true
"""

from datetime import datetime
from typing import List, Dict, Any


class AuditEnhancer:
    """
    审计增强层

    给OpenDataLoader输出添加审计字段：
    - confidence: 置信度
    - need_review: 是否需要人工核验
    - review_reason: 核验原因
    """

    # 置信度阈值
    CONFIDENCE_THRESHOLD = 0.85

    # 非常规字体特征（简化判断）
    RARE_FONTS = {
        "handwriting", "script", "cursive", "calligraphic",
        "手写", "书写", "楷体", "行书"
    }

    def enhance(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        对OpenDataLoader原始输出进行审计增强

        参数：
            raw_result: OpenDataLoader原始JSON输出

        返回：
            添加了审计字段的增强结果
        """
        if not raw_result:
            return raw_result

        # 添加审计元数据
        raw_result["audit_metadata"] = {
            "processing_mode": "hybrid",
            "extraction_timestamp": datetime.now().isoformat(),
            "enhancer_version": "1.0.0"
        }

        # 处理 Docling 格式：texts/tables/pictures 在 document.json_content 顶层
        # raw_result 结构: {"status": "success", "document": {"json_content": {...}}}
        doc_content = raw_result.get("document", {}).get("json_content", raw_result)

        if "texts" in doc_content:
            for block in doc_content["texts"]:
                self._enhance_block(block)

        if "tables" in doc_content:
            for table in doc_content.get("tables", []):
                self._enhance_table(table)

        if "pictures" in doc_content:
            for image in doc_content.get("pictures", []):
                self._enhance_block(image)

        # 处理 pages dict（兼容旧格式或 group 内容）
        if "pages" in doc_content:
            pages_val = doc_content["pages"]
            if isinstance(pages_val, dict):
                for page in pages_val.values():
                    self._enhance_page(page)
            else:
                for page in pages_val:
                    self._enhance_page(page)

        # 质量检测
        raw_result["quality_flags"] = self._detect_quality_issues(raw_result)

        return raw_result

    def _enhance_page(self, page: Dict[str, Any]) -> None:
        """增强单个页面"""
        if "blocks" in page:
            for block in page["blocks"]:
                self._enhance_block(block)

        if "tables" in page:
            for table in page.get("tables", []):
                self._enhance_table(table)

        if "images" in page:
            for image in page.get("images", []):
                self._enhance_block(image)

    def _enhance_block(self, block: Dict[str, Any]) -> None:
        """增强单个block"""
        block_type = block.get("type", "").lower()

        # 计算基础置信度
        confidence = 1.0
        need_review = False
        review_reasons = []

        # 规则1: 来自OCR层（hidden_text字段存在表示经过OCR）
        if block.get("hidden_text"):
            confidence *= 0.88
            review_reasons.append("经过OCR识别")

        # 规则2: 非常规字体/手写特征
        font = block.get("font", "")
        if self._is_rare_font(font):
            confidence *= 0.90
            need_review = True
            review_reasons.append("非常规字体")

        # 规则3: 印章类型
        if block_type == "stamp" or block_type == "seal":
            need_review = True
            review_reasons.append("印章内容")

        # 规则4: 置信度低于阈值
        if confidence < self.CONFIDENCE_THRESHOLD:
            need_review = True
            if "OCR识别" not in "".join(review_reasons):
                review_reasons.append(f"置信度低于{self.CONFIDENCE_THRESHOLD}")

        # 添加审计字段
        block["confidence"] = round(confidence, 4)
        block["need_review"] = need_review
        block["review_reason"] = "; ".join(review_reasons) if review_reasons else None
        block["status"] = "pending_review" if need_review else "normal"

    def _enhance_table(self, table: Dict[str, Any]) -> None:
        """增强表格"""
        table["confidence"] = 0.95
        table["need_review"] = False
        table["review_reason"] = None
        table["status"] = "normal"

        for row in table.get("rows", []):
            for cell in row.get("cells", []):
                self._enhance_block(cell)

    def _is_rare_font(self, font_name: str) -> bool:
        """判断是否是非常规字体"""
        if not font_name:
            return False
        font_lower = font_name.lower()
        return any(rare in font_lower for rare in self.RARE_FONTS)

    def _detect_quality_issues(self, result: Dict[str, Any]) -> List[str]:
        """检测质量问题"""
        issues = []
        doc_content = result.get("document", {}).get("json_content", result)

        pages_val = doc_content.get("pages", {})
        if isinstance(pages_val, dict):
            total_pages = len(pages_val)
        else:
            total_pages = len(pages_val)
        if total_pages == 0:
            issues.append("警告：无页面数据")

        low_confidence_count = 0
        total_blocks = 0
        for block in doc_content.get("texts", []):
            total_blocks += 1
            if block.get("confidence", 1.0) < self.CONFIDENCE_THRESHOLD:
                low_confidence_count += 1
        for block in doc_content.get("pictures", []):
            total_blocks += 1
            if block.get("confidence", 1.0) < self.CONFIDENCE_THRESHOLD:
                low_confidence_count += 1

        if total_blocks > 0:
            low_conf_ratio = low_confidence_count / total_blocks
            if low_conf_ratio > 0.3:
                issues.append(f"警告：低置信度块占比 {low_conf_ratio:.1%}")

        return issues
