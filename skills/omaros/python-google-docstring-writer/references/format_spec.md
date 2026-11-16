# Google Docstring Format — Formal Specification

This document describes the syntactic structure of Google-style Python docstrings as consumed by `sphinx.ext.napoleon`, the canonical parser. Read this when the output must round-trip through documentation tooling without warnings.

## 1. Overall structure

```
"""<summary>

<longer description, optional>

<Section1:>
    <name>: <description>
    <name>: <description>

<Section2:>
    <description-block>

<Section3:>
    <name>: <description>
"""
```

Rules:

- Opening `"""` is followed immediately by the summary text, on the same line.
- The summary is a single sentence.
- A single blank line separates the summary from the longer description.
- A single blank line separates the longer description (if present) from the first section.
- A single blank line separates each section from the next.
- The closing `"""` is on its own line, indented to the construct's indentation.

For one-line docstrings:

```
"""Summary."""
```

The opening `"""`, the summary text, the closing `"""`, and nothing else, all on one line. No trailing blank line before the closing quotes.

## 2. Section names

Napoleon recognises exactly these section names (with trailing colon):

```
Args:
Arguments:           # alias for Args; prefer Args
Attention:
Attributes:
Caution:
Danger:
Error:
Example:
Examples:
Hint:
Important:
Keyword Args:
Keyword Arguments:   # alias for Keyword Args
Methods:
Note:
Notes:
Other Parameters:
Parameters:          # alias for Args; prefer Args
Return:              # alias for Returns; prefer Returns
Returns:
Raise:               # alias for Raises; prefer Raises
Raises:
References:
See Also:
Tip:
Todo:
Warning:
Warnings:            # alias for Warning; prefer Warning
Warns:
Yield:               # alias for Yields; prefer Yields
Yields:
```

This skill emits only the canonical forms: `Args:`, `Returns:`, `Yields:`, `Raises:`, `Attributes:`, `Note:`, `Example:`, `Examples:`, `Warning:`, `Todo:`, `Keyword Args:`. Do not emit aliases — they parse but reduce consistency across a codebase.

## 3. The `Args:` block

Each parameter is one entry. Two equivalent grammars are accepted:

**Without explicit type (preferred when the signature has annotations):**

```
Args:
    name: Description of the parameter.
    other: Description spanning
        multiple lines, each continuation
        indented four extra spaces.
```

**With explicit type (use only when the signature has no annotation and the type is unambiguous):**

```
Args:
    name (int): Description of the parameter.
    other (Optional[str]): Description.
```

Do not mix the two grammars within the same docstring.

Continuation lines indent four spaces beyond the parameter name. Blank lines inside the section terminate the section, so do not put blank lines between parameter entries.

## 4. The `Returns:` block

A single description block, not a list. Format:

```
Returns:
    Description of the returned value.
```

For tuples, name the components inline:

```
Returns:
    A tuple ``(count, total)`` where ``count`` is the number of items and
    ``total`` is their sum.
```

For dict-like returns, list keys explicitly:

```
Returns:
    A dict with keys:

        - ``status``: HTTP status code as ``int``.
        - ``body``: Response body as ``str``.
        - ``headers``: Response headers as ``Mapping[str, str]``.
```

Do not invent a `Returns:` block for functions that return `None` and exist for side effects. Document the side effect in the summary or in `Note:`.

## 5. The `Yields:` block

Identical structure to `Returns:`, used for generators.

```
Yields:
    Each non-empty line of the file, with trailing newline stripped.
```

A function with `yield` in its body uses `Yields:`. A function with `return value` and no `yield` uses `Returns:`. A function with both — i.e. `return value` inside a generator — yields the values and the return value becomes the `StopIteration.value`. In that case, document only `Yields:` and add a `Note:` describing the return value if it is non-trivial.

## 6. The `Raises:` block

Each entry: `ExceptionType: condition.`

```
Raises:
    ValueError: If ``n`` is negative.
    TypeError: If ``items`` is not iterable.
    FileNotFoundError: If ``path`` does not exist.
```

Order: most specific to most general, or order of appearance in the body. Whichever is more readable.

Include the exception's qualified name when ambiguity matters (e.g. `urllib.error.HTTPError` vs `requests.exceptions.HTTPError`). Otherwise the unqualified name is sufficient.

## 7. The `Attributes:` block

Used on classes and modules. Same structure as `Args:`.

```
Attributes:
    name: Description of the attribute.
    threshold (float): Description, with explicit type since no annotation.
```

For dataclasses, the type comes from the field annotation; do not repeat it.

## 8. The `Note:` block

A free-form prose block.

```
Note:
    The function is not thread-safe. Concurrent invocations may interleave
    reads and writes to the underlying cache.
```

Multi-paragraph notes use a blank line between paragraphs, with both paragraphs indented under the section header.

## 9. The `Example:` / `Examples:` block

Free-form prose, but doctest format is preferred:

```
Example:
    >>> chunked([1, 2, 3, 4, 5], 2)
    [[1, 2], [3, 4], [5]]
```

Multi-step examples:

```
Examples:
    Basic usage:

        >>> cache = LRUCache(maxsize=2)
        >>> cache.put("a", 1)
        >>> cache.get("a")
        1

    Eviction:

        >>> cache.put("b", 2)
        >>> cache.put("c", 3)  # evicts "a"
        >>> cache.get("a") is None
        True
```

