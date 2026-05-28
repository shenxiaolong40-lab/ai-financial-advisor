from datetime import datetime, date as PyDate
from typing import Optional, List
from sqlalchemy import Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    single_user_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transactions: Mapped[List["Transaction"]] = relationship(back_populates="user")
    fire_profile: Mapped[Optional["FireProfile"]] = relationship(back_populates="user", uselist=False)
    ai_sessions: Mapped[List["AISession"]] = relationship(back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, default="💰")

    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("sync_source", "sync_id", name="uq_sync"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # income | expense
    date: Mapped[PyDate] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    merchant: Mapped[str] = mapped_column(String, default="")
    sync_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sync_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")


class FireProfile(Base):
    """用户的 FIRE 配置：收入、分类资产、预期收益率"""
    __tablename__ = "fire_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    monthly_income: Mapped[float] = mapped_column(Float, default=0.0)
    # 分类资产
    cash_assets: Mapped[float] = mapped_column(Float, default=0.0)          # 现金/货币基金
    stock_assets: Mapped[float] = mapped_column(Float, default=0.0)         # 股票/基金
    real_estate_assets: Mapped[float] = mapped_column(Float, default=0.0)   # 房产市值
    other_assets: Mapped[float] = mapped_column(Float, default=0.0)         # 其他（债券/黄金等）
    # FIRE 参数
    expected_return: Mapped[float] = mapped_column(Float, default=0.07)     # 年化收益率
    fire_multiplier: Mapped[float] = mapped_column(Float, default=25.0)     # 倍数（4%法则=25）
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="fire_profile")


class AISession(Base):
    __tablename__ = "ai_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="ai_sessions")
