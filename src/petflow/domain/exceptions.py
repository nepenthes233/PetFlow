from __future__ import annotations


class PetFlowError(Exception):
    """Base error for the PetFlow domain."""


class GraphValidationError(PetFlowError):
    """Raised when graph structure or data violates domain rules."""


class DependencyCycleError(GraphValidationError):
    """Raised when a dependency edge would introduce a cycle."""


class RepositoryError(PetFlowError):
    """Raised when persistence or external storage fails."""

