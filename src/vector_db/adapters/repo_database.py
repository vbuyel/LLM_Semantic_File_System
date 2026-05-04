from abc import ABC, abstractmethod
from src.vector_db.domain.domain import RAGResults, ObjectUploaded, UploadObject

class RepositoryDataBase(ABC):
    @abstractmethod
    def search_similar(self, embedding: list[float], limit: int = 3) -> RAGResults:
        pass

    @abstractmethod
    def upload_object(self, upload: UploadObject, embedding_model) -> ObjectUploaded:
        pass
