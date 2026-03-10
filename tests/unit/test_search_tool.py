from src.infrastructure.adapters.tools.search_tool import RAGSearchTool


def test_search_tool_calls_use_case():
    class DummyUseCase:
        def __init__(self):
            self.called = None

        def execute(self, question, enhancement_question):
            self.called = (question, enhancement_question)
            return "answer"

    use_case = DummyUseCase()
    tool = RAGSearchTool(use_case)

    result = tool("hello", "enhanced")

    assert result == "answer"
    assert use_case.called == ("hello", "enhanced")
