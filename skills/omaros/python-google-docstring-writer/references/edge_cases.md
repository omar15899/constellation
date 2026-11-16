# Edge-Case Catalogue

This document covers situations where the standard rules in `SKILL.md` need adjustment. Read it when the construct in front of you does not match the common shapes in `examples.md`.

Each entry states the situation, the rule, and the rationale. When two rules conflict, the more conservative one wins.

---

## In-place mutation

**Situation.** A function mutates one of its inputs.

**Rule.** State the mutation in the relevant `Args:` entry. If the mutation is non-obvious from the function name or signature, also add a `Note:` block.

**Examples.**

`heapq.heapify(heap)` mutates `heap` in place. Document `heap` as ``heap: List to convert into a heap, in place.``

`dict.update(other)` mutates the dict the method is called on. The implicit receiver is the mutated value; document the side effect in the summary: ``"""Update the dict with key-value pairs from ``other``."""``

A free function `normalize(arr)` that mutates `arr` and also returns it: state both. ``Args: arr: Array to normalise in place.`` ``Returns: The same ``arr`` object, normalised. Returned for chaining.``

A function `sorted_in_place(arr)` whose name *does* convey the mutation needs only the `Args:` note, no extra `Note:` block.

**Rationale.** Mutation is a contract; callers who pass shared mutable state must know. Hiding it behind absent documentation is how the race-condition bugs get written.

---

## Functions returning `None` for side effects

**Situation.** The function's `-> None` annotation (or absent return) means it exists for the side effect.

**Rule.** Omit `Returns:`. Describe the side effect in the summary, or in a longer description, or in `Note:`.

**Anti-pattern.** ``Returns: ``None``.`` This is noise; the annotation already states it.

**Edge case.** A function that conditionally returns `None` *or* a value (e.g. ``return None`` inside an early-exit branch, ``return value`` at the end) is not "returning `None` for side effects" — it returns an optional value. Document with ``Returns: The X if found, or ``None`` if not.``

---

## Optional returns (`X | None`)

**Situation.** Return type is `Optional[X]`, `X | None`, or the body has explicit `return None` paths.

**Rule.** State both possibilities in `Returns:`.

```
Returns:
    The matching record, or ``None`` if no match exists.
```

When the conditions for each branch are non-trivial, list them:

```
Returns:
    The cached value when ``key`` is present; ``None`` if ``key`` is
    absent or its entry has expired.
```

---

## Multiple-value returns

**Situation.** The function returns a tuple.

**Rule.** Describe each component. If the tuple is structured (e.g. `(min, max, count)`), name the components inline.

```
Returns:
    A tuple ``(min_value, max_value, count)`` where:

        - ``min_value``: The smallest element seen.
        - ``max_value``: The largest element seen.
        - ``count``: The number of elements processed.
```

For named tuples or dataclasses, prefer the named form: ``Returns: A ``Statistics(min, max, count)`` named tuple.``

---

## Generators that also `return`

**Situation.** A generator function uses `return value` somewhere in its body. The returned value becomes `StopIteration.value` and is accessible via `yield from` or by catching `StopIteration`.

**Rule.** Document `Yields:`. If the return value is non-trivial and load-bearing for callers, add a `Note:` describing it.

```
Yields:
    Each line of the file as a string.

Note:
    On exhaustion, the generator's ``StopIteration.value`` is the total
    number of bytes read. Callers using ``yield from`` capture this value
    as the result.
```

---

## Async functions that yield (async generators)

**Situation.** `async def` body contains `yield`.

**Rule.** Use `Yields:`, not `Returns:`. Treat as a generator.

```python
async def stream_chunks(source):
    """Yield decoded chunks from ``source`` as they become available.

    Args:
        source: An async iterable producing raw bytes.

    Yields:
        Each chunk as a UTF-8-decoded string.
    """
    async for chunk in source:
        yield chunk.decode("utf-8")
```

---

## `*args` and `**kwargs` — when to document

**Default rule.** Do not document them.

