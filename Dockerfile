FROM python:3.12-slim

RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем папку для данных
RUN mkdir -p /app/data

# КОПИРУЕМ базу данных в контейнер
COPY data/fembo_colos.db /app/data/fembo_colos.db

# Делаем БД доступной для записи
RUN chmod 666 /app/data/fembo_colos.db

CMD ["python", "bot.py"]