"""One simple way to talk to the LLM, whichever provider .env points at."""
import json
import os
import time

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI, RateLimitError
from pydantic import BaseModel

load_dotenv()


def _client() -> OpenAI:
    return OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])


def _ask(messages: list[dict], json_schema: dict | None) -> str:
    """Send one request; wait and retry if the provider says 'slow down' (HTTP 429)."""
    kwargs = {}
    if json_schema is not None:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "answer", "schema": json_schema},
        }
    for attempt in range(8):
        try:
            reply = _client().chat.completions.create(
                model=os.environ["LLM_MODEL"], messages=messages, **kwargs
            )
            return reply.choices[0].message.content or ""
        except RateLimitError:
            time.sleep(min(2**attempt, 30))  # wait 1, 2, 4, 8, 16, 30, 30, 30 seconds
    raise RuntimeError("LLM kept answering 'rate limit' (429); try again later.")


def chat(messages: list[dict], json_schema: dict | None = None) -> str:
    """Return the model's reply text. Pass json_schema to ask for JSON output."""
    return _ask(messages, json_schema)


def chat_json(messages: list[dict], model_class: type[BaseModel]) -> BaseModel | None:
    """Ask for JSON, validate with Pydantic, retry once, then give up (None) and log."""
    schema = model_class.model_json_schema()
    for _ in range(2):
        try:
            text = _ask(messages, schema)
        except BadRequestError:  # e.g. Groq 400 json_validate_failed: the model produced no valid JSON
            continue
        try:
            return model_class.model_validate(json.loads(text))
        except ValueError:  # bad JSON or failed validation
            continue
    print("chat_json: invalid JSON twice, skipping.")
    return None
