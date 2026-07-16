FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY . .

EXPOSE 8404

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8404"]
