FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --upgrade pip && pip install -r /app/requirements.txt

EXPOSE 8080

ENV PYTHONPATH=/app

# Копирование исходников можно не делать, т.к. будет volume в compose.
# COPY ./ /app

CMD ["python", "main.py"]
