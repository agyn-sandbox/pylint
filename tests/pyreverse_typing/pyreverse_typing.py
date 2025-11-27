from __future__ import annotations

from typing import Dict, List, Optional


class Team:
    title: str


class User:
    identifier: int
    metadata: Dict[str, int] = {}

    def __init__(self, username: str, tags: Optional[List[str]] = None) -> None:
        self.username: str = username
        self.tags: list[str] = list(tags or [])
        self.owner: Team | None = None
        self.alias: Optional[str] = None

    def add_tag(self, tag: str) -> List[str]:
        self.tags.append(tag)
        return self.tags

    @classmethod
    def from_payload(cls, payload: Dict[str, str]) -> User:
        return cls(payload["username"])
