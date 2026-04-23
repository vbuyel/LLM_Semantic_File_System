import sys

# Mock aiokafka and sentence_transformers before importing
_original_modules = {}
for _key in ["aiokafka", "aiokafka.AIOKafkaConsumer", "aiokafka.AIOKafkaProducer",
             "sentence_transformers", "sentence_transformers.SentenceTransformer"]:
    _original_modules[_key] = sys.modules.get(_key)

from unittest.mock import MagicMock as _MagicMock
_mock = _MagicMock()
_mock.AIOKafkaConsumer = _MagicMock()
_mock.AIOKafkaProducer = _MagicMock()
sys.modules["aiokafka"] = _mock
sys.modules["aiokafka.AIOKafkaConsumer"] = _mock.AIOKafkaConsumer
sys.modules["aiokafka.AIOKafkaProducer"] = _mock.AIOKafkaProducer
_mock2 = _MagicMock()
_mock2.SentenceTransformer = _MagicMock()
sys.modules["sentence_transformers"] = _mock2
sys.modules["sentence_transformers.SentenceTransformer"] = _mock2.SentenceTransformer

from src.llm.adapters.rag_search import RAGSearch
from src.llm.domain.domain import RAGResponse

# Restore
for _key, _val in _original_modules.items():
    if _val is None:
        if _key in sys.modules:
            del sys.modules[_key]
    else:
        sys.modules[_key] = _val

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
