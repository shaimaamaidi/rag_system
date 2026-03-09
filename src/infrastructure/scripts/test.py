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

    question = "ما هي أنواع الإجازات التي يستحقها الموظف الحكومي؟"
    question_embedding = container.embedding_provider.get_embedding_vector(question)
    chunks = container.vector_store.search(question, question_embedding)

    # Print de tous les chunks récupérés
    for idx, chunk in enumerate(chunks, start=1):
        print(f"----- Chunk {idx} ------")
        print(f"id: {chunk.id}")
        print(f"doc_name: {chunk.doc_name}")
        print(f"paragraph_id: {chunk.paragraph_id}")
        print(f"title: {chunk.title}")
        print(f"target_group: {chunk.target_group}")
        print(f"chunk_text: {chunk.chunk_text}...")
        print(f"has_table: {chunk.has_table}")
