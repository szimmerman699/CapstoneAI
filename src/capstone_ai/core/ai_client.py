import anthropic
import json
import logging

from pydantic import BaseModel, Field
from capstone_ai.core.prompt_loader import load_prompt
from capstone_ai.core.config import settings
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class MeetingSummary(BaseModel):
    title: str = Field(description="Short meeting title, e.g. 'Q3 Planning Standup'")
    date: str = Field(description="Meeting date in ISO format (YYYY-MM-DD)")
    attendees: list[str] = Field(description="Full names of people who attended")
    action_items: list[str] = Field(description="One entry per commitment, prefixed with the owner's name")
    key_decisions: list[str] = Field(description="Decisions reached, excluding items still under discussion")


EXTRACT_MEETING_TOOL = {
    "name": "record_meeting_summary",
    "description": "Record a structured summary of a meeting transcript.",
    "input_schema": MeetingSummary.model_json_schema(),
}


def first_text(content: list) -> str:
    """Return the first text block's text, skipping thinking and tool_use blocks."""
    for block in content:
        if block.type == "text":
            return block.text
    return ""


class AIClient:
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.model_name
        self._max_tokens = settings.max_tokens

    async def message(self, user_message: str, system: str = "") -> str:
        if not system:
            system = load_prompt("system_default.txt")
        params: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": user_message}],
            "system": system,
        }
        response = await self._client.messages.create(**params)
        return first_text(response.content)

    async def close(self):
        await self._client.close()

    async def conversation(
        self,
        messages: list[dict],
        system: str = "",
    ) -> anthropic.types.Message:
        params: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if system:
            params["system"] = system
        return await self._client.messages.create(**params)

    async def stream_message(
        self,
        user_message: str,
        system: str = "",
    ) -> AsyncIterator[str]:
        params: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": user_message}],
        }
        if system:
            params["system"] = system

        async with self._client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text
                
    async def tool_conversation(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_handler: dict,
        system: str = "",
        max_tool_rounds: int = 5,
    ) -> str:
        params: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": list(messages),
            "tools": tools,
        }
        if system:
            params["system"] = system

        for round_num in range(1, max_tool_rounds + 1):
            response = await self._client.messages.create(**params)
            logger.debug("tool round %d: stop_reason=%s", round_num, response.stop_reason)

            # Loop ONLY on tool_use. Every other stop_reason is terminal.
            if response.stop_reason != "tool_use":
                text_blocks = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_blocks)

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = tool_handler.get(block.name)
                    if handler:
                        result = await handler(block.input)
                    else:
                        result = f"Error: unknown tool '{block.name}'"
                    logger.debug("tool %s(%s) -> %s", block.name, json.dumps(block.input), result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })

            params["messages"].append({"role": "assistant", "content": response.content})
            params["messages"].append({"role": "user", "content": tool_results})

        return "Max tool rounds exceeded"

    async def extract_structured(
        self,
        user_message: str,
        tool: dict,
        model: type[BaseModel],
        system: str = "",
    ) -> BaseModel:
        params: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": user_message}],
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": tool["name"]},
        }
        if system:
            params["system"] = system

        response = await self._client.messages.create(**params)
        for block in response.content:
            if block.type == "tool_use":
                return model.model_validate(block.input)

        raise ValueError("Model did not return a tool_use block")


async def main():
    client = AIClient()
    try:
        async for chunk in client.stream_message("Explain async/await in Python in 3 sentences."):
            print(chunk, end="", flush=True)
        print()

        transcript = """
        Team standup March 15. Alice, Bob, and Carol attended.
        We decided to switch from REST to GraphQL for the internal API.
        Action items: Alice will draft the GraphQL schema by Friday.
        Bob will benchmark query performance. Carol updates the documentation.
        """

        summary = await client.extract_structured(
            transcript, EXTRACT_MEETING_TOOL, MeetingSummary
        )
        print(summary.model_dump_json(indent=2))

        print(MeetingSummary.model_json_schema())
        
    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
