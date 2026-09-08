"""Evidence store with token measurement, deduplication, and relevance-based assembly."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
from harness.budget import count_tokens


@dataclass
class EvidenceItem:
    id: str
    source: str  # "rag" | "kb" | "mcp"
    origin: Dict[str, Any]  # {date, speaker, page, file} or {table, row_id}
    content: str
    tokens: int = field(default=0)
    relevance: float = 1.0

    def __post_init__(self):
        if not self.tokens and self.content:
            self.tokens = count_tokens(self.content)


class EvidenceStore:
    def __init__(self):
        self._items: Dict[str, EvidenceItem] = {}

    def add(self, item: EvidenceItem) -> bool:
        """Add an evidence item with deduplication on id. Returns True if added."""
        if item.id in self._items:
            # If already present, keep the one with higher relevance
            if item.relevance > self._items[item.id].relevance:
                self._items[item.id] = item
            return False
        self._items[item.id] = item
        return True

    def get(self, item_id: str) -> EvidenceItem | None:
        return self._items.get(item_id)

    def all_items(self) -> List[EvidenceItem]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def assemble(self, budget_limit: int) -> Tuple[List[EvidenceItem], List[Dict[str, Any]]]:
        """Sort by relevance descending and admit until budget is exhausted.
        
        Returns:
            admitted: list of EvidenceItems
            dropped: list of dicts with id, relevance, tokens
        """
        # Sort items: highest relevance first, tie-break by fewer tokens
        sorted_items = sorted(
            self._items.values(),
            key=lambda x: (x.relevance, -x.tokens),
            reverse=True
        )

        admitted: List[EvidenceItem] = []
        dropped: List[Dict[str, Any]] = []
        current_spent = 0

        for item in sorted_items:
            if current_spent + item.tokens <= budget_limit:
                admitted.append(item)
                current_spent += item.tokens
            else:
                dropped.append({
                    "id": item.id,
                    "relevance": round(item.relevance, 4),
                    "tokens": item.tokens
                })

        return admitted, dropped

    def render_summary(self) -> str:
        """Render a concise summary of evidence held for the plan prompt."""
        if not self._items:
            return "No evidence gathered yet."
        lines = []
        for item in self._items.values():
            origin_str = ", ".join(f"{k}={v}" for k, v in item.origin.items() if v is not None)
            lines.append(f"[{item.id}] source={item.source} origin=({origin_str}) relevance={item.relevance:.2f} tokens={item.tokens}")
        return "\n".join(lines)

    def render_assembled(self, admitted: List[EvidenceItem]) -> str:
        """Render admitted evidence for the compose prompt."""
        if not admitted:
            return "No evidence assembled."
        blocks = []
        for item in admitted:
            origin_str = ", ".join(f"{k}={v}" for k, v in item.origin.items() if v is not None)
            blocks.append(
                f"[{item.id}] source={item.source} origin={{{origin_str}}} relevance={item.relevance:.2f}\n{item.content.strip()}"
            )
        return "\n\n".join(blocks)
