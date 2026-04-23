from abc import ABC, abstractmethod
from src.vector_db.domain.domain import RAGResults

class RepositoryDataBase(ABC):
    @abstractmethod
    def search_similar(self, embedding: list[float], limit: int = 3) -> RAGResults:
        pass
