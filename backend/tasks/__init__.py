# Tasks module exports
from .document_tasks import process_document_task, celery_app

__all__ = ["process_document_task", "celery_app"]
