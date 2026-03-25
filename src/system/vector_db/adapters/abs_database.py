from abc import ABC, abstractmethod
from typing import Optional

class AbstractDataBase(ABC):
    @abstractmethod
    def setup_vector_db(self, recreate: bool = False) -> None:
        pass

    @abstractmethod
    def insert_embedding(self, embedding: list[float], metadata: Optional[dict] = None) -> int:
        pass

    @abstractmethod
    def search_similar(self, embedding: list[float], limit: int = 3) -> list[dict]:
        pass

    @abstractmethod
    def delete_by_id(self, doc_id: int) -> bool:
        pass
