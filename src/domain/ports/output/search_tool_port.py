from abc import ABC

class SearchToolPort(ABC):
    def __call__(self, question: str, enhancement_question: str) -> str:
        pass