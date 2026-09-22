import json
import logging
import time
import uuid
import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from capstone_ai.core.ai_client import AIClient
from capstone_ai.core.config import settings
from capstone_ai.api.models import ChatRequest, ChatResponse
from fastapi.responses import StreamingResponse
from capstone_ai.api.models import ToolRequest, ChatResponse
from anthropic import APIError
from fastapi.responses import JSONResponse
from fastapi import Depends, Security
from fastapi.security import APIKeyHeader
from capstone_ai.api.models import ErrorResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logging.basicConfig(level=logging.INFO)
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    expected = "dev-key-change-in-production"
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ai_client = AIClient()
    yield
    await app.state.ai_client.close()


# Define tools and handlers at module level (or load from config)
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city. Use this when the user asks about weather.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["city"],
        },
    }
]

logger = logging.getLogger(__name__)


async def handle_weather(params: dict) -> str:
    return json.dumps({"city": params["city"], "temp_c": 22, "condition": "sunny"})


TOOL_HANDLERS = {"get_weather": handle_weather}

app = FastAPI(title="Capstone AI API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])

async def chat(request: ChatRequest):
    try:
        result = await app.state.ai_client.message(
            request.message, system=request.system
        )
        return ChatResponse(response=result, model=settings.model_name)
    except APIError:
        raise  # handled by anthropic_error_handler -> structured 502
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/chat/stream", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            async for chunk in app.state.ai_client.stream_message(
                request.message, system=request.system
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

@app.post("/chat/tools", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat_with_tools(request: ToolRequest):
    try:
        result = await app.state.ai_client.tool_conversation(
            messages=[{"role": "user", "content": request.message}],
            tools=TOOLS,
            tool_handler=TOOL_HANDLERS,
            system=request.system,
        )
        return ChatResponse(response=result, model=settings.model_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        response = await call_next(request)

        elapsed = time.perf_counter() - start
        logger.info(
            "[%s] %s %s -> %d (%.3fs)",
            request_id, request.method, request.url.path,
            response.status_code, elapsed,
        )
        response.headers["X-Request-ID"] = request_id
        return response


# Add to app setup (after app = FastAPI(...)):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)



@app.exception_handler(APIError)
async def anthropic_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(error="AI service error", detail=str(exc)).model_dump(),
    )