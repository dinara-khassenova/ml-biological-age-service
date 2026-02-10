from __future__ import annotations

import json
import os
import sys
import time
import socket
from typing import Any, Dict

import pika
from sqlmodel import Session

from database.database import engine
from models.assessment import AssessmentResult
from models.enum import TaskStatus
from services.billing import BillingService
from services.crud import task as task_crud
from services.crud import ml_model as ml_model_crud
from ml.runtime_model import RuntimeMLModel


def _connect() -> pika.BlockingConnection:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost = os.getenv("RABBITMQ_VHOST", "/")

    creds = pika.PlainCredentials(user, password)
    params = pika.ConnectionParameters(host=host, port=port, virtual_host=vhost, credentials=creds)
    return pika.BlockingConnection(params)


def _validation_errors_to_dict(errors: list[Any]) -> list[dict]:
    out: list[dict] = []
    for e in errors:
        out.append({"field_name": getattr(e, "field_name", "unknown"), "message": getattr(e, "message", str(e))})
    return out


def main() -> None:
    worker_id = socket.gethostname()
    queue = os.getenv("RABBITMQ_QUEUE", "ml_tasks")
    prefetch = int(os.getenv("RABBITMQ_PREFETCH", "1"))

    while True:
        try:
            conn = _connect()
            ch = conn.channel()
            ch.queue_declare(queue=queue, durable=True)
            ch.basic_qos(prefetch_count=prefetch)

            print(f"[{worker_id}] started; queue={queue}; prefetch={prefetch}", flush=True)

            def on_message(channel: pika.channel.Channel, method, properties, body: bytes) -> None:
                external_id: str | None = None
                try:
                    payload: Dict[str, Any] = json.loads(body.decode("utf-8"))
                    external_id = str(payload["task_id"])

                    with Session(engine) as session:
                        billing = BillingService(session)

                        task = task_crud.get_task_by_external_id(external_id, session)
                        if task is None:
                            raise ValueError(f"Task not found in DB for task_id={external_id}")

                        # идемпотентность
                        if task.status in {TaskStatus.DONE, TaskStatus.FAILED}:
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                            return

                        meta = ml_model_crud.get_model_by_id(task.model_id, session)
                        if meta is None:
                            task.worker_id = worker_id
                            task.set_error("ML модель не найдена")
                            task_crud.update_task(task, session)
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                            return

                        runtime = RuntimeMLModel(meta=meta)

                        features = dict(task.answers or {})

                        # валидация
                        ok, errors_obj = runtime.validate(features)
                        errors = _validation_errors_to_dict(errors_obj)

                        if errors:
                            task.validation_errors = errors
                            task.worker_id = worker_id
                            task.set_error("Validation failed in worker")
                            task_crud.update_task(task, session)
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                            return

                        # баланс
                        price = int(meta.price_per_task)
                        if not billing.can_pay(task.user_id, price):
                            task.worker_id = worker_id
                            task.set_error("Недостаточно средств")
                            task_crud.update_task(task, session)
                            channel.basic_ack(delivery_tag=method.delivery_tag)
                            return

                        # processing
                        if task.status == TaskStatus.VALIDATED:
                            task.start_processing()
                        task.worker_id = worker_id
                        task_crud.update_task(task, session)

                        # predict
                        result: AssessmentResult = runtime.predict(features)

                        # списание строго после успеха
                        if task.charged_amount is None:
                            billing.charge_after_success(task.user_id, price, task.id)

                        # сохранить результат
                        task.set_result(result, charged_amount=price)
                        task.worker_id = worker_id
                        task_crud.update_task(task, session)

                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    print(f"[{worker_id}] ok task_id={external_id}", flush=True)

                except Exception as ex:
                    # 1) Не оставляем задачу в PROCESSING
                    if external_id:
                        try:
                            with Session(engine) as session:
                                task = task_crud.get_task_by_external_id(external_id, session)
                                if task and task.status not in {TaskStatus.DONE, TaskStatus.FAILED}:
                                    task.worker_id = worker_id
                                    task.set_error(str(ex))
                                    task_crud.update_task(task, session)
                        except Exception as ex2:
                            print(f"[{worker_id}] failed to mark task FAILED: {ex2}", file=sys.stderr, flush=True)

                    # 2) Сообщение из очереди — не перекидываем по кругу
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    print(f"[{worker_id}] failed: {ex}", file=sys.stderr, flush=True)

            ch.basic_consume(queue=queue, on_message_callback=on_message, auto_ack=False)
            ch.start_consuming()

        except Exception as ex:
            print(f"[{worker_id}] reconnecting after error: {ex}", file=sys.stderr, flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main()
