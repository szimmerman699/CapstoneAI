import asyncio

from capstone_ai.core.ai_client import AIClient


async def add(input: dict) -> str:
    return str(input["a"] + input["b"])


TOOLS = [
    {
        "name": "add",
        "description": "Add two numbers together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    }
]

TOOL_HANDLERS = {"add": add}


async def main():
    client = AIClient()
    try:
        result = await client.tool_conversation(
            messages=[{"role": "user", "content": "What is 47 plus 55? Use the add tool."}],
            tools=TOOLS,
            tool_handler=TOOL_HANDLERS,
        )
        print(result)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
