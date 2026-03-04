from src.infrastructure.adapters.tools.search_tool import create_search_tool


def test_search_tool_calls_use_case():
    class DummyUseCase:
        def __init__(self):
            self.called = None

        def execute(self, question):
            self.called = question
            return "answer"

    use_case = DummyUseCase()
    tool = create_search_tool(use_case)

    result = tool("hello")

    assert result == "answer"
    assert use_case.called == "hello"
