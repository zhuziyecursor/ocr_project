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

        # 优先处理 OpenDataLoader 旧格式（kids 格式）
        if "kids" in raw_result:
            # 先拆分不合规的 kid
            raw_result["kids"] = self._split_kids(raw_result["kids"])
            for kid in raw_result["kids"]:
                self._enhance_kid(kid)
        else:
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

    def _enhance_kid(self, kid: Dict[str, Any]) -> None:
        """增强旧格式的单个 kid"""
        kid_type = kid.get("type", "").lower()

        # 计算基础置信度
        confidence = 1.0
        need_review = False
        review_reasons = []

        # 规则1: 来自OCR层（旧格式通过字体判断，null 表示可能是OCR）
        if kid.get("font") is None:
            confidence *= 0.88
            review_reasons.append("经过OCR识别")

        # 规则2: 非常规字体/手写特征
        font = kid.get("font", "")
        if self._is_rare_font(font):
            confidence *= 0.90
            need_review = True
            review_reasons.append("非常规字体")

        # 规则3: 印章类型
        if kid_type == "stamp" or kid_type == "seal":
            need_review = True
            review_reasons.append("印章内容")

        # 规则4: 置信度低于阈值
        if confidence < self.CONFIDENCE_THRESHOLD:
            need_review = True
            if "OCR识别" not in "".join(review_reasons):
                review_reasons.append(f"置信度低于{self.CONFIDENCE_THRESHOLD}")

        # 添加审计字段
        kid["confidence"] = round(confidence, 4)
        kid["need_review"] = need_review
        kid["review_reason"] = "; ".join(review_reasons) if review_reasons else None
        kid["status"] = "pending_review" if need_review else "normal"

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

    def _split_kids(self, kids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        拆分不合规的 kid

        规则：
        1. 如果 kid 包含换行符（\n），按换行拆分成多个 kid
        2. 如果 kid 的 formatting 数组中包含多个不同的字体大小，按字体大小拆分
        3. 注意：有空格的内容（如 "Claude Code"）不会被拆分
        """
        result = []

        for kid in kids:
            kid_type = kid.get("type", "").lower()
            # 只处理文本类型的 kid
            if kid_type not in ("paragraph", "heading", "text", "title", "section_header"):
                result.append(kid)
                continue

            content = kid.get("content", "") or kid.get("text", "") or ""

            # 情况1：content 中包含换行符，直接按换行拆分
            if "\n" in content:
                split_kids = self._split_by_newline(kid)
                result.extend(split_kids)
                continue

            # 情况2：检查 formatting 数组中是否有多个字体大小
            formatting = kid.get("formatting") or []
            if formatting and len(formatting) > 1:
                # 检查是否有不同的字体大小
                sizes = set()
                for fmt in formatting:
                    if fmt and fmt.get("size"):
                        sizes.add(fmt["size"])
                if len(sizes) > 1:
                    # 有多种字体大小，按字体大小拆分
                    split_kids = self._split_by_font_size(kid, formatting)
                    result.extend(split_kids)
                    continue

            # 默认：保留原 kid（不按高度估算拆分，因为不可靠）
            result.append(kid)

        return result

    def _split_by_newline(self, kid: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按换行符拆分 kid"""
        content = kid.get("content", "") or kid.get("text", "") or ""
        lines = content.split("\n")
        result = []

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            new_kid = dict(kid)
            new_kid["content"] = line
            new_kid["text"] = line
            # 调整 ID
            new_kid["id"] = f"{kid.get('id', 'kid')}_{i}"
            new_kid["_split_from"] = kid.get("id")
            new_kid["_split_index"] = i
            new_kid["_split_type"] = "newline"
            result.append(new_kid)

        return result

    def _split_by_font_size(self, kid: Dict[str, Any], formatting: List[Dict]) -> List[Dict[str, Any]]:
        """按字体大小拆分 kid"""
        result = []
        # 按字体大小分组内容
        current_size = None
        current_lines = []

        for fmt in formatting:
            size = fmt.get("size")
            text = fmt.get("text", "")

            if size != current_size:
                # 字体大小变了，保存之前的内容并开始新组
                if current_lines and current_size is not None:
                    new_kid = self._create_split_kid(kid, current_lines, current_size, "font_size")
                    result.append(new_kid)
                current_size = size
                current_lines = [text]
            else:
                current_lines.append(text)

        # 保存最后一组
        if current_lines and current_size is not None:
            new_kid = self._create_split_kid(kid, current_lines, current_size, "font_size")
            result.append(new_kid)

        return result if result else [kid]

    def _create_split_kid(self, kid: Dict, lines: List[str], font_size: float, split_type: str) -> Dict[str, Any]:
        """创建拆分后的 kid"""
        content = "".join(lines)
        new_kid = dict(kid)
        new_kid["content"] = content
        new_kid["text"] = content
        new_kid["font size"] = font_size
        new_kid["id"] = f"{kid.get('id', 'kid')}_s{font_size}"
        new_kid["_split_from"] = kid.get("id")
        new_kid["_split_type"] = split_type
        return new_kid

    def _is_rare_font(self, font_name: str) -> bool:
        """判断是否是非常规字体"""
        if not font_name:
            return False
        font_lower = font_name.lower()
        return any(rare in font_lower for rare in self.RARE_FONTS)

    def _detect_quality_issues(self, result: Dict[str, Any]) -> List[str]:
        """检测质量问题"""
        issues = []

        # 优先处理 OpenDataLoader 旧格式（kids 格式）
        if "kids" in result:
            total_pages = result.get("number of pages", 0)
            if total_pages == 0:
                issues.append("警告：无页面数据")

            low_confidence_count = 0
            total_blocks = 0
            for kid in result.get("kids", []):
                total_blocks += 1
                if kid.get("confidence", 1.0) < self.CONFIDENCE_THRESHOLD:
                    low_confidence_count += 1

            if total_blocks > 0:
                low_conf_ratio = low_confidence_count / total_blocks
                if low_conf_ratio > 0.3:
                    issues.append(f"警告：低置信度块占比 {low_conf_ratio:.1%}")
        else:
            # 处理 Docling 格式
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
