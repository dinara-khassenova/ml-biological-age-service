from __future__ import annotations

import json
import os
from typing import Any, Dict

import pika


def publish_to_queue(payload: Dict[str, Any]) -> None:
    queue = os.getenv("RABBITMQ_QUEUE", "ml_tasks")

    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost = os.getenv("RABBITMQ_VHOST", "/")

    creds = pika.PlainCredentials(user, password)
    params = pika.ConnectionParameters(host=host, port=port, virtual_host=vhost, credentials=creds)

    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.queue_declare(queue=queue, durable=True)

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=body,
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
        ),
    )

    conn.close()