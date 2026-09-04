import os

from ..config import settings
from ..prompts.grounded_answer import SYSTEM_PROMPT, build_user_prompt


class MissingAPIKeyError(RuntimeError):
    pass


class LLMProviderError(RuntimeError):
    pass


def generate_grounded_answer(question: str, context: str) -> str:
    """Generate an answer through the single configured LLM provider."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise MissingAPIKeyError("OPENAI_API_KEY is not configured.")

    try:
        from openai import OpenAI

        response = OpenAI(api_key=api_key).chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(question, context)},
            ],
        )
        answer = response.choices[0].message.content
    except Exception as error:
        raise LLMProviderError("The language model could not generate an answer.") from error

    if not answer or not answer.strip():
        raise LLMProviderError("The language model returned an empty answer.")
    return answer.strip()
