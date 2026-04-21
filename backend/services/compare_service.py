"""
跨文件比对服务

根据 CLAUDE.md 第六节：
- 文本相似度权重 0.7，位置相似度权重 0.3
- 匹配阈值 score > 0.75
- A/B 两份文档各自在自己坐标系中独立高亮，不做跨文档坐标换算
"""

import uuid
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import RecognitionResult


class CompareService:
    TEXT_WEIGHT = 0.7
    POS_WEIGHT = 0.3
    MATCH_THRESHOLD = 0.75

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_result(self, document_id: str) -> Optional[Dict]:
        result = await self.db.execute(
            select(RecognitionResult).where(RecognitionResult.document_id == document_id)
        )
        record = result.scalar_one_or_none()
        return record.result_json if record else None

    def _extract_blocks(self, result_json: Dict) -> List[Dict]:
        """从 result_json 中展平所有 block，附加 page 号

        支持两种格式：
        - kids 格式（OpenDataLoader 旧格式）：result_json["kids"] 为块列表
        - Docling 格式：result_json["pages"] 为页面列表，每页有 blocks
        """
        blocks = []

        # kids 格式（扁平结构，块直接带 page number）
        if "kids" in result_json:
            for kid in result_json["kids"]:
                blocks.append({
                    **kid,
                    "_page": kid.get("page number", kid.get("page", 1)),
                    "_source": "kids"
                })
        # Docling 格式（page → blocks 层级结构）
        elif "pages" in result_json:
            for page in result_json.get("pages", []):
                page_no = page.get("page_no", page.get("page", 0))
                for block in page.get("blocks", []):
                    blocks.append({**block, "_page": page_no, "_source": "docling"})
        # 兼容纯 texts 顶层结构（某些 Docling 变体）
        elif "texts" in result_json:
            for block in result_json["texts"]:
                page_no = block.get("prov", [{}])[0].get("page_no", 1) if block.get("prov") else 1
                blocks.append({**block, "_page": page_no, "_source": "docling"})
        return blocks

    def _text_similarity(self, a: str, b: str) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    def _position_similarity(self, bbox_a: List, bbox_b: List) -> float:
        """用 IoU 近似位置相似度，跨文档坐标系不同，仅做相对比较"""
        if not bbox_a or not bbox_b or len(bbox_a) < 4 or len(bbox_b) < 4:
            return 0.0
        # 归一化到 [0,1] 范围：用各自宽高做 bbox 中心归一化
        def center(bbox):
            return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

        cx_a, cy_a = center(bbox_a)
        cx_b, cy_b = center(bbox_b)
        # 用绝对距离的倒数（最大值1，越近越高）
        norm = max(cx_a, cx_b, cy_a, cy_b, 1)
        dist = ((cx_a / norm - cx_b / norm) ** 2 + (cy_a / norm - cy_b / norm) ** 2) ** 0.5
        return max(0.0, 1.0 - dist)

    def _score(self, block_a: Dict, block_b: Dict) -> float:
        text_a = block_a.get("content") or block_a.get("text") or ""
        text_b = block_b.get("content") or block_b.get("text") or ""
        t_sim = self._text_similarity(str(text_a), str(text_b))
        p_sim = self._position_similarity(
            block_a.get("bbox", []), block_b.get("bbox", [])
        )
        return self.TEXT_WEIGHT * t_sim + self.POS_WEIGHT * p_sim

    async def compare(self, doc_a_id: str, doc_b_id: str) -> List[Dict]:
        result_a = await self._get_result(doc_a_id)
        result_b = await self._get_result(doc_b_id)

        if result_a is None:
            raise ValueError(f"文档 {doc_a_id} 的识别结果不存在")
        if result_b is None:
            raise ValueError(f"文档 {doc_b_id} 的识别结果不存在")

        blocks_a = self._extract_blocks(result_a)
        blocks_b = self._extract_blocks(result_b)

        matched_b = set()
        diffs = []

        for block_a in blocks_a:
            best_score = 0.0
            best_b = None

            for i, block_b in enumerate(blocks_b):
                if i in matched_b:
                    continue
                s = self._score(block_a, block_b)
                if s > best_score:
                    best_score = s
                    best_b = (i, block_b)

            if best_b and best_score > self.MATCH_THRESHOLD:
                idx_b, block_b = best_b
                matched_b.add(idx_b)

                text_a = str(block_a.get("content") or block_a.get("text") or "")
                text_b = str(block_b.get("content") or block_b.get("text") or "")

                if text_a != text_b:
                    diffs.append({
                        "id": str(uuid.uuid4()),
                        "diff_type": "modified",
                        "block_id_a": block_a.get("id") or block_a.get("block_id"),
                        "block_id_b": block_b.get("id") or block_b.get("block_id"),
                        "bbox_a": block_a.get("bbox"),
                        "bbox_b": block_b.get("bbox"),
                        "page_a": block_a.get("_page"),
                        "page_b": block_b.get("_page"),
                        "original_content": text_a,
                        "modified_content": text_b,
                        "need_review": block_a.get("need_review", False) or block_b.get("need_review", False),
                    })
            else:
                # 在 B 中找不到匹配 → A 中的 block 被删除
                diffs.append({
                    "id": str(uuid.uuid4()),
                    "diff_type": "deleted",
                    "block_id_a": block_a.get("id") or block_a.get("block_id"),
                    "block_id_b": None,
                    "bbox_a": block_a.get("bbox"),
                    "bbox_b": None,
                    "page_a": block_a.get("_page"),
                    "page_b": None,
                    "original_content": str(block_a.get("content") or block_a.get("text") or ""),
                    "modified_content": None,
                    "need_review": block_a.get("need_review", False),
                })

        # B 中未匹配的 block → 新增
        for i, block_b in enumerate(blocks_b):
            if i not in matched_b:
                diffs.append({
                    "id": str(uuid.uuid4()),
                    "diff_type": "added",
                    "block_id_a": None,
                    "block_id_b": block_b.get("id") or block_b.get("block_id"),
                    "bbox_a": None,
                    "bbox_b": block_b.get("bbox"),
                    "page_a": None,
                    "page_b": block_b.get("_page"),
                    "original_content": None,
                    "modified_content": str(block_b.get("content") or block_b.get("text") or ""),
                    "need_review": block_b.get("need_review", False),
                })

        return diffs
