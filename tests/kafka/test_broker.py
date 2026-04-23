import os
import sys

# Mock kafka modules before importing
_original_modules = {}
for _key in ["kafka", "kafka.admin", "kafka.errors"]:
    _original_modules[_key] = sys.modules.get(_key)

from unittest.mock import MagicMock as _MagicMock

_mock_kafka = _MagicMock()
# Remove pytest_plugins to avoid pytest trying to use the mock as a plugin
if hasattr(_mock_kafka, 'pytest_plugins'):
    delattr(_mock_kafka, 'pytest_plugins')
_mock_kafka.admin = _MagicMock()
_mock_kafka.errors = _MagicMock()
_mock_kafka.errors.TopicAlreadyExistsError = type("TopicAlreadyExistsError", (Exception,), {})

sys.modules["kafka"] = _mock_kafka
sys.modules["kafka.admin"] = _mock_kafka.admin
sys.modules["kafka.errors"] = _mock_kafka.errors

from src.kafka.broker import KafkaManager

# Restore original modules
for _key, _val in _original_modules.items():
    if _val is None:
        if _key in sys.modules:
            del sys.modules[_key]
    else:
        sys.modules[_key] = _val

import pytest
from unittest.mock import patch, MagicMock


class TestKafkaManagerInit:
    @patch("src.kafka.broker.KafkaAdminClient")
    def test_init_default_broker_hosts(self, mock_admin_client):
        with patch.dict(os.environ, {}, clear=True):
            KafkaManager()
            mock_admin_client.assert_called_once_with(
                bootstrap_servers=["localhost:9092"]
            )

    @patch("src.kafka.broker.KafkaAdminClient")
    def test_init_custom_broker_hosts(self, mock_admin_client):
        with patch.dict(os.environ, {"BROKER_HOSTS": "kafka1:9092,kafka2:9092"}):
            KafkaManager()
            mock_admin_client.assert_called_once_with(
                bootstrap_servers=["kafka1:9092", "kafka2:9092"]
            )


class TestGetTopics:
    @patch("src.kafka.broker.os.getenv")
    def test_get_topics_only_topics_env(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "TOPICS": "topic1,topic2",
            "REQUEST_TOPIC": default,
            "REPLY_TOPIC": default,
        }.get(key, default)

        topics = KafkaManager._get_topics()
        assert "topic1" in topics
        assert "topic2" in topics
        assert "service.requests" in topics
        assert "service.replies" in topics

    @patch("src.kafka.broker.os.getenv")
    def test_get_topics_all_env_vars(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "TOPICS": "custom1,custom2",
            "REQUEST_TOPIC": "custom.request",
            "REPLY_TOPIC": "custom.reply"
        }.get(key, default)

        topics = KafkaManager._get_topics()
        assert topics == ["custom1", "custom2", "custom.request", "custom.reply"]

    @patch("src.kafka.broker.os.getenv")
    def test_get_topics_empty_topics(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "TOPICS": "",
            "REQUEST_TOPIC": default,
            "REPLY_TOPIC": default,
        }.get(key, default)

        topics = KafkaManager._get_topics()
        assert topics == ["service.requests", "service.replies"]

    @patch("src.kafka.broker.os.getenv")
    def test_get_topics_duplicate_topics(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "TOPICS": "topic1,topic2,topic1",
            "REQUEST_TOPIC": "topic2",
            "REPLY_TOPIC": "topic3"
        }.get(key, default)

        topics = KafkaManager._get_topics()
        assert topics == ["topic1", "topic2", "topic3"]

    @patch("src.kafka.broker.os.getenv")
    def test_get_topics_preserves_order(self, mock_getenv):
        mock_getenv.side_effect = lambda key, default=None: {
            "TOPICS": "zebra,apple,banana",
            "REQUEST_TOPIC": "apple",
            "REPLY_TOPIC": "zebra"
        }.get(key, default)

        topics = KafkaManager._get_topics()
        assert topics == ["zebra", "apple", "banana"]


class TestSetupTopics:
    @patch("src.kafka.broker.KafkaAdminClient")
    @patch("src.kafka.broker.NewTopic")
    @patch("src.kafka.broker.KafkaManager._get_topics")
    def test_setup_topics_success(self, mock_get_topics, mock_new_topic, mock_admin_client):
        mock_get_topics.return_value = ["topic1", "topic2"]
        mock_admin_instance = MagicMock()
        mock_admin_client.return_value = mock_admin_instance

        manager = KafkaManager()
        manager.setup_topics()

        mock_admin_client.assert_called_once()
        mock_admin_instance.create_topics.assert_called_once()
        mock_admin_instance.close.assert_called_once()

    @patch("src.kafka.broker.KafkaAdminClient")
    @patch("src.kafka.broker.NewTopic")
    @patch("src.kafka.broker.KafkaManager._get_topics")
    def test_setup_topics_topic_already_exists(self, mock_get_topics, mock_new_topic, mock_admin_client):
        # Use the mocked TopicAlreadyExistsError
        TopicAlreadyExistsError = type("TopicAlreadyExistsError", (Exception,), {})

        mock_get_topics.return_value = ["topic1"]
        mock_admin_instance = MagicMock()
        mock_admin_instance.create_topics.side_effect = TopicAlreadyExistsError()
        mock_admin_client.return_value = mock_admin_instance

        manager = KafkaManager()
        manager.setup_topics()

        mock_admin_instance.close.assert_called_once()

    @patch("src.kafka.broker.KafkaAdminClient")
    @patch("src.kafka.broker.NewTopic")
    @patch("src.kafka.broker.KafkaManager._get_topics")
    def test_setup_topics_generic_exception(self, mock_get_topics, mock_new_topic, mock_admin_client):
        mock_get_topics.return_value = ["topic1"]
        mock_admin_instance = MagicMock()
        mock_admin_instance.create_topics.side_effect = Exception("Something went wrong")
        mock_admin_client.return_value = mock_admin_instance

        manager = KafkaManager()
        manager.setup_topics()

        mock_admin_instance.close.assert_called_once()