**Document them when:**
- The body iterates over `*args` and treats each element as a documented unit. Document under `Args:` as ``*args: Each positional argument is a regex pattern to apply.``
- The body retrieves specific keys from `**kwargs`. Document the keys, not the parameter as a whole. ``**kwargs: Configuration options. Recognised keys: ``timeout`` (seconds), ``retries`` (count), ``verify`` (bool).``
- The function is the public surface of a library and the user expects every parameter documented.

**Do not document them when:**
- They are pure forwarding (`super().__init__(*args, **kwargs)`, `func(*args, **kwargs)`).
- The wrapped callable is the source of truth.

**Example with explicit kwargs documentation:**

```
Args:
    request: The incoming HTTP request.
    **kwargs: Additional handler options.

        - ``timeout``: Seconds before the handler is aborted. Defaults to 30.
        - ``retries``: Number of retry attempts on failure. Defaults to 3.
```

---

## `self`, `cls`, and metaclass methods

**Rule.** Do not document `self`, `cls`, `mcs`, or any other implicit-receiver parameter, regardless of name. The `Args:` block starts at the first real parameter.

This applies to:
- Instance methods (`self`).
- Class methods (`cls`).
- Static methods (no implicit parameter, document all parameters).
- Metaclass methods (`mcs`, `cls`).

**Edge case.** Some codebases use unusual receiver names (`me`, `this`, `inst`). The convention follows position, not name: the first parameter of an instance method or class method is implicit and undocumented.

---

## Magic methods (dunders)

**Rule.** Document the operator semantics, not the dunder mechanics.

**Common patterns:**

- ``__init__``: Summary, `Args:`, `Raises:`. No `Returns:`.
- ``__new__``: Document only when overridden non-trivially (e.g. controlling instance creation, returning a different type). Otherwise leave undocumented.
- ``__str__`` / ``__repr__``: One-line summary describing the format.
- ``__eq__`` / ``__hash__``: One-line summary describing the equality / hash key.
- ``__lt__`` / ``__le__`` / ``__gt__`` / ``__ge__``: One-line summary describing the ordering key. ``"""Order by ``(priority, timestamp)``."""``
- ``__call__``: Document as if the instance were a function with that signature.
- ``__enter__`` / ``__exit__``: ``__enter__`` describes the bound resource; ``__exit__`` describes whether it suppresses exceptions.
- ``__iter__``: ``Yields:`` block describing the elements.
- ``__next__``: Same content as ``__iter__`` but per-call. Mention ``StopIteration`` only if termination is non-trivial.
- ``__getitem__`` / ``__setitem__`` / ``__delitem__``: Document as ``container[key]`` semantics.
- ``__getattr__`` / ``__setattr__`` / ``__getattribute__``: Document the attribute-access policy. These often warrant a `Note:` because they affect every attribute access.
- ``__add__`` / ``__sub__`` / etc.: Document the arithmetic semantics. State the operand types accepted.

**Anti-pattern.** Documenting ``__init__`` with phrases like "Constructor for the class". The Python community knows what `__init__` does; the docstring should describe what arguments mean and what state is established.

---

## Properties, setters, deleters

**Rule.** The property's docstring is the getter's docstring. Setter and deleter docstrings are optional and used only when their behaviour is non-obvious.

**Common pattern:**

```python
@property
def name(self) -> str:
    """The user's display name."""
    return self._name

@name.setter
def name(self, value: str) -> None:
    self._name = value.strip()
```

The setter is undocumented because its body is self-evident. If the setter validated, raised, or had side effects, document it:

```python
@name.setter
def name(self, value: str) -> None:
    """Set the display name, raising ``ValueError`` on empty input."""
    if not value:
        raise ValueError("name must not be empty")
    self._name = value
```

---

## Decorators that change the signature

**Situation.** A decorator wraps a function and changes the signature exposed to callers (e.g. adds a parameter, removes one, changes the return type).

**Rule.** Document the function as the *caller* sees it, accounting for the decorator. State the decorator's role in the longer description.

