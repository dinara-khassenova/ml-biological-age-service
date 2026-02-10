FROM python:3.12-slim

WORKDIR /worker

COPY requirements.txt /worker/
RUN pip install --upgrade pip && pip install -r requirements.txt

ENV PYTHONPATH=/worker

CMD ["python", "main.py"]
