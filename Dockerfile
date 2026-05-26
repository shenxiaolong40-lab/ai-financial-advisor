FROM python:3.11-slim

WORKDIR /app

# 依赖层（先复制 requirements 利用缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# 非 root 用户运行
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 数据库目录
RUN mkdir -p /app/data

ENV DATABASE_URL=sqlite:////app/data/finance.db
ENV USER_MODE=single
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
