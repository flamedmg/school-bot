import asyncio


async def test_function():
    print("Starting test function")
    await asyncio.sleep(1)
    print("After sleep")
    return "Test complete"


async def main():
    print("Debug test starting")
    result = await test_function()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
