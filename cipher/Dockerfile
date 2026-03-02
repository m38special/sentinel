FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir redis

COPY . .

CMD ["python3", "cipher_listener.py"]