The four-space indent of each example block is required for the rendered output to be a code block in Sphinx.

## 10. Inline formatting

- Double backticks for inline code: ``\`\`name\`\````. Single backticks are reserved for cross-references in reST and will be interpreted as such by Sphinx.
- Asterisks for emphasis: `*emphasis*` becomes italic. Double asterisks: `**strong**` becomes bold. Use sparingly.
- Bullet lists: lines starting with `- `, `+ `, or `* ` after a blank line.
- Numbered lists: lines starting with `1. `, `2. `, etc. after a blank line.
- Code blocks: indent four spaces beyond the surrounding text.

## 11. Cross-references (advanced)

When the docstring will be consumed by Sphinx and the codebase uses Sphinx cross-references:

- `:func:`module.func`` — link to a function.
- `:class:`module.Class`` — link to a class.
- `:meth:`module.Class.method`` — link to a method.
- `:attr:`module.Class.attribute`` — link to an attribute.
- `:exc:`module.ExceptionClass`` — link to an exception class.
- `:mod:`module`` — link to a module.

This skill does not emit cross-references by default — they tie the docstring to a specific documentation toolchain. Emit them only when the user explicitly asks.

## 12. Multi-line elements

Long descriptions wrap at ~88 columns and continue at the same indent level:

```
Args:
    request: An HTTP request object containing the headers, body, and
        connection metadata for the incoming call. The body is read
        eagerly and may be large.
```

Continuation lines indent four spaces beyond the parameter name (so eight spaces total for an `Args:` entry). For other sections (`Returns:`, `Yields:`, `Raises:`, `Note:`), continuation lines align with the start of the description on the previous line — typically four spaces in from the section header.

## 13. One-line docstrings

For trivial constructs (one-line lambdas, simple property getters, dunder methods with obvious semantics):

```python
@property
def name(self) -> str:
    """The display name of the user."""
    return self._name
```

A one-line docstring has no trailing blank line and no separate closing `"""` line. Use one-line docstrings only when:

- the construct is genuinely one-line semantically;
- no `Args:`, `Returns:`, `Raises:`, or `Note:` block is warranted;
- the summary line by itself fully specifies the contract.

Otherwise prefer the multi-line form.

## 14. Module docstrings

A module docstring sits at the top of the file, before any imports:

```python
"""One-sentence summary of the module's purpose.

Longer description, optional. Describe the major public objects and how
they relate to each other. Do not enumerate every name; describe the
public surface at the level of intent.

Attributes:
    DEFAULT_TIMEOUT: Seconds before the default HTTP client times out.
    LOGGER: Module-level logger; mutate via standard ``logging`` config.
"""
import os
import sys
...
```

The blank line between the closing `"""` and the first `import` is preserved. Do not insert anything between the docstring and the first import.

## 15. Class docstrings

A class docstring sits immediately after the `class ClassName:` line:

```python
class LRUCache:
    """A bounded least-recently-used cache.

    Eviction is performed lazily on insertion when ``len(cache) > maxsize``.
    The cache is not thread-safe.

    Attributes:
        maxsize: Maximum number of entries before eviction begins.
    """

    def __init__(self, maxsize: int) -> None:
        ...
```

Do not document class-level attributes inline (`maxsize: int = 0  #: max entries`). Use the `Attributes:` section in the class docstring instead — it is more discoverable.

For dataclasses, list every public field in `Attributes:`:

```python
@dataclass
class Point:
    """A point in two-dimensional space.

    Attributes:
        x: The horizontal coordinate.
        y: The vertical coordinate.
    """
    x: float
    y: float
```

## 16. Punctuation discipline

- Summary line ends with a period.
- Each `Args:` entry ends with a period.
- Each `Returns:` description ends with a period.
- Each `Raises:` entry ends with a period.
- Bullet list items end with a period if they are sentences; do not if they are noun phrases.

This is not pedantry — Sphinx and IDE consumers concatenate descriptions in tooltips, and missing terminal punctuation produces run-on prose.

## 17. Common Napoleon pitfalls

Things that look like Google style but break Napoleon:

- `Returns: foo` (description on the same line as the section header). Napoleon expects the description on the next line, indented.
- Mixing reST field markers (``:param x: ...``) with Google sections.
- Single backticks around code identifiers (Napoleon interprets them as Sphinx cross-references and emits warnings on missing targets).
- Section names with trailing whitespace before the colon: ``Args :`` does not parse.
- Section names that are not in the recognised list (``Inputs:``, ``Outputs:``).
- Indentation mismatches between section headers and their bodies.

## 18. Verifying the output

When the user has Sphinx available, the output can be verified by building docs:

```
sphinx-build -W -n -b html docs/ docs/_build/
```

The ``-W`` flag turns warnings into errors. Napoleon warnings about undefined references or malformed sections will surface here. This is the strictest and most reliable verification.

For lighter verification, ``pydocstyle --convention=google`` flags surface-level deviations. ``ruff check --select D --pydocstyle.convention=google`` does the same with faster execution.

This skill does not require either tool to run, but a consumer who relies on Sphinx output should run the strict build at least once after large docstring batches.
