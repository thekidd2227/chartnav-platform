#!/usr/bin/env python3
"""Production gate wrapper for marketing asset governance.

Delegates to scripts/marketing/validate_chartnav_assets.py so the production
readiness check fails if the public marketing bank is invalid (orphans,
duplicate hashes, missing approval metadata, schema violations). Stdlib only.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "marketing"))


def main() -> int:
    try:
        from validate_chartnav_assets import main as validate_main
    except ImportError as e:
        print(f"❌ cannot import marketing validator: {e}")
        return 1
    rc = validate_main()
    if rc == 0:
        print("✅ marketing asset governance gate passed")
    return rc


if __name__ == "__main__":
    sys.exit(main())
