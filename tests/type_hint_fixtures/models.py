"""Fixtures for pyreverse type hint tests."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


class User:
    identifier: int


class Repository:
    name: str


class Service:
    repo: Optional[Repository] = None
    registry: Dict[str, Repository] = {}

    def __init__(
        self,
        repo: Repository | None,
        *,
        cache: Dict[str, User],
    ) -> None:
        self.repo = repo
        self.owner: User
        self.cache: Dict[str, User] = cache
        self.maybe_user: Optional[User] = None
        self.ids: list[int] = []
        self.users: List["User"] = []
        self.members: Set[User] = set()
        self.pairs: Tuple[int, User]
        self.delegate: "Controller | None" = None
        self.alias: "User"


class Controller:
    def __init__(self, service: Service) -> None:
        self.service = service
        self.users: List[User] = []
