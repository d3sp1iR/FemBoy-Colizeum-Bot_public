FROM python:3.12-slim

RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Папка для базы — именно сюда будет монтироваться Volume
RUN mkdir -p /app/data

# Указываем хостингу где должен быть volume:
# В панели хостинга укажи путь /app/data
VOLUME ["/app/data"]

# Если нужен вебхук — оставим, не нужен — не мешает
EXPOSE 8080

CMD ["python", "bot.py"]
