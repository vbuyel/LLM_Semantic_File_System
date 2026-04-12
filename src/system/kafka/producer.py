from kafka import KafkaProducer
import json
from fastapi import FastAPI
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.producer = KafkaProducer(
        bootstrap_servers=["localhost:9000"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    yield
    app.state.producer.flush()
    app.state.producer.close()


app = FastAPI(lifespan=lifespan)


# == User's request to Message Broker ==
@app.post("/produce/{topic}")
def sendto_broker_ai_agent(topic: str, message: dict):
    app.state.producer.send(topic, value=message)
