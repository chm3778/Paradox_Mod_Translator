import json
import os
from typing import Dict, Optional

class TranslationMemory:
    """Simple JSON-based translation memory."""

    def __init__(self, memory_path: str):
        self.memory_path = memory_path
        self.memory: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self.memory_path):
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    self.memory = json.load(f)
        except Exception:
            self.memory = {}

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, source_text: str, source_lang: str, target_lang: str) -> Optional[str]:
        return (
            self.memory
            .get(source_lang, {})
            .get(target_lang, {})
            .get(source_text)
        )

    def add(self, source_text: str, translated_text: str, source_lang: str, target_lang: str) -> None:
        self.memory.setdefault(source_lang, {}).setdefault(target_lang, {})[source_text] = translated_text
