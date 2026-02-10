# Образ Python
FROM python:3.12.7
# Рабочая директория
WORKDIR /service
# Копирование requirements.txt
COPY requirement.txt .
# Установка зависимостей
RUN pip install --no-cache-dir -r requirement.txt
# Копируем ВСЮ папку app
COPY app ./app
# Говорим Python, что app — это import root
ENV PYTHONPATH=/service/app
# Запуск сервиса
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
