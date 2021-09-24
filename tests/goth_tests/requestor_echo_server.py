#!/usr/bin/env python3
import asyncio
import sys

SUBNET_TAG = sys.argv[1]

async def main():
    print("AAAA")
    await asyncio.sleep(10)
    print("BBBB")
    assert False

if __name__ == "__main__":
    asyncio.run(main())
