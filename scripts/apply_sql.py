"""Apply SQL files to the database pointed to by DATABASE_URL."""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

import asyncpg


async def apply_files(files: list[str]) -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    conn = await asyncpg.connect(database_url)
    try:
        for file_name in files:
            path = Path(file_name)
            sql = path.read_text(encoding="utf-8")
            await conn.execute(sql)
            print(f"applied {path}")
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply SQL files using DATABASE_URL.")
    parser.add_argument("files", nargs="+", help="SQL files to apply in order.")
    args = parser.parse_args()
    asyncio.run(apply_files(args.files))


if __name__ == "__main__":
    main()
