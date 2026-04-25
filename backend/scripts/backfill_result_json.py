"""
一次性修复脚本：将数据库中 recognition_results.result_json 与本地 ocr_res/{doc_id}/result.json 同步。

背景：原流程将 enhanced_result（无 source 字段）存入 DB，而 result.json 是由
save_to_local 生成的 result_copy（含 source 字段）。本脚本把磁盘文件的内容同步回 DB。

用法：
    cd backend && python3 scripts/backfill_result_json.py
"""

import asyncio
import json
import os
import sys

# 确保 backend 在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.database import AsyncSessionLocal
from sqlalchemy import select, update
from models.document import RecognitionResult

OCR_RES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ocr_res"
)


async def backfill():
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(RecognitionResult))).scalars().all()
        print(f"找到 {len(rows)} 条 recognition_results 记录")

        updated = 0
        skipped = 0

        for row in rows:
            doc_id = row.document_id
            json_path = os.path.join(OCR_RES_DIR, doc_id, "result.json")

            if not os.path.exists(json_path):
                print(f"  [SKIP] {doc_id} — 无本地 result.json")
                skipped += 1
                continue

            with open(json_path, "r", encoding="utf-8") as f:
                disk_result = json.load(f)

            # 统计 source 字段覆盖情况（仅用于日志）
            disk_images = [k for k in disk_result.get("kids", []) if k.get("type") == "image"]
            disk_with_source = [k for k in disk_images if k.get("source")]

            await db.execute(
                update(RecognitionResult)
                .where(RecognitionResult.document_id == doc_id)
                .values(result_json=disk_result)
            )
            print(
                f"  [OK] {doc_id} — "
                f"images: {len(disk_images)}, with source: {len(disk_with_source)}"
            )
            updated += 1

        await db.commit()
        print(f"\n完成：更新 {updated} 条，跳过 {skipped} 条")


if __name__ == "__main__":
    asyncio.run(backfill())
