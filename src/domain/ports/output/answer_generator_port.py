from abc import ABC, abstractmethod

class AnswerGeneratorPort(ABC):
    @abstractmethod
    def generate_answer(self, context: str, question: str) -> str:
        pass