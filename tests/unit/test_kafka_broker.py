"""
Unit tests for src.kafka.broker (KafkaManager).

NOTE: KafkaManager._get_topics() has a bug — it extends `topics` with
sub-lists instead of individual strings, so dict.fromkeys(topics) fails
with "unhashable type: 'list'". Tests document this existing behavior.
"""
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.unit


class TestKafkaManager:
    def test_get_topics_bug_unhashable(self, monkeypatch):
        """_get_topics uses topics.extend([list, list, list]) — a known bug."""
        monkeypatch.setenv("REQUEST_TOPIC", "req.topic")
        monkeypatch.setenv("REPLY_TOPIC", "rep.topic")
        monkeypatch.setenv("SEND_EVENT_TOPIC", "evt.topic")

        with patch("src.kafka.broker.KafkaAdminClient"):
            from src.kafka.broker import KafkaManager
            with pytest.raises(TypeError, match="unhashable type"):
                KafkaManager._get_topics()

    def test_setup_topics_fails_due_to_get_topics_bug(self, monkeypatch):
        """setup_topics also fails because it calls _get_topics internally."""
        monkeypatch.setenv("BROKER_HOSTS", "localhost:9092")
        with patch("src.kafka.broker.KafkaAdminClient") as MockAdmin:
            mock_admin = MagicMock()
            MockAdmin.return_value = mock_admin

            from src.kafka.broker import KafkaManager
            km = KafkaManager()
            # The TypeError propagates out of the list comprehension
            # before create_topics can be called
            with pytest.raises(TypeError):
                km.setup_topics()

    def test_init_creates_admin_client(self, monkeypatch):
        monkeypatch.setenv("BROKER_HOSTS", "localhost:9092")
        with patch("src.kafka.broker.KafkaAdminClient") as MockAdmin:
            mock_admin = MagicMock()
            MockAdmin.return_value = mock_admin

            from src.kafka.broker import KafkaManager
            km = KafkaManager()
            assert km.admin is mock_admin
            MockAdmin.assert_called_once()

    def test_topics_already_exist(self, monkeypatch):
        """If topics already exist, setup_topics should handle gracefully
        — but cannot reach that branch due to _get_topics bug."""
        monkeypatch.setenv("BROKER_HOSTS", "localhost:9092")
        from kafka.errors import TopicAlreadyExistsError
        with patch("src.kafka.broker.KafkaAdminClient") as MockAdmin:
            mock_admin = MagicMock()
            mock_admin.create_topics.side_effect = TopicAlreadyExistsError()
            MockAdmin.return_value = mock_admin

            from src.kafka.broker import KafkaManager
            km = KafkaManager()
            # Bug prevents reaching create_topics
            with pytest.raises(TypeError):
                km.setup_topics()
