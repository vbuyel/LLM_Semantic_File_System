import os
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KafkaManager:
    def __init__(self):
        self.admin = KafkaAdminClient(
            bootstrap_servers=os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
        )

    @staticmethod
    def _get_topics() -> list[str]:
        topics = []
        topics_env = os.getenv("TOPICS", "")
        if topics_env.strip():
            topics.extend([topic.strip() for topic in topics_env.split(",") if topic.strip()])

        request_topic = os.getenv("REQUEST_TOPIC", "service.requests")
        reply_topic = os.getenv("REPLY_TOPIC", "service.replies")
        topics.extend([request_topic, reply_topic])

        # Preserve order and remove duplicates.
        return list(dict.fromkeys(topics))

    def setup_topics(self):
        """Создает все необходимые топики для работы системы"""
        new_topics = [
            NewTopic(name=topic, num_partitions=1, replication_factor=1)
            for topic in self._get_topics()
        ]

        try:
            self.admin.create_topics(new_topics=new_topics, validate_only=False)
            logger.info(f"Successfully created topics")
        except TopicAlreadyExistsError:
            logger.info("Topics already exist, skipping creation.")
        except Exception as e:
            logger.error(f"Failed to setup topics: {e}")
        finally:
            self.admin.close()
