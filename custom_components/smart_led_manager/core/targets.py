"""Authorization-first target resolution."""

from __future__ import annotations

from collections.abc import Iterable


class UnauthorizedTargetError(ValueError):
    """Raised when a request names an unmanaged physical light."""

    def __init__(self, targets: set[str]) -> None:
        self.targets = frozenset(targets)
        super().__init__(f"unmanaged targets: {', '.join(sorted(targets))}")


class TargetResolver:
    """Resolve explicit targets against the user's allow-list."""

    def __init__(self, authorized: Iterable[str]) -> None:
        self._authorized = frozenset(authorized)
        if not self._authorized:
            raise ValueError("at least one authorized target is required")

    @property
    def authorized(self) -> frozenset[str]:
        """Return the immutable allow-list."""
        return self._authorized

    def resolve(
        self, targets: Iterable[str] | None, *, all_managed: bool = False
    ) -> frozenset[str]:
        """Deduplicate explicit targets and reject anything outside the allow-list."""
        if all_managed:
            return self._authorized
        resolved = frozenset(targets or ())
        if not resolved:
            raise ValueError("at least one explicit target is required")
        if unauthorized := set(resolved).difference(self._authorized):
            raise UnauthorizedTargetError(unauthorized)
        return resolved
