from datetime import date
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

    def _run(self, query: str) -> list[dict[str, str]]:
        ddgs: DDGS = get_ddgs_client()
        results: list[dict[str, str]] = ddgs.text(
            query=query,
            region="de-de",
            backend="google",
            max_results=5,
        )
        return results


class GetCurrentDateTool(BaseTool):
    """Tool to get the current date."""

    name: str = "get_current_date"
    description: str = "Get the current date in YYYY-MM-DD format."
    args_schema: ArgsSchema | None = None
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(self) -> str:
        current_date: str = date.today().isoformat()
        return current_date
