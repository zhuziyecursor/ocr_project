from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.database import engine, Base, AsyncSessionLocal
from api.documents import router as documents_router
from api.auth import router as auth_router
from api.reviews import router as reviews_router
from api.ocr_files import router as ocr_files_router
from api.llm import router as llm_router


async def seed_default_admin():
    """启动时创建默认管理员账号（如果不存在）"""
    from models.user import User
    from services.auth_service import AuthService
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.DEFAULT_ADMIN_USER))
        existing = result.scalar_one_or_none()
        if not existing:
            hashed = AuthService(db).get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
            admin = User(
                username=settings.DEFAULT_ADMIN_USER,
                hashed_password=hashed,
                email="admin@example.com",
                is_active=True
            )
            db.add(admin)
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_default_admin()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(reviews_router, prefix=settings.API_PREFIX)
app.include_router(ocr_files_router, prefix=settings.API_PREFIX)
app.include_router(llm_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {"message": "审计文档处理系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
