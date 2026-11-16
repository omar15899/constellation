"""Canonical Google-style docstring templates for classes.

This file is a reference, not executable code. Copy the docstring shape and
adapt it to the actual class.
"""

from dataclasses import dataclass


class StandardClass:
    """One-sentence summary describing what the class is.

    Optional longer paragraph describing invariants, threading model,
    lifecycle, or major collaborators. Keep it terse — most callers
    only need the summary plus the attribute list.

    Attributes:
        public_attr: Description of the publicly readable attribute.
        threshold (float): Description, with explicit type for an
            attribute that has no annotation in ``__init__``.
    """

    def __init__(self, value: int) -> None:
        """Initialise the instance from ``value``.

        Args:
            value: Description of the constructor argument.

        Raises:
            ValueError: If ``value`` violates the class invariant.
        """
        if value < 0:
            raise ValueError("value must be non-negative")
        self.public_attr = value
        self.threshold = 1.0

    def public_method(self, x):
        """One-sentence summary of what the method does.

        Args:
            x: Description.

        Returns:
            Description.
        """
        return x + self.public_attr

    @property
    def derived(self) -> int:
        """Twice ``public_attr``."""
        return self.public_attr * 2


@dataclass
class StandardDataclass:
    """One-sentence summary describing what the data record represents.

    For dataclasses, list every public field under ``Attributes:``. The
    type comes from the field annotation; do not repeat it parenthetically.

    Attributes:
        x: Description of the first field.
        y: Description of the second field.
        label: Description of the third field.
    """

    x: float
    y: float
    label: str = ""


class StandardException(Exception):
    """One-sentence summary stating when this exception is raised."""


class _PrivateClass:
    """Internal helper.

    Single-underscore-prefixed classes are still worth a short summary —
    the next maintainer should not have to read the body to learn the
    purpose. Detail can be omitted; intent cannot.
    """
