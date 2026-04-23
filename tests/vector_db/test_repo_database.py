"""Tests for RepositoryDataBase (ABC)."""
import pytest
from abc import ABC

from src.vector_db.adapters.repo_database import RepositoryDataBase
from src.vector_db.domain.domain import RAGResults


class TestRepositoryDataBase:
    """Tests for the abstract base class."""

    def test_cannot_instantiate_abc_directly(self):
        """Test that RepositoryDataBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RepositoryDataBase()

    def test_concrete_subclass_must_implement_search_similar(self):
        """Test that concrete subclass must implement search_similar."""

        class IncompleteRepo(RepositoryDataBase):
            pass

        with pytest.raises(TypeError):
            IncompleteRepo()

    def test_concrete_subclass_can_be_instantiated(self):
        """Test that a proper concrete subclass can be instantiated."""

        class ConcreteRepo(RepositoryDataBase):
            def search_similar(self, embedding: list[float], limit: int = 3) -> RAGResults:
                return RAGResults(data=None)

        repo = ConcreteRepo()
        assert isinstance(repo, RepositoryDataBase)
        result = repo.search_similar([0.1, 0.2], 3)
        assert result.data is None

    def test_search_similar_signature(self):
        """Test that search_similar has correct signature."""

        class ConcreteRepo(RepositoryDataBase):
            def search_similar(self, embedding: list[float], limit: int = 3) -> RAGResults:
                return RAGResults(data=None)

        repo = ConcreteRepo()
        # Test with default limit
        result = repo.search_similar([0.1])
        assert isinstance(result, RAGResults)

        # Test with custom limit
        result = repo.search_similar([0.1], limit=5)
        assert isinstance(result, RAGResults)
