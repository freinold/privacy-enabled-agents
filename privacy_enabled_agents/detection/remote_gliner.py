from collections.abc import Sequence
from logging import Logger, getLogger
from typing import Any, TypeVar
from urllib.parse import urljoin

from httpx import Client, HTTPError, Response, get
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from stamina import retry

from privacy_enabled_agents import Entity
from privacy_enabled_agents.detection import BaseDetector

logger: Logger = getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class RemoteGlinerDetector(BaseDetector):
    """
    RemoteGlinerDetector class for detecting entities in text using a remote GLiNER API.
    """

    _client: Client
    _default_threshold: float
    _model_id: str

    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        api_key: str | None = None,
        supported_entities: set[str] | None = None,
    ) -> None:
        info_url: str = urljoin(base=base_url, url="/api/info")
        response: Response = get(info_url)
        response.raise_for_status()
        info_response: RemoteInfoResponse = RemoteInfoResponse.model_validate(response.json())

        logger.debug(f"GLiNER API Endpoint Info:\n{info_response.model_dump_json(indent=2)}")

        if info_response.api_key_required and not api_key:
            raise ValueError("API key is required for this detector instance.")

        supported_entities = set(info_response.default_entities) if supported_entities is None else supported_entities
        super().__init__(
            name=f"RemoteGlinerDetector-{info_response.configured_use_case}",
            supported_entities=supported_entities,
        )
        self._model_id = info_response.model_id
        self._default_threshold = info_response.default_threshold
        self._client = Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    def invoke(
        self,
        input: str,
        config: RunnableConfig | None = None,
        *,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> list[Entity]:
        invoke_response: RemoteInvokeResponse = self._call_api_and_validate(
            path="/api/invoke",
            json={
                "text": input,
                "threshold": threshold or self._default_threshold,
                "entity_types": list(self.supported_entities),
            },
            validation_model=RemoteInvokeResponse,
        )
        return invoke_response.entities

    def batch(
        self,
        inputs: Sequence[str],
        config: RunnableConfig | list[RunnableConfig] | None = None,
        *,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> list[list[Entity]]:
        batch_response: RemoteBatchResponse = self._call_api_and_validate(
            path="/api/batch",
            json={
                "texts": inputs,
                "threshold": threshold or self._default_threshold,
                "entity_types": list(self.supported_entities),
            },
            validation_model=RemoteBatchResponse,
        )
        return batch_response.entities

    @retry(on=HTTPError, attempts=3)
    def _call_api_and_validate(self, path: str, json: dict[str, Any] | None, validation_model: type[T]) -> T:
        response: Response = self._client.post(path, json=json)
        response.raise_for_status()
        return validation_model.model_validate(response.json())


class RemoteInfoResponse(BaseModel):
    configured_use_case: str
    model_id: str
    default_entities: list[str]
    default_threshold: float
    api_key_required: bool


class RemoteInvokeResponse(BaseModel):
    entities: list[Entity]


class RemoteBatchResponse(BaseModel):
    entities: list[list[Entity]]


class InitError(Exception):
    """Exception raised when the detector fails to initialize."""


class RemoteDetectionError(Exception):
    """Exception raised when the API detection fails."""
