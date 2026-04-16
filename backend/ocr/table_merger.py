"""
跨页表格合并

根据技术方案手册2.3，利用OpenDataLoader提供的
previous_table_id和next_table_id字段实现跨页表格合并
"""

from typing import List, Dict, Any, Optional


class TableMerger:
    """
    跨页表格合并器

    检测并合并跨页表格，保留表头和单元格信息
    """

    def merge_cross_page_tables(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测并合并跨页表格

        参数：
            pages: OpenDataLoader输出的页面列表

        返回：
            合并后的表格列表
        """
        merged_tables = []
        processed_table_ids = set()

        for page in pages:
            for table in page.get("tables", []):
                table_id = table.get("id")

                if table_id in processed_table_ids:
                    continue

                if table.get("next_table_id"):
                    next_table = self._find_table_by_id(
                        pages, table.get("next_table_id")
                    )
                    if next_table:
                        merged = self._merge_tables(table, next_table)
                        merged_tables.append(merged)
                        processed_table_ids.add(table_id)
                        processed_table_ids.add(next_table.get("id"))
                    else:
                        merged_tables.append(table)
                        processed_table_ids.add(table_id)
                else:
                    merged_tables.append(table)
                    processed_table_ids.add(table_id)

        return merged_tables

    def _find_table_by_id(
        self, pages: List[Dict[str, Any]], table_id: str
    ) -> Optional[Dict[str, Any]]:
        """根据ID查找表格"""
        for page in pages:
            for table in page.get("tables", []):
                if table.get("id") == table_id:
                    return table
        return None

    def _merge_tables(
        self, table_a: Dict[str, Any], table_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并两个表格

        保留第一个表格的表头，合并数据行
        """
        header = table_a.get("rows", [{}])[0] if table_a.get("rows") else {}

        rows_a = table_a.get("rows", [])
        rows_b = table_b.get("rows", [])

        data_rows = rows_a[1:] if len(rows_a) > 1 else []
        data_rows_b = rows_b[1:] if len(rows_b) > 1 else []

        merged_rows = [header] if header else []
        for idx, row in enumerate(data_rows + data_rows_b):
            if isinstance(row, dict):
                row["row"] = idx + 1
                if "cells" in row:
                    for cell in row["cells"]:
                        if isinstance(cell, dict):
                            cell["row"] = idx + 1
            merged_rows.append(row)

        return {
            "id": table_a.get("id"),
            "rows": merged_rows,
            "bbox": self._calculate_merged_bbox(table_a, table_b),
            "page_range": [
                table_a.get("page", 1),
                table_b.get("page", 2)
            ],
            "confidence": min(
                table_a.get("confidence", 1.0),
                table_b.get("confidence", 1.0)
            ),
            "merged": True
        }

    def _calculate_merged_bbox(
        self, table_a: Dict[str, Any], table_b: Dict[str, Any]
    ) -> List[float]:
        """计算合并后的bbox"""
        bbox_a = table_a.get("bbox", [0, 0, 0, 0])
        bbox_b = table_b.get("bbox", [0, 0, 0, 0])

        return [
            min(bbox_a[0], bbox_b[0]),
            min(bbox_a[1], bbox_b[1]),
            max(bbox_a[2], bbox_b[2]),
            max(bbox_a[3], bbox_b[3]),
        ]
