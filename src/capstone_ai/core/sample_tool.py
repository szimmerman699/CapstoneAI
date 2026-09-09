import asyncio
import json
import logging

import anthropic
from anthropic import beta_async_tool

from capstone_ai.core.ai_client import AIClient
from capstone_ai.core.config import settings

logging.basicConfig(level=logging.DEBUG)  # so the loop's trace is visible

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["city"],
        },
    }
]

BROKEN_TOOLS = [
    {
        "name": "get_weather",
        "description": "Get weather",  # too vague
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},  # no description
            },
            # "required" missing
        },
    }
]


async def handle_weather(params: dict) -> str:
    city = params["city"]
    # Simulated weather data
    return json.dumps({"city": city, "temp_c": 22, "condition": "sunny"})


async def main():
    client = AIClient()
    try:
        tool_handler = {"get_weather": handle_weather}
        result = await client.tool_conversation(
            messages=[{"role": "user", "content": "What's the weather in Tel Aviv?"}],
            tools=TOOLS,
            tool_handler=tool_handler,
        )
        result = await client.tool_conversation(
                    messages=[{"role": "user", "content": "Broken Tools: What's the weather?"}],
                    tools=BROKEN_TOOLS,
                    tool_handler=tool_handler,
                )
        print(result)
    finally:
        await client.close()


@beta_async_tool
async def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: City name
    """
    # Simulated weather data
    return json.dumps({"city": city, "temp_c": 22, "condition": "sunny"})


async def main_tool_runner():
    """Same request as main(), but delegates the tool-use loop to the SDK's
    tool_runner instead of the hand-rolled loop in AIClient.tool_conversation."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        print("\n Starting tool runner")
        runner = client.beta.messages.tool_runner(
            model=settings.model_name,
            max_tokens=settings.max_tokens,
            messages=[{"role": "user", "content": "What's the weather in Tel Aviv?"}],
            tools=[get_weather],
        )
        final = await runner.until_done()
        text_blocks = [b.text for b in final.content if b.type == "text"]
        print("\n".join(text_blocks))
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main_tool_runner())