**Example.** A `@click.command` decorator turns a function into a CLI command. Callers interact with it via the command line, not by calling the function directly. The docstring describes the command's behaviour, options, and side effects, not the underlying Python signature.

**Example.** A `@functools.singledispatch` function exposes a `register` method on the wrapped object. Document the dispatch behaviour and how to register additional implementations.

---

## Dead code and stubs

**Situation.** The body is `pass`, `...`, `raise NotImplementedError`, or a sentinel returning a placeholder.

**Rule.** Write a short summary stating it is a stub, abstract method, or placeholder. Do not invent semantics.

```python
def fetch(self, key):
    """Fetch the value for ``key``.

    Subclasses must override this method.

    Raises:
        NotImplementedError: Always, in this base class.
    """
    raise NotImplementedError
```

For abstract base methods (`@abstractmethod`):

```python
@abstractmethod
def serialize(self) -> bytes:
    """Return the serialised representation of the instance."""
```

---

## Type hints disagree with the body

**Situation.** A parameter is annotated `int` but the body accepts any numeric (or vice versa); a return is annotated `str` but the body returns `bytes` in some path.

**Rule.** Document the body. Add a one-line `Note:` flagging the discrepancy.

```python
def to_text(value: str) -> str:
    """Return ``value`` as a UTF-8 string.

    Args:
        value: The value to convert. Despite the annotation, ``bytes``
            and ``bytearray`` are also accepted.

    Returns:
        ``value`` as a string.

    Note:
        The type annotation is narrower than the actual accepted set.
        This is a known discrepancy.
    """
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    return value
```

The discrepancy is surfaced. The skill does not silently update the type hint to match.

---

## Behaviour depends on globals or env vars

**Situation.** The function's behaviour switches on a module-level global, an environment variable, or a config object.

**Rule.** Mention the dependency and the variable name. Do not enumerate possible values unless the body switches on a small fixed set.

```python
def get_logger():
    """Return the module-level logger.

    Note:
        The log level is taken from the ``LOG_LEVEL`` environment
        variable on first access. Subsequent calls return the cached
        logger; changing the environment variable later has no effect.
    """
```

---

## Recursion

**Situation.** The function calls itself.

**Rule.** Document the contract from the caller's perspective. Do not describe the recursion mechanics unless they affect termination guarantees.

**Anti-pattern.** ``This function recursively descends into the tree, calling itself on each child …``. The caller does not care that it is implemented recursively.

**Pro-pattern.** ``Returns the leaves of ``tree`` in pre-order traversal.``

When the recursion has a non-trivial termination property (depth limit, accumulator), mention it:

```
Note:
    Recursion is bounded by the depth of ``tree``. Trees deeper than
    ``sys.getrecursionlimit()`` raise ``RecursionError``.
```

---

## Singleton, registry, or memoised function

**Situation.** The function caches its result, registers itself with a global registry, or is otherwise stateful across calls.

**Rule.** Mention the statefulness in the summary or longer description. Document the cache invalidation policy if relevant.

```python
@functools.lru_cache(maxsize=128)
def parse_template(text: str) -> Template:
    """Parse ``text`` into a ``Template`` AST.

    Memoised via ``functools.lru_cache`` (max 128 entries). Cache
    invalidation is purely LRU; there is no manual ``clear()`` exposed.
    """
```

---

## Functions that catch and re-raise

**Situation.** The function catches one exception type and re-raises another (translation pattern).

**Rule.** Document the *raised* exception, not the caught one. The translation is the contract.

```python
def fetch_record(key):
    """Return the record for ``key``.

    Args:
        key: Lookup key.

    Returns:
        The record.

    Raises:
        RecordNotFound: If no record exists for ``key``.
    """
    try:
        return self._db.get(key)
    except KeyError:
        raise RecordNotFound(key)
```

The caller sees `RecordNotFound`. They do not need to know about `KeyError`.

---

## Functions in a deeply private module

**Situation.** The module name starts with `_` (e.g. `_internal.py`) or the function is private (`_helper`).

**Rule.** Default to documenting anyway, more tersely. Single-name-prefixed (`_foo`) functions are common subjects of refactor and tests, and a one-line summary is cheap.

