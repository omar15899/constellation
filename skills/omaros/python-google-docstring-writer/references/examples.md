# Before / After Catalogue

Twelve worked examples covering the common shapes encountered in real Python code. Each example shows the *before* (input as the user might supply it) and the *after* (the expected output). Code outside docstring slots is byte-identical between the two.

The headings indicate which case is being illustrated. Refer to a heading when the construct in front of you matches it.

---

## 1. Plain function with type hints

**Before:**

```python
def clamp(value: float, low: float, high: float) -> float:
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(high, value))
```

**After:**

```python
def clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` to the closed interval ``[low, high]``.

    Args:
        value: The value to clamp.
        low: Lower bound of the interval, inclusive.
        high: Upper bound of the interval, inclusive.

    Returns:
        ``value`` when ``low <= value <= high``; otherwise ``low`` or ``high``,
        whichever is closer.

    Raises:
        ValueError: If ``low > high``.
    """
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(high, value))
```

---

## 2. Function without type hints

When type hints are absent, state types only when they are unambiguous from the body.

**Before:**

```python
def reservoir_sample(stream, k):
    import random
    reservoir = []
    for i, item in enumerate(stream):
        if i < k:
            reservoir.append(item)
        else:
            j = random.randint(0, i)
            if j < k:
                reservoir[j] = item
    return reservoir
```

**After:**

```python
def reservoir_sample(stream, k):
    """Return ``k`` items sampled uniformly at random from ``stream``.

    Implements Algorithm R: a single pass over ``stream`` is sufficient,
    and the size of ``stream`` need not be known in advance. If ``stream``
    contains fewer than ``k`` items, all items are returned.

    Args:
        stream: An iterable of items to sample from. Consumed exhaustively.
        k (int): Desired sample size. Must be non-negative.

    Returns:
        A list of up to ``k`` items in arbitrary order.
    """
    import random
    reservoir = []
    for i, item in enumerate(stream):
        if i < k:
            reservoir.append(item)
        else:
            j = random.randint(0, i)
            if j < k:
                reservoir[j] = item
    return reservoir
```

Note that ``stream``'s type is left unstated — it could be any iterable, and the code does not constrain it further. ``k`` is annotated as ``int`` parenthetically because the body treats it as a count.

---

## 3. Generator (uses `yield`)

`Yields:` replaces `Returns:`.

**Before:**

```python
def lines_with_prefix(path, prefix):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                yield line.rstrip("\n")
```

**After:**

```python
def lines_with_prefix(path, prefix):
    """Yield the lines of the file at ``path`` that begin with ``prefix``.

    The file is opened with UTF-8 encoding. Trailing newline characters
    are stripped before yielding.

    Args:
        path: Filesystem path to the file to read.
        prefix: String prefix that selects which lines to yield.

    Yields:
        Each matching line as a string, with trailing ``\\n`` removed.

    Raises:
        FileNotFoundError: If no file exists at ``path``.
        UnicodeDecodeError: If the file contains bytes that are not valid
            UTF-8.
    """
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                yield line.rstrip("\n")
```

---

## 4. Async function

`async def` without `yield` returns a coroutine; document the awaited value as `Returns:`.

**Before:**

```python
async def fetch_json(session, url, *, timeout=30):
    async with session.get(url, timeout=timeout) as response:
        response.raise_for_status()
        return await response.json()
```

**After:**

```python
async def fetch_json(session, url, *, timeout=30):
    """Fetch ``url`` and return the parsed JSON body.

    Args:
        session: An ``aiohttp.ClientSession`` (or compatible) instance.
        url: URL to GET.
        timeout: Request timeout in seconds. Defaults to 30.

    Returns:
        The parsed JSON body of the response, as returned by
        ``response.json()``.

    Raises:
        aiohttp.ClientResponseError: If the response status is not 2xx.
    """
    async with session.get(url, timeout=timeout) as response:
        response.raise_for_status()
        return await response.json()
```

---

## 5. Class with attributes and methods

Document the class on its docstring; document each public method on its own.

**Before:**

```python
class LRUCache:
    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self.maxsize = maxsize
        self._data: dict = {}

    def get(self, key):
        if key not in self._data:
            return None
        value = self._data.pop(key)
        self._data[key] = value
        return value

    def put(self, key, value) -> None:
        if key in self._data:
            self._data.pop(key)
        elif len(self._data) >= self.maxsize:
            self._data.pop(next(iter(self._data)))
        self._data[key] = value
```

**After:**

```python
class LRUCache:
    """A bounded least-recently-used cache backed by an insertion-ordered dict.

    On insertion past ``maxsize``, the least-recently-used entry is evicted.
    Access via :meth:`get` promotes an entry to most-recently-used. The
    cache is not thread-safe.

    Attributes:
        maxsize: Maximum number of entries before eviction begins.
    """

    def __init__(self, maxsize: int) -> None:
        """Initialise the cache with capacity ``maxsize``.

        Args:
            maxsize: Maximum number of entries. Must be strictly positive.

        Raises:
            ValueError: If ``maxsize`` is not strictly positive.
        """
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self.maxsize = maxsize
        self._data: dict = {}

    def get(self, key):
        """Return the value for ``key`` and mark it most-recently-used.

        Args:
            key: Lookup key.

        Returns:
            The value previously associated with ``key``, or ``None`` if no
            such entry exists.
        """
        if key not in self._data:
            return None
        value = self._data.pop(key)
        self._data[key] = value
        return value

    def put(self, key, value) -> None:
        """Insert or update ``key`` with ``value``, evicting if necessary.

        If ``key`` already exists, its position is refreshed to
        most-recently-used. Otherwise, when the cache is full, the
        least-recently-used entry is evicted before insertion.

        Args:
            key: Lookup key.
            value: Value to associate with ``key``.
        """
        if key in self._data:
            self._data.pop(key)
        elif len(self._data) >= self.maxsize:
            self._data.pop(next(iter(self._data)))
        self._data[key] = value
```

Note: `self` is not documented. `__init__` has no `Returns:` section. The class docstring lists `maxsize` under `Attributes:` because it is part of the class's public surface.

---

## 6. Dataclass

Use `Attributes:` for the fields. Do not duplicate the type — the annotation already states it.

**Before:**

```python
from dataclasses import dataclass

@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: dict[str, str]
```

**After:**

```python
from dataclasses import dataclass

@dataclass
class HttpResponse:
    """An HTTP response captured as raw bytes plus headers.

    Attributes:
        status: HTTP status code (e.g. 200, 404).
        body: Raw response body. Not decoded.
        headers: Response headers as a mapping from name to value.
    """
    status: int
    body: bytes
    headers: dict[str, str]
```

---

## 7. Property, setter, deleter

The property's docstring lives on the getter only.

**Before:**

```python
class Temperature:
    def __init__(self, celsius: float) -> None:
        self._c = celsius

    @property
    def fahrenheit(self) -> float:
        return self._c * 9 / 5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value: float) -> None:
        self._c = (value - 32) * 5 / 9
```

**After:**

```python
class Temperature:
    """A temperature value held internally in degrees Celsius."""

    def __init__(self, celsius: float) -> None:
        """Initialise from a Celsius value.

        Args:
            celsius: Temperature in degrees Celsius.
        """
        self._c = celsius

    @property
    def fahrenheit(self) -> float:
        """The temperature in degrees Fahrenheit."""
        return self._c * 9 / 5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value: float) -> None:
        """Set the temperature from a Fahrenheit value."""
        self._c = (value - 32) * 5 / 9
```

The getter uses a one-line docstring describing the value. The setter gets a one-line summary because its behaviour is fully captured by it.

---

## 8. Context manager (`@contextmanager`)

Use `Yields:` for the value bound by `as`.

**Before:**

```python
from contextlib import contextmanager

@contextmanager
def temporary_directory(prefix: str = "tmp"):
    import shutil, tempfile
    path = tempfile.mkdtemp(prefix=prefix)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
```

**After:**

```python
from contextlib import contextmanager

@contextmanager
def temporary_directory(prefix: str = "tmp"):
    """Create a temporary directory and remove it on exit.

    The directory is removed when the ``with`` block exits, regardless of
    whether the block raised. ``ignore_errors=True`` is passed to
    ``shutil.rmtree``, so a partially-deleted directory does not raise
    on cleanup.

    Args:
        prefix: Prefix for the directory name. Defaults to ``"tmp"``.

    Yields:
        The absolute path of the newly-created directory, as a string.
    """
    import shutil, tempfile
    path = tempfile.mkdtemp(prefix=prefix)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
```

---

## 9. Decorator factory

Document what the *wrapped* function gains, not just the factory's parameters.

**Before:**

```python
import functools, time

def retry(times: int, *, delay: float = 0.0):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for _ in range(times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if delay:
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
```

**After:**

```python
import functools, time

def retry(times: int, *, delay: float = 0.0):
    """Return a decorator that retries the wrapped call on any exception.

    The wrapped callable is invoked, and on any raised exception is
    re-invoked up to ``times`` additional times. Between attempts the
    decorator sleeps for ``delay`` seconds. If every attempt fails, the
    exception from the final attempt is re-raised.

    Args:
        times: Number of additional attempts after the first. Must be
            non-negative.
        delay: Seconds to wait between attempts. Defaults to ``0``.

    Returns:
        A decorator that, when applied to a callable, produces a wrapper
        with the same signature and the retry behaviour described above.

    Note:
        The decorator catches every ``Exception``. Callers that need to
        exclude particular exception types should wrap or replace it.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for _ in range(times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if delay:
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
```

---

## 10. NumPy → Google conversion

Preserve facts; change syntax.

**Before (NumPy style):**

```python
def percentile(arr, q):
    """Return the q-th percentile of arr.

    Parameters
    ----------
    arr : array-like
        Input data, treated as a flat sequence of numbers.
    q : float
        Percentile to compute, in [0, 100].

    Returns
    -------
    float
        The interpolated percentile.

    Raises
    ------
    ValueError
        If q is outside [0, 100].
    """
    import numpy as np
    return float(np.percentile(np.asarray(arr).ravel(), q))
```

**After (Google style):**

```python
def percentile(arr, q):
    """Return the ``q``-th percentile of ``arr``.

    Args:
        arr: Input data, treated as a flat sequence of numbers (anything
            accepted by ``numpy.asarray``).
        q (float): Percentile to compute, in ``[0, 100]``.

    Returns:
        The interpolated percentile, as a Python ``float``.

    Raises:
        ValueError: If ``q`` is outside ``[0, 100]``.
    """
    import numpy as np
    return float(np.percentile(np.asarray(arr).ravel(), q))
```

The substance is preserved; only the syntactic structure changed.

---

## 11. reST → Google conversion

**Before (reST style):**

```python
def open_db(path, *, readonly=False):
    """Open a SQLite database.

    :param path: Path to the database file.
    :type path: str
    :param readonly: If True, open in read-only mode.
    :type readonly: bool
    :returns: A connection object.
    :rtype: sqlite3.Connection
    :raises sqlite3.OperationalError: If the file cannot be opened.
    """
    import sqlite3
    uri = f"file:{path}?mode=ro" if readonly else path
    return sqlite3.connect(uri, uri=readonly)
```

**After (Google style):**

```python
def open_db(path, *, readonly=False):
    """Open a SQLite database at ``path``.

    Args:
        path (str): Path to the database file.
        readonly (bool): If ``True``, open in read-only mode using a
            ``file:`` URI. Defaults to ``False``.

    Returns:
        A ``sqlite3.Connection`` to the database.

    Raises:
        sqlite3.OperationalError: If the file cannot be opened (e.g. the
            path is missing or inaccessible).
    """
    import sqlite3
    uri = f"file:{path}?mode=ro" if readonly else path
    return sqlite3.connect(uri, uri=readonly)
```

When the source had `:type x:` markers and the signature has no annotations, fold the type into the `Args:` entry. When the signature *does* have annotations, drop the parenthetical type — the annotation is the source of truth.

---

## 12. Function with side effects, no return value

Omit `Returns:` and describe the side effect.

**Before:**

```python
def write_atomic(path, data: bytes) -> None:
    import os, tempfile
    dir_ = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise
```

**After:**

```python
def write_atomic(path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically via a temporary file and rename.

    The bytes are first written to a sibling temporary file in the same
    directory as ``path``, then renamed onto ``path``. The rename is
    atomic on POSIX filesystems and on Windows for files within the same
    volume. If writing fails, the temporary file is removed and the
    original ``path`` is left untouched.

    Args:
        path: Destination filesystem path.
        data: Bytes to write.

    Raises:
        OSError: If the temporary file cannot be created, written, or
            renamed onto ``path``.
    """
    import os, tempfile
    dir_ = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise
```

The function returns `None`, so there is no `Returns:` block. The atomicity guarantee is the actual interface — that goes in the longer description, not the summary.
