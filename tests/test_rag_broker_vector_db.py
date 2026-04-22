import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock,PropertyMock
from datetime import datetime


mock_modules = {}

def setup_mocks():
    if 'sentence_transformers' not in sys.modules:
        mock_st = MagicMock()
        mock_modules['sentence_transformers'] = mock_st
        
    if 'aiokafka' not in sys.modules:
        mock_aiokafka = MagicMock()
        mock_modules['aiokafka'] = mock_aiokafka
        
    if 'psycopg' not in sys.modules:
        mock_psycopg = MagicMock()
        mock_modules['psycopg'] = mock_psycopg
        
    if 'kafka' not in sys.modules:
        mock_kafka = MagicMock()
        mock_kafka.admin = MagicMock()
        mock_kafka.errors = MagicMock()
        mock_modules['kafka'] = mock_kafka
    
    return mock_modules


setup_mocks()


@pytest.fixture(autouse=True)
def mock_all():
    mock_st = MagicMock()
    sys.modules['sentence_transformers'] = mock_st
    
    mock_aiokafka = MagicMock()
    sys.modules['aiokafka'] = mock_aiokafka
    
    mock_psycopg = MagicMock()
    mock_psycopg.rows = MagicMock()
    sys.modules['psycopg'] = mock_psycopg
    
    mock_pgvector = MagicMock()
    sys.modules['pgvector'] = mock_pgvector
    sys.modules['pgvector.psycopg'] = mock_pgvector
    
    mock_kafka = MagicMock()
    mock_kafka.admin = MagicMock()
    mock_kafka.errors = MagicMock()
    sys.modules['kafka'] = mock_kafka
    sys.modules['kafka.admin'] = mock_kafka.admin
    sys.modules['kafka.errors'] = mock_kafka.errors
    
    yield
    
    for key in list(sys.modules.keys()):
        if any(key.startswith(m) for m in ['sentence_transformers', 'aiokafka', 'psycopg', 'pgvector', 'kafka']):
            del sys.modules[key]


class TestRAGSearch:
    def test_rag_search_init(self):
        from src.llm.adapters.rag_search import RAGSearch
        
        rag = RAGSearch()
        
        assert rag._bootstrap_servers is not None
        assert rag._request_topic == "service.requests"
        assert rag._reply_topic == "service.replies"

    def test_do_search_returns_response_obj(self):
        from src.llm.adapters.rag_search import RAGSearch
        from src.llm.domain.domain import RAGResponse
        
        rag = RAGSearch()
        
        result = rag.do_search("test query")
        
        assert isinstance(result, RAGResponse)
        assert hasattr(result, 'text')


class TestVectorDBService:
    def test_domain_models(self):
        from src.system.vector_db.domain.domain import DocMetadata, RAGResults
        
        meta = DocMetadata(
            id=1,
            created_at=datetime.now(),
            file_name="test.txt",
            file_path="/test.txt",
            text_chunk="test content"
        )
        
        assert meta.id == 1
        assert meta.file_name == "test.txt"
        
        results = RAGResults(data=[meta])
        assert len(results.data) == 1


class TestBrokerConfig:
    def test_get_topics_from_env(self):
        with patch('os.getenv', side_effect=lambda k, d=None: {
            'TOPICS': 'topic1,topic2',
            'REQUEST_TOPIC': 'default_req',
            'REPLY_TOPIC': 'default_rep'
        }.get(k, d)):
            with patch('src.system.kafka.broker.KafkaAdminClient'):
                from src.system.kafka.broker import KafkaManager
                manager = KafkaManager()
                topics = manager._get_topics()

        assert 'topic1' in topics
        assert 'topic2' in topics

    def test_get_topics_default(self):
        with patch('os.getenv', side_effect=lambda k, d=None: {
            'TOPICS': '',
            'REQUEST_TOPIC': 'service.requests',
            'REPLY_TOPIC': 'service.replies'
        }.get(k, d)):
            with patch('src.system.kafka.broker.KafkaAdminClient'):
                from src.system.kafka.broker import KafkaManager
                manager = KafkaManager()
                topics = manager._get_topics()

        assert 'service.requests' in topics
        assert 'service.replies' in topics
        assert 'default_req' not in topics
        assert 'default_rep' not in topics

    def test_get_topics_no_duplicates(self):
        with patch('os.getenv', side_effect=lambda k, d=None: {
            'TOPICS': 'topic1,topic1,topic2,topic1',
            'REQUEST_TOPIC': 'service.requests',
            'REPLY_TOPIC': 'service.replies'
        }.get(k, d)):
            with patch('src.system.kafka.broker.KafkaAdminClient'):
                from src.system.kafka.broker import KafkaManager
                manager = KafkaManager()
                topics = manager._get_topics()

        assert topics.count('topic1') == 1


class TestRAGIntegration:
    def test_rag_search_uses_correct_topics(self):
        from src.llm.adapters.rag_search import RAGSearch
        import os
        
        rag = RAGSearch()
        
        assert rag._request_topic == os.getenv("REQUEST_TOPIC", "service.requests")
        assert rag._reply_topic == os.getenv("REPLY_TOPIC", "service.replies")
        assert rag._request_topic == "service.requests"
        assert rag._reply_topic == "service.replies"

    def test_rag_search_timeout_config(self):
        from src.llm.adapters.rag_search import RAGSearch
        import os
        
        rag = RAGSearch()
        
        assert rag._timeout_sec == float(os.getenv("RAG_KAFKA_TIMEOUT_SEC", "20"))
