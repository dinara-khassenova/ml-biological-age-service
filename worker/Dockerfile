FROM python:3.12-slim

WORKDIR /worker

COPY requirements.txt /worker/requirements.txt

RUN pip install --upgrade pip && pip install -r requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "main.py"]
