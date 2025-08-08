// MCP Transport Parity - TypeScript Interfaces
// Spec: docs/MCP_TRANSPORT_PARITY_GUIDE_V2.md and docs/transport-parity/schemas/*
// This module defines transport-agnostic wire types for stdio, HTTP and SSE

export interface Capabilities {
  protocol: { min: string; max?: string };
  streaming: boolean;
  resume: boolean;
  idempotentRetry?: boolean;
  maxConcurrent?: number;
  maxPayloadBytes?: number;
}

export interface Handshake {
  type: "handshake";
  protocolVersion: string;
  sessionId: string;
  resumeToken?: string;
  capabilities: Capabilities;
  auth?: {
    issuerUrl: string;
    resourceServerUrl: string;
    bearerMethodsSupported: ("header" | "query")[];
  };
}

export interface RequestEnvelope {
  id: string | number;
  type: "request";
  method: string;
  params: Record<string, unknown>;
  stream?: boolean;
  idempotent?: boolean;
  headers?: Record<string, string>;
  traceId?: string;
}

export interface ErrorObject {
  code:
    | "invalid_request"
    | "version_unsupported"
    | "feature_not_available"
    | "auth.unauthorized"
    | "auth.forbidden"
    | "rate_limited"
    | "payload_too_large"
    | "already_processed"
    | "internal";
  message: string;
  details?: unknown;
  retryable?: boolean;
  retryAfter?: number;
}

export type ResponseEnvelope =
  | { id: string | number; type: "response"; result: unknown }
  | { id: string | number; type: "response"; error: ErrorObject };

export interface StreamChunk {
  type: "stream";
  streamId: string;
  seq: number;
  chunkType: "data" | "progress" | "eos" | "err" | "keepalive";
  data?: unknown;
  offset?: number;
}

export type CancelMessage = {
  type: "cancel";
  id?: string | number;
  streamId?: string;
};

export type Keepalive = {
  type: "keepalive";
  ts: string; // ISO-8601
  timeoutHintSec?: number;
};

// Example helpers
export function encodeRequest(r: RequestEnvelope): string {
  return JSON.stringify(r);
}

export function decodeResponse(s: string): ResponseEnvelope {
  return JSON.parse(s) as ResponseEnvelope;
}