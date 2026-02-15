from abc import ABC, abstractmethod

class Storage(ABC):
    @abstractmethod
    def save(self, path: str, data: bytes):
        pass

    @abstractmethod
    def read(self, path: str) -> bytes:
        pass
