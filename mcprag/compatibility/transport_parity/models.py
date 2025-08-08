from __future__ import annotations

"""
Transport-agnostic wire models for MCP parity across stdio, HTTP, SSE.

NOTE: Reference models for documentation and future work; not imported by the
runtime server. Safe to remove if you don’t need transport parity prototypes.

Spec references: docs/transport-parity/schemas/* and docs/MCP_TRANSPORT_PARITY_GUIDE_V2.md
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union, Literal, TypedDict, ClassVar
import json


@dataclass
class VersionRange:
    min: str
    max: Optional[str] = None


@dataclass
class Capabilities:
    protocol: VersionRange
    streaming: bool
    resume: bool
    idempotentRetry: Optional[bool] = None
    maxConcurrent: Optional[int] = None
    maxPayloadBytes: Optional[int] = None


@dataclass
class Handshake:
    type: ClassVar[Literal["handshake"]] = "handshake"
    protocolVersion: str
    sessionId: str
    capabilities: Capabilities
    resumeToken: Optional[str] = None
    auth: Optional[Dict[str, Any]] = None


@dataclass
class RequestEnvelope:
    type: ClassVar[Literal["request"]] = "request"
    id: Union[str, int]
    method: str
    params: Dict[str, Any]
    stream: Optional[bool] = None
    idempotent: Optional[bool] = None
    headers: Optional[Dict[str, str]] = None
    traceId: Optional[str] = None


@dataclass
class ErrorObject:
    code: Literal[
        "invalid_request",
        "version_unsupported",
        "feature_not_available",
        "auth.unauthorized",
        "auth.forbidden",
        "rate_limited",
        "payload_too_large",
        "already_processed",
        "internal",
    ]
    message: str
    details: Optional[Any] = None
    retryable: Optional[bool] = None
    retryAfter: Optional[int] = None


class ResponseResult(TypedDict):
    id: Union[str, int]
    type: Literal["response"]
    result: Any


class ResponseError(TypedDict):
    id: Union[str, int]
    type: Literal["response"]
    error: Dict[str, Any]


ResponseEnvelope = Union[ResponseResult, ResponseError]


@dataclass
class StreamChunk:
    type: ClassVar[Literal["stream"]] = "stream"
    streamId: str
    seq: int
    chunkType: Literal["data", "progress", "eos", "err", "keepalive"]
    data: Optional[Any] = None
    offset: Optional[int] = None


@dataclass
class CancelMessage:
    type: ClassVar[Literal["cancel"]] = "cancel"
    id: Optional[Union[str, int]] = None
    streamId: Optional[str] = None


@dataclass
class Keepalive:
    type: ClassVar[Literal["keepalive"]] = "keepalive"
    ts: str
    timeoutHintSec: Optional[int] = None


def encode_request(r: RequestEnvelope) -> str:
    """Encode a RequestEnvelope to JSON string."""
    obj = asdict(r)
    obj["type"] = "request"
    return json.dumps(obj)


def decode_response(s: str) -> ResponseEnvelope:
    """Decode a JSON string into a ResponseEnvelope."""
    return json.loads(s)


__all__ = [
    "VersionRange",
    "Capabilities",
    "Handshake",
    "RequestEnvelope",
    "ErrorObject",
    "ResponseResult",
    "ResponseError",
    "ResponseEnvelope",
    "StreamChunk",
    "CancelMessage",
    "Keepalive",
    "encode_request",
    "decode_response",
]
