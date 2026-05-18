import os
import sys
from pathlib import Path

# Add the src/llm directory to sys.path so modules can be imported directly
llm_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(llm_dir))

# Mock environment variables to avoid reading the real .env file and causing side effects
os.environ["MODEL"] = "mock-model"
os.environ["EXA_API_KEY"] = "mock-exa-key"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
os.environ["REQUEST_TOPIC_RAG"] = "mock-request-topic"
os.environ["REPLY_TOPIC_RAG"] = "mock-reply-topic"
os.environ["EVENT_DB_TOPIC"] = "mock-event-topic"
os.environ["RAG_KAFKA_TIMEOUT_SEC"] = "5.0"
