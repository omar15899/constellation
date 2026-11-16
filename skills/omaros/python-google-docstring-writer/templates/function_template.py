"""Canonical Google-style docstring template for a plain function.

This file is a reference, not executable code. Copy the docstring shape and
adapt it to the actual signature and body. Section headings are listed in
their canonical order; omit any that do not apply.
"""


def function_name(arg: int, *, flag: bool = False) -> str:
    """One-sentence summary in imperative mood.

    Optional longer description. Use this paragraph for invariants, complexity
    properties, side-effect categories, or qualitative caveats that genuinely
    help a caller. Skip it when the summary line is sufficient.

    Args:
        arg: Description of the positional argument. Lowercase first letter,
            terminal period. Continuation lines indent four extra spaces.
        flag: Description of the keyword-only argument. State the default
            only when its value carries meaning the name does not convey.

    Returns:
        Description of the returned value. For tuples, name the components
        inline: ``(count, total)`` where ``count`` is the number of items
        and ``total`` is their sum.

    Raises:
        ValueError: If ``arg`` is negative.
        TypeError: If ``flag`` is not a bool.

    Note:
        Optional. Use for invariants, ambiguities, or non-obvious behaviour
        that does not fit into a numbered section.

    Example:
        >>> function_name(3)
        'three'
    """
    return str(arg)


def generator_name(source):
    """One-sentence summary describing what is yielded.

    Use ``Yields:`` (not ``Returns:``) when the body contains ``yield`` or
    ``yield from``.

    Args:
        source: Description of the input stream.

    Yields:
        Description of each yielded value, including any qualifications about
        ordering, duplicates, or termination.
    """
    for item in source:
        yield item


async def coroutine_name(client, url: str) -> dict:
    """One-sentence summary of the awaited result.

    For ``async def`` without ``yield``, use ``Returns:`` to describe the
    awaited value. There is no need to say "a coroutine that returns X" —
    the annotation already communicates the awaited type.

    Args:
        client: Description.
        url: Description.

    Returns:
        Description of the awaited value.

    Raises:
        TimeoutError: If the request does not complete within the client's
            configured deadline.
    """
    response = await client.get(url)
    return await response.json()
