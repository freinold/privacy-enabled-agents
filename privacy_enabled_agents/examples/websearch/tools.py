from functools import lru_cache
from typing import Literal

from ddgs import DDGS
from langchain_core.tools import ArgsSchema, BaseTool
from pydantic import BaseModel, Field


@lru_cache
def get_ddgs_client() -> DDGS:
    """Create and return a DDGS client for web search."""
    return DDGS()


class SearchWebInput(BaseModel):
    """Input schema for the search_web tool."""

    query: str = Field(
        description="The search query to perform on the web.",
        max_length=200,
        min_length=1,
    )


class SearchWebTool(BaseTool):
    """Tool to perform a web search."""

    name: str = "search_web"
    description: str = "Perform a web search with the given query."
    args_schema: ArgsSchema | None = SearchWebInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(self, input: SearchWebInput) -> list[dict[str, str]]:
        client: DDGS = get_ddgs_client()
        results: list[dict[str, str]] = client.text(
            query=input.query,
            region="de-de",
            safesearch="on",
            max_results=5,
            backend="duckduckgo",
        )
        return results