For double-underscore-prefixed (`__foo` — name-mangled) attributes, defer to user instruction. They are usually deliberately undocumented.

---

## Cython, generated, or vendored code

**Situation.** Files generated by Cython, protobuf, gRPC, ORM model generators, etc.

**Rule.** Skip. These files are owned by the generator; modifying them produces churn that is overwritten on the next regeneration.

Detect generated files by:
- A leading comment such as `# Generated by ...`, `# DO NOT EDIT`.
- Presence in a directory named `generated/`, `_pb2.py`, `_generated.py`, etc.
- A `pyproject.toml` `tool.X.generated` entry.

If unsure, ask the user before modifying.

---

## Type aliases, `TypeVar`, `Protocol`, `TypedDict`

**Situation.** The construct is not a class or function but a typing primitive.

**Rule.** Document them anyway. Treat as classes for the purpose of section structure.

```python
T = TypeVar("T", bound=Hashable)
"""Type variable for hashable values used as cache keys."""

class Cache(Protocol[T]):
    """Structural type for cache backends.

    Implementations must support ``get`` and ``set`` with hashable keys.

    Attributes:
        maxsize: Maximum number of entries.
    """

    maxsize: int

    def get(self, key: T) -> Any | None: ...
    def set(self, key: T, value: Any) -> None: ...
```

For `TypedDict`, list every key in `Attributes:`:

```python
class Config(TypedDict):
    """Application configuration as a typed dict.

    Attributes:
        host: Server host name.
        port: TCP port to bind to.
        debug: When ``True``, enables verbose logging.
    """
    host: str
    port: int
    debug: bool
```

---

## Tests and fixtures

**Situation.** Files under `tests/`, functions named `test_*`, classes named `Test*`, pytest fixtures.

**Rule.** Single-sentence summary for tests. For fixtures, also describe what is yielded and any cleanup.

```python
def test_chunked_handles_empty_input():
    """An empty input yields an empty list, regardless of chunk size."""
    assert chunked([], 3) == []

@pytest.fixture
def temp_db():
    """Yield a connection to a temporary on-disk SQLite database.

    The database file is created in a temporary directory and is removed
    after the test exits, regardless of pass/fail status.
    """
```

For parametrised tests, document the test name, not each parameter combination.

---

## Functions that the user has *not* asked to be documented

**Situation.** A file contains both functions in the user's request and other functions they did not mention.

**Rule.** Default to documenting only what the user asked for. If the file is "the module", document everything public. If the request was specific ("document `foo` and `bar`"), document only those.

When in doubt, ask. The cost of asking is one round-trip; the cost of unwanted churn is a rejected change.

---

## Multiple files with cross-references

**Situation.** Function `A` in `a.py` calls function `B` in `b.py`. Documenting `A` involves describing what `B` returns.

**Rule.** Read `B` before documenting `A`. Document `A` from the caller's contract — the return shape `B` produces is part of `A`'s contract only insofar as `A` exposes it.

Do not embed cross-references (`:func:` syntax) by default; they tie the docstring to a specific documentation toolchain. Mention the called function by name in prose: ``Returns the dict produced by ``b.normalise``.``

---

## Cython-style `.pyi` stub files

**Situation.** Type stubs for compiled extensions or for type-checker-only imports.

**Rule.** Document each stub as if it were the implementation. Stubs declare the interface to type checkers, IDEs, and humans; their docstrings serve the same role as the actual implementation's would.

For an `.pyi` file accompanying a `.py` file, prefer documenting on the `.py` file. The `.pyi` is then redundant for documentation purposes; leave it lean.

---

## Resilience to malformed input

**Final principle.** When the source is itself malformed (mixed indentation, partial syntax, an obvious typo), do not "fix" it while documenting. Document what the code as written does, and flag the malformation in the change report.

If the source is so malformed that its behaviour is genuinely ambiguous (unparseable, semantically incoherent), surface the issue to the user and stop. Do not paper over uncertainty with confident docstrings.
