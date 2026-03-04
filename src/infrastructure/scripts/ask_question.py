import sys

from src.application.use_cases.answer_question_pipeline import AskQuestionUseCase
from src.domain.exceptions.app_exception import AppException
from src.infrastructure.adapters.agent.agent_adapter import AzureAgentAdapter
from src.infrastructure.di.container import Container


def ask(ask_use_case: AzureAgentAdapter):
    questions = [
        "كنت مكلف/معار لجهة خارجية لمدة سبعة أشهر خلال دورة الأداء لهذا العام وباشرت العمل في إدارتي بالوزارة، فمن يعد تقويم أدائي خلال دورة الأداء لعام 2024؟",
        "تمت مباشرتي للعمل في الوزارة بعد انتهاء فترة الإيفاد الداخلي خلال هذا العام، ما هي الطريقة الصحيحة لتقويم أدائي خلال مرحلة تقييم الأداء لعام 2024؟",
        "تمت مباشرتي للعمل في الوزارة بعد انتهاء فترة الابتعاث خارج المملكة بداية هذا العام، ما هي الطريقة الصحيحة لتقويم أدائي خلال مرحلة تقييم الأداء لعام 2024؟",
        "ما عدد ساعات العمل الرسمية في رمضان؟",

    ]

    for i, q in enumerate(questions, 1):
        print("=" * 100)
        print(f"Question {i}: {q}")
        print("-" * 100)

        try:
            for chunk in ask_use_case.ask_question_stream(question=q):
                yield chunk
        except Exception as e:
            print(f"Error while processing question {i}: {e}")

        print("\n")



if __name__ == "__main__":
    try:
        container = Container()
    except AppException as e:
        sys.exit(1)
    except Exception as e:
        sys.exit(1)

    ask_use_case=container.agent_adapter
    for chunk in ask(ask_use_case):
        print(chunk, end="", flush=True)

