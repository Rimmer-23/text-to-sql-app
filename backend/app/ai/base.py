"""Provider-agnostic interface for turning a question into SQL.

A provider only implements `complete` (one prompt in, raw text out); building the prompt and
cleaning up the answer are shared, so adding a provider is a few lines.
The returned SQL is still untrusted: callers must run it through `sql_guard`.
"""

import re
from abc import ABC, abstractmethod

from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.errors import AppError, ErrorCode
from app.services.schema_service import SchemaTable

# The prompt asks the model to start its answer with this when the data can't answer the
# question, so the user sees the reason instead of the result of a made-up query.
CANNOT_ANSWER_MARKER = "CANNOT_ANSWER"

_FENCED_BLOCK = re.compile(r"```[A-Za-z]*\s*(.*?)```", re.DOTALL)
_OPENING_FENCE = re.compile(r"^```[A-Za-z]*\s*")


class AIProvider(ABC):
    def generate_sql(self, schema: list[SchemaTable], question: str) -> str:
        raw = self.complete(SYSTEM_PROMPT, build_user_prompt(schema, question))
        return extract_sql(raw)

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send one prompt to the model and return its raw text answer.

        Must raise AppError(AI_ERROR) on any provider failure.
        """


def extract_sql(raw: str) -> str:
    """Strip markdown fences the model may add despite the prompt; surface CANNOT_ANSWER."""
    text = raw.strip()
    fenced = _FENCED_BLOCK.search(text)
    if fenced:
        text = fenced.group(1)
    else:  # an opening fence the model never closed
        text = _OPENING_FENCE.sub("", text).removesuffix("```")
    text = text.strip()

    if text.upper().startswith(CANNOT_ANSWER_MARKER):
        reason = text[len(CANNOT_ANSWER_MARKER) :].lstrip(" :-").strip()
        raise AppError(
            ErrorCode.AI_ERROR,
            reason or "The question can't be answered from the uploaded data",
            422,
        )
    if not text:
        raise AppError(ErrorCode.AI_ERROR, "AI returned an empty answer", 502)
    return text
