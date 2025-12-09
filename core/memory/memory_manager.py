"""
memory_manager.py
Manages short-term and long-term memory
for the AI Co-Partner.

Short-term: recent items kept in RAM.
Long-term: persisted to disk in a JSONL
file in MEMORY_DIR.
"""

import os
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.paths import MEMORY_DIR
from core.logger import get_logger   # ← only change is here

log = get_logger("memory_manager")


# =============================================================
#   DATA STRUCTURES
# =============================================================

@dataclass
class MemoryItem:
    id: str
    timestamp: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================
#   MEMORY MANAGER
# =============================================================

class MemoryManager:
    """
    Handles:
      • Short-term memory in RAM
      • Long-term memory in /memory/storage/long_term.jsonl
    """

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.long_term_file = os.path.join(MEMORY_DIR, "long_term.jsonl")

        # in-RAM short term list
        self.short_term: List[MemoryItem] = []

        log.info("MemoryManager initialized.")

    # ---------------------------------------------------------
    #   BASE MEMORY WRITE
    # ---------------------------------------------------------

    def add_memory(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> MemoryItem:

        if metadata is None:
            metadata = {}

        item = MemoryItem(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            text=text,
            metadata=metadata,
        )

        # store in short-term RAM
        self.short_term.append(item)

        # optional long-term persistence
        if persist:
            try:
                with open(self.long_term_file, "a", encoding="utf8") as f:
                    f.write(json.dumps(asdict(item)) + "\n")
            except Exception as e:
                log.error(f"[MemoryManager] Failed writing long-term memory: {e}")

        return item

    # ---------------------------------------------------------
    #   COMPATIBILITY WRAPPER FOR AIEngine
    # ---------------------------------------------------------

    def store_message(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> MemoryItem:
        """
        The AIEngine calls this. It wraps add_memory()
        and attaches priority into metadata.
        """

        if metadata is None:
            metadata = {}

        metadata = dict(metadata)
        metadata.setdefault("priority", priority)

        return self.add_memory(
            text=message,
            metadata=metadata,
            persist=True,
        )

    # ---------------------------------------------------------
    #   READ FUNCTIONS
    # ---------------------------------------------------------

    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """Return newest short-term memories."""
        return self.short_term[-limit:]

    def search_long_term(self, keyword: str) -> List[MemoryItem]:
        """Very basic keyword search through stored long-term JSONL."""
        results: List[MemoryItem] = []

        if not os.path.exists(self.long_term_file):
            return results

        try:
            with open(self.long_term_file, "r", encoding="utf8") as f:
                for line in f:
                    data = json.loads(line)
                    if keyword.lower() in data["text"].lower():
                        results.append(MemoryItem(**data))
        except Exception as e:
            log.error(f"[MemoryManager] Long-term search error: {e}")

        return results
