import sys
from src.domain.exceptions.app_exception import AppException
from src.infrastructure.di.container import Container

if __name__ == "__main__":
    try:
        container = Container()
    except AppException as e:
        print(f"Application error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

    question = "ما هي حقوق الموظف أثناء التحقيق التأديبي؟"
    enhancement="ما هي حقوق وضمانات الموظف أثناء التحقيق التأديبي؟ ما الذي لا يجوز فعله مع الموظف المحقق معه؟ محظورات التحقيق وحماية الموظف من الإكراه والضغط"
    question_embedding = container.answer_service.execute(question, enhancement)

