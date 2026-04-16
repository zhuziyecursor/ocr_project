from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime, timedelta

from models.user import User
from schemas.user import UserCreate, UserResponse, Token, TokenData
from core.config import settings

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """哈希密码"""
        return pwd_context.hash(password)

    async def register(self, user_data: UserCreate) -> UserResponse:
        """注册用户"""
        # 检查用户名是否存在
        result = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            return None

        # 创建新用户
        hashed_password = self.get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            hashed_password=hashed_password,
            email=user_data.email
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return UserResponse.model_validate(user)

    async def authenticate(self, username: str, password: str) -> UserResponse:
        """验证用户登录"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return UserResponse.model_validate(user)

    def create_access_token(self, data: dict, expires_delta: timedelta = None) -> str:
        """创建JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def get_current_user(self, token: str) -> UserResponse:
        """从token获取当前用户"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
        except JWTError:
            return None

        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if user:
            return UserResponse.model_validate(user)
        return None
