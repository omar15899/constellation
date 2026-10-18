#!/usr/bin/env python3
"""Compatibility entry point for the shared Constellation dispatch runtime."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
_PACKAGE_PARENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PACKAGE_PARENT))
from ecosystem.runtime import dispatch as _runtime

# Existing Python consumers receive the same module, classes and exceptions.
sys.modules[__name__] = _runtime
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})
