from abc import ABC, abstractmethod


class Extractor(ABC):
    @abstractmethod
    def extract(self) -> list[dict]:
        pass


class Transformer(ABC):
    @abstractmethod
    def transform(self, data: list[dict]) -> list:
        pass


class Loader(ABC):
    @abstractmethod
    def load(self, data: list) -> None:
        pass