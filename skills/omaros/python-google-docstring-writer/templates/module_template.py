"""One-sentence summary of the module's purpose.

Optional longer paragraph describing the major public objects and how they
relate to each other. Describe the public surface at the level of intent,
not at the level of every name. Avoid authorship metadata, change logs, and
long preambles — source control owns that information.

Attributes:
    DEFAULT_TIMEOUT: Seconds before the default HTTP client times out.
    LOGGER: Module-level logger; mutate via standard ``logging`` config.
"""

import logging

DEFAULT_TIMEOUT: int = 30
LOGGER = logging.getLogger(__name__)


def public_function(x: int) -> int:
    """One-sentence summary.

    Args:
        x: Description.

    Returns:
        Description.
    """
    return x + 1
