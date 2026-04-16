# API module exports
from .documents import router as documents_router
from .auth import router as auth_router
from .reviews import router as reviews_router

__all__ = ["documents_router", "auth_router", "reviews_router"]
