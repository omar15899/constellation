# Python Asyncio Notes

## Event Loop Architecture

The asyncio event loop manages coroutines, tasks, and I/O operations.

```
┌─────────────────────────────────────┐
│          Event Loop                 │
│                                     │
│  ┌──────────┐    ┌──────────────┐   │
│  │ Ready    │    │  I/O polling │   │
│  │ Queue    │───►│  (selector)  │   │
│  └──────────┘    └──────────────┘   │
│       │                │            │
│       ▼                ▼            │
│  ┌──────────┐    ┌──────────────┐   │
│  │Callbacks │    │  Callbacks   │   │
│  └──────────┘    └──────────────┘   │
└─────────────────────────────────────┘
```

## Task Lifecycle

```
PENDING ──► RUNNING ──► DONE
               │
               ▼
           CANCELLED
```

## coroutine vs task

| Concept   | Type          | Scheduled? |
|-----------|---------------|------------|
| coroutine | `Coroutine`   | No         |
| task      | `Task`        | Yes        |
| future    | `Future`      | No         |

## Code example

```python
import asyncio

async def fetch(url: str) -> str:
    await asyncio.sleep(1)
    return f"Response from {url}"

async def main():
    results = await asyncio.gather(
        fetch("http://example.com/a"),
        fetch("http://example.com/b"),
    )
    print(results)

asyncio.run(main())
```
