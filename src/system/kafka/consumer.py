from kafka import KafkaConsumer
import json
import requests


TOPICS = [
    "ai_agent",
    "cloud_storage",
    "vector_db",
]

SERVERS_URL = {
    TOPICS[0]: "localhost:.../",
    TOPICS[1]: "localhost:.../",
    TOPICS[2]: "localhost:.../",
}

consumer = KafkaConsumer(
    ["ai_agent", ],
    bootstrap_servers=["localhost:9000"],
    group_id="group_consumer",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)


def consume(topic: str):
    responses = []
    for message in consumer:
        payload = message.value
        responses.append(requests.post(SERVERS_URL[topic] + topic, json=payload))
    return responses
