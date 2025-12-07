"""
memory_manager.py
Manages short-term and long-term memory for the AI Co-Partner.

Short-term: recent items kept in RAM.
Long-term: persisted to disk in a JSONL file in MEMORY_DIR.
"""

import os
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.paths import MEMORY_DIR
from core.logger.logger import get_logger

log = get_logger("memory_manager")


@dataclass
class MemoryItem:
    id: str
    timestamp: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryManager:
    def __init__(self, max_short_term: int = 100):
        self.max_short_term = max_short_term
        self.short_term: List[MemoryItem] = []
        self.long_term_file = os.path.join(MEMORY_DIR, "long_term.jsonl")

        os.makedirs(MEMORY_DIR, exist_ok=True)
        log.info("MemoryManager initializing...")
        self._load_long_term()
        log.info("MemoryManager ready.")

    # ---------- Internal helpers ----------

    def _load_long_term(self):
        """Load long-term memory from disk, but don't flood RAM."""
        if not os.path.exists(self.long_term_file):
            log.info("No existing long-term memory file found.")
            return

        try:
            with open(self.long_term_file, "r", encoding="utf-8") as f:
                # Just count lines for now; we don't need to keep them all in RAM.
                count = sum(1 for _ in f)
            log.info(f"Long-term memory file present with ~{count} items.")
        except Exception as e:
            log.error(f"Failed to inspect long-term memory file: {e}")

    def _append_long_term(self, item: MemoryItem):
        """Append a memory item to the long-term store on disk."""
        try:
            with open(self.long_term_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        except Exception as e:
            log.error(f"Failed to write long-term memory item: {e}")

    # ---------- Public API ----------

    def add_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> MemoryItem:
        """Create a new memory item and store it."""
        if metadata is None:
            metadata = {}

        item = MemoryItem(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            text=text,
            metadata=metadata,
        )

        # Short-term list
        self.short_term.append(item)
        if len(self.short_term) > self.max_short_term:
            self.short_term.pop(0)

        log.info(f"Added memory: {text[:80]!r}")

        if persist:
            self._append_long_term(item)

        return item

    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """Return the most recent short-term memories."""
        return self.short_term[-limit:]

    def search_long_term(self, keyword: str, limit: int = 20) -> List[MemoryItem]:
        """
        Simple keyword search over long-term memory.
        This is basic and will be upgraded later to embeddings.
        """
        results: List[MemoryItem] = []
        if not os.path.exists(self.long_term_file):
            return results

        try:
            with open(self.long_term_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if keyword.lower() in data.get("text", "").lower():
                            results.append(MemoryItem(**data))
                            if len(results) >= limit:
                                break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            log.error(f"Error searching long-term memory: {e}")

        return results


# Simple self-test when run directly
if __name__ == "__main__":
    mm = MemoryManager()
    mm.add_memory("This is a test memory from self-test.", {"source": "self_test"})
    recent = mm.get_recent(5)
    print("Recent memories:")
    for m in recent:
        print(f"- {m.timestamp} :: {m.text}")
