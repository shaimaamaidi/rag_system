# src/application/ports/search_tool_port.py
from abc import ABC

class SearchToolPort(ABC):
    def __call__(self, question: str) -> str:
        pass