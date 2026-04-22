from celery import Celery

from core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, document_id: str, file_path: str):
    """
    处理文档的Celery异步任务

    流程：
    1. 更新文档状态为 PROCESSING
    2. 调用 OpenDataLoader 进行识别
    3. 审计增强（置信度、need_review标记）
    4. 存储识别结果（数据库 + 本地文件）
    5. 更新文档状态为 DONE
    """
    import os
    import base64
    import json
    from core.database import AsyncSessionLocal
    from services.document_service import DocumentService
    from ocr.wrapper import OpenDataLoaderWrapper
    from ocr.audit_enhancer import AuditEnhancer
    from models.document import RecognitionResult

    # 本地存储目录
    LOCAL_RESULT_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "ocr_res", document_id
    )

    def save_to_local(result_json: dict, output_dir: str):
        """
        将识别结果保存到本地目录
        目录结构：
        ocr_res/{document_id}/
        ├── result.json          # 识别结果
        └── images/              # 图片目录
            ├── imageFile89.png  # OpenDataLoader 提取的图片
            └── ...
        """
        os.makedirs(output_dir, exist_ok=True)
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        # 收集已复制的图片文件名（OpenDataLoader 输出 imageFileN.png）
        copied_images = {}
        if os.path.exists(images_dir):
            for fname in os.listdir(images_dir):
                name_part = os.path.splitext(fname)[0]
                # imageFileN.png 格式，提取 N 作为 kid id
                if name_part.startswith("imageFile") and name_part[9:].isdigit():
                    kid_id = int(name_part[9:])
                    copied_images[kid_id] = fname
                elif name_part.isdigit():
                    copied_images[int(name_part)] = fname

        # 1. 保存 result.json（深拷贝，避免修改原数据）
        result_copy = {k: v for k, v in result_json.items() if k != 'kids'}
        kids_saved = []

        for kid in result_json.get("kids", []):
            kid_copy = dict(kid)
            # 如果有内嵌图片（Base64），提取保存
            if kid.get("type") == "image" and kid.get("data"):
                img_data = kid["data"]
                img_format = kid.get("format", "png")
                kid_id = kid.get("id", len(kids_saved))
                img_filename = f"{kid_id}.{img_format}"
                img_path = os.path.join(images_dir, img_filename)

                try:
                    # 解析 Base64 数据
                    if img_data.startswith("data:"):
                        # data:image/png;base64,iVBOrw0KGgo...
                        header, b64_data = img_data.split(",", 1)
                        img_bytes = base64.b64decode(b64_data)
                    else:
                        img_bytes = base64.b64decode(img_data)

                    with open(img_path, "wb") as f:
                        f.write(img_bytes)

                    # 修改 kid 中的 data 为文件路径
                    kid_copy["data"] = None
                    kid_copy["source"] = f"images/{img_filename}"
                    kid_copy["local_path"] = img_path
                except Exception:
                    # 如果图片保存失败，保留原 data
                    pass
            elif kid.get("type") == "image":
                # 外部图片：已在 convert_with_images 时复制到 images_dir
                # 只有已有 source 的才修正路径；没有 source 的保持原样（不乱关联到错误图片）
                old_source = kid_copy.get("source", "")
                if old_source and "_images/" in old_source:
                    # old_source 形如 "Claude Code从入门到精通-v2.0.0_images/imageFile1.png"
                    # 需要改成 "images/imageFile1.png"
                    fname = old_source.split("_images/", 1)[-1]
                    kid_copy["source"] = f"images/{fname}"
                    kid_copy["local_path"] = os.path.join(images_dir, fname)

            kids_saved.append(kid_copy)

        result_copy["kids"] = kids_saved

        # 保存 JSON 文件
        json_path = os.path.join(output_dir, "result.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result_copy, f, ensure_ascii=False, indent=2)

        return json_path, images_dir, result_copy

    async def _process():
        from datetime import datetime

        async with AsyncSessionLocal() as db:
            service = DocumentService(db)

            # 1. 更新状态为处理中
            await service.update_document_status(document_id, "PROCESSING")

            try:
                wrapper = OpenDataLoaderWrapper()

                # 记录处理日志
                processing_start = datetime.now()

                # 调用 OpenDataLoader（同时复制图片到本地目录）
                raw_result = wrapper.convert_with_images(
                    file_path,
                    target_images_dir=os.path.join(LOCAL_RESULT_DIR, "images")
                )

                processing_end = datetime.now()

                if raw_result is None:
                    raise ValueError(
                        "OpenDataLoader 返回空结果，可能是文件损坏、格式不支持或 Hybrid Server 异常。"
                        f"文件路径：{file_path}"
                    )

                # 3. 审计增强
                enhancer = AuditEnhancer()
                enhanced_result = enhancer.enhance(raw_result)

                if enhanced_result is None:
                    raise ValueError("审计增强层返回空结果，原始识别结果可能为空。")

                # 4. 保存到本地目录
                json_path, images_dir, saved_result = save_to_local(enhanced_result, LOCAL_RESULT_DIR)

                # 保存处理日志（整个文件作为一块）
                page_logs = [{
                    "chunk": "1-all",
                    "processing_path": "hybrid",
                    "model": "docling-fast",
                    "start_time": processing_start.isoformat(),
                    "end_time": processing_end.isoformat(),
                    "duration_ms": int((processing_end - processing_start).total_seconds() * 1000),
                    "blocks_count": len(saved_result.get("kids", []))
                }]
                log_path = os.path.join(LOCAL_RESULT_DIR, "page_processing_log.json")
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(page_logs, f, ensure_ascii=False, indent=2)

                # 5. 存储识别结果到数据库
                result_record = RecognitionResult(
                    document_id=document_id,
                    result_json=saved_result,
                    storage_path=LOCAL_RESULT_DIR
                )
                db.add(result_record)

                # 6. 更新状态为完成
                total_pages_estimate = saved_result.get("number of pages", saved_result.get("total_pages", 0))
                await service.update_document_status(
                    document_id, "DONE",
                    total_pages=total_pages_estimate
                )

                return {
                    "status": "success",
                    "document_id": document_id,
                    "local_path": LOCAL_RESULT_DIR,
                    "json_path": json_path,
                    "log_path": log_path,
                    "images_count": len(os.listdir(images_dir)) if os.path.exists(images_dir) else 0
                }

            except Exception as e:
                await service.update_document_status(
                    document_id, "FAILED",
                    error_message=str(e)
                )
                raise

    # 执行异步任务
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_process())


@celery_app.task
def send_progress(task_id: str, current_page: int, total_pages: int, message: str = ""):
    """
    发送进度更新（WebSocket推送）
    """
    # 这里会通过Redis pub/sub推送到WebSocket
    # 简化实现，实际项目中需要集成WebSocket管理器
    pass
