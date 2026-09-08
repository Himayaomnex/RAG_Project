"""Budget management with real token counting using tiktoken."""

from dataclasses import dataclass, field
from typing import Dict
import tiktoken

# Default tokenizer for modern LLMs
_ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Measure exact token count for text using tiktoken cl100k_base."""
    if not text:
        return 0
    return len(_ENCODER.encode(str(text), disallowed_special=()))


@dataclass
class Budget:
    total: int = 40000
    reserved: Dict[str, int] = field(default_factory=dict)
    spent: int = 0

    @property
    def remaining(self) -> int:
        reserved_total = sum(self.reserved.values())
        return max(0, self.total - self.spent - reserved_total)

    def measure(self, text: str) -> int:
        """Measure token count for string content."""
        return count_tokens(text)

    def reserve(self, category: str, tokens: int) -> None:
        """Reserve token budget for a fixed section (e.g. system prompt, plan history)."""
        self.reserved[category] = tokens

    def can_fit(self, tokens: int) -> bool:
        """Check if incoming tokens fit within remaining budget."""
        return tokens <= self.remaining

    def admit(self, tokens: int) -> bool:
        """Spend tokens from budget if they fit. Returns True if admitted."""
        if self.can_fit(tokens):
            self.spent += tokens
            return True
        return False

    def render(self) -> str:
        """Render string summary for prompts."""
        return f"{self.remaining} tokens remaining out of {self.total} total (spent: {self.spent})"
