from abc import ABC, abstractmethod
from typing import Optional

class RepositoryDataBase(ABC):
    @abstractmethod
    def search_similar(self, embedding: list[float], limit: int = 3) -> list[dict]:
        pass
