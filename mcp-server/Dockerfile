FROM python:3.11-slim

WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ARL_HOST="" \
    ARL_TOKEN=""

# 安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝服务端代码
COPY server.py ./

# 使用 python 直接运行 MCP Server
ENTRYPOINT ["python", "server.py"]
