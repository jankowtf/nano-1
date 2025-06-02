"""Main entry point."""

import asyncio
from test-nanobricks-app import greeting_pipeline


async def main():
    result = await greeting_pipeline.invoke("world")
    print(result)  # "HELLO, WORLD!"


if __name__ == "__main__":
    asyncio.run(main())
