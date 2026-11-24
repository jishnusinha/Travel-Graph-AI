from __future__ import annotations

import argparse
import asyncio
import json

from app.db.session import engine
from app.seed.demo_seed import DEMO_EMAIL, DEMO_PASSWORD, REVIEWER_EMAIL, run_seed


async def _main(reset: bool) -> None:
    try:
        summary = await run_seed(reset=reset)
    finally:
        await engine.dispose()
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nDemo login:     {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"Reviewer login: {REVIEWER_EMAIL} / {DEMO_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.seed", description="Seed TravelGraph local demo data")
    parser.add_argument("--reset", action="store_true", help="delete the seeded demo users' data first, then reseed")
    args = parser.parse_args()
    asyncio.run(_main(args.reset))


if __name__ == "__main__":
    main()
