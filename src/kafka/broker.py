"""
Command to rebuild container:
cd src/kafka
docker-compose up -d
"""

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
        """Возвращает список всех существующих топиков"""
        request_topics = os.getenv("REQUEST_TOPIC", "service.requests").split(",")
        reply_topics = os.getenv("REPLY_TOPIC", "service.replies").split(",")
        send_event_topics = os.getenv("SEND_EVENT_TOPIC", "send_event").split(",")
        
        topics = []
        topics.extend(request_topics)
        topics.extend(reply_topics)
        topics.extend(send_event_topics)
        
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


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    manager = KafkaManager()
    manager.setup_topics()
