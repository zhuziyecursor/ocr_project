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
    4. 存储识别结果
    5. 更新文档状态为 DONE
    """
    from core.database import AsyncSessionLocal
    from services.document_service import DocumentService
    from ocr.wrapper import OpenDataLoaderWrapper
    from ocr.audit_enhancer import AuditEnhancer
    from models.document import RecognitionResult
    import json

    async def _process():
        async with AsyncSessionLocal() as db:
            service = DocumentService(db)

            # 1. 更新状态为处理中
            await service.update_document_status(document_id, "PROCESSING")

            try:
                # 2. 调用 OpenDataLoader
                wrapper = OpenDataLoaderWrapper()
                raw_result = wrapper.convert(file_path)

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

                # 4. 存储识别结果
                result_record = RecognitionResult(
                    document_id=document_id,
                    result_json=enhanced_result,
                    storage_path=file_path.replace("/tmp/ocr_project/", "/data/recognition_results/")
                )
                db.add(result_record)

                # 5. 更新状态为完成
                await service.update_document_status(
                    document_id, "DONE",
                    total_pages=enhanced_result.get("total_pages", 0)
                )

                return {"status": "success", "document_id": document_id}

            except Exception as e:
                # 处理失败，更新状态
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
