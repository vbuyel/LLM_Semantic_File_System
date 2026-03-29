import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from src.llm.agent_web_rag.adapters.rag_search import RAGSearch
from src.llm.agent_web_rag.domain.domain import (
    RAGRequest,
    RAGResponse,
    DataForExtraction,
)


class TestRAGSearch:
    @pytest.fixture
    def mock_env(self):
        with patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "test_key",
                "MODEL": "test_model",
                "MODEL_EMBED": "test_embed",
            },
        ):
            yield

    @patch("src.llm.agent_web_rag.adapters.rag_search.SentenceTransformer")
    @patch("src.llm.agent_web_rag.adapters.rag_search.UnstructuredLoader")
    @patch("src.llm.agent_web_rag.adapters.rag_search.OpenAI")
    def test_rag_search_initialization(
        self, mock_openai, mock_loader, mock_sentence, mock_env
    ):
        rag_search = RAGSearch()
        assert rag_search.model_embed is not None
        assert rag_search.num_top_results == 5

    @patch("src.llm.agent_web_rag.adapters.rag_search.UnstructuredLoader")
    @patch("src.llm.agent_web_rag.adapters.rag_search.CharacterTextSplitter")
    def test_extract_text_from_file(self, mock_splitter, mock_loader, mock_env):
        mock_doc = Mock()
        mock_doc.page_content = "Sample document content"

        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [mock_doc]
        mock_loader.return_value = mock_loader_instance

        mock_splitter_instance = Mock()
        mock_splitter_instance.split_text.return_value = ["chunk1", "chunk2"]
        mock_splitter.return_value = mock_splitter_instance

        with patch("src.llm.agent_web_rag.adapters.rag_search.SentenceTransformer"):
            with patch("src.llm.agent_web_rag.adapters.rag_search.OpenAI"):
                rag_search = RAGSearch()
                result = rag_search._extract_text_from_file("/path/to/file.pdf")

                assert isinstance(result, list)

    @patch("src.llm.agent_web_rag.adapters.rag_search.SentenceTransformer")
    @patch("src.llm.agent_web_rag.adapters.rag_search.faiss")
    def test_get_file_content_based_on_query_text(
        self, mock_faiss, mock_sentence_cls, mock_env
    ):
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]]).astype(np.float32)
        mock_sentence_cls.return_value = mock_model

        mock_index = Mock()
        mock_index.search.return_value = (None, [[0]])
        mock_faiss.IndexFlatL2.return_value = mock_index

        with patch("src.llm.agent_web_rag.adapters.rag_search.OpenAI"):
            rag_search = RAGSearch()
            query = DataForExtraction(
                text="test query", additional_data=["chunk1 content", "chunk2 content"]
            )
            result = rag_search._get_file_content_based_on_query_text(query)

            assert isinstance(result.text, str)

    def test_do_search_with_none_file_path(self):
        pass
