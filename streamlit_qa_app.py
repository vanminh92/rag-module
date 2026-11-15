"""K50 AI entrypoint. UI-only redesign; the RAG pipeline is unchanged."""

from ui.app import main


def generate_answer(question: str, chunks: list[dict]) -> tuple[str, list[dict]]:
    """Preserve the existing helper and its original generation behavior."""
    from src.answering import AnswerGenerator
    from src.entailment import get_entailment
    from src.llm import OllamaJSON
    from src.settings import RAGSettings

    settings = RAGSettings.from_env()
    checker = (lambda premise, hypothesis: get_entailment().check(premise, hypothesis)) if settings.support_check == "nli" else None
    result = AnswerGenerator(OllamaJSON(settings), entailment=checker).generate(question, chunks)
    return result.answer, result.sources


if __name__ == "__main__":
    main()
