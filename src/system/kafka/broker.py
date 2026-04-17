from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOPICS = [
    "user_db",
    "cloud_storage",
    "vector_db",
]

BROKER_HOSTS = [
    "localhost:9092",
]


class KafkaManager:
    def __init__(self, bootstrap_servers=["localhost:9092"]):
        self.admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    def setup_topics(self):
        """Создает все необходимые топики для работы системы"""
        new_topics = [
            NewTopic(name=topic, num_partitions=1, replication_factor=1)
            for topic in TOPICS
        ]
        
        try:
            self.admin.create_topics(new_topics=new_topics, validate_only=False)
            logger.info(f"Successfully created topics: {TOPICS}")
        except TopicAlreadyExistsError:
            logger.info("Topics already exist, skipping creation.")
        except Exception as e:
            logger.error(f"Failed to setup topics: {e}")
        finally:
            self.admin.close()
