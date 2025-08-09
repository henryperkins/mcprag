// Cloudflare Worker type declarations
// These would normally come from @cloudflare/workers-types

declare global {
  interface D1Database {
    prepare(query: string): D1PreparedStatement;
  }

  interface D1PreparedStatement {
    bind(...values: unknown[]): D1PreparedStatement;
    run(): Promise<D1Result>;
    first(): Promise<unknown>;
    all(): Promise<D1ResultSet>;
  }

  interface D1Result {
    success: boolean;
    meta: Record<string, unknown>;
  }

  interface D1ResultSet {
    results: unknown[];
    success: boolean;
  }

  interface KVNamespace {
    get(key: string): Promise<string | null>;
    put(key: string, value: string): Promise<void>;
    delete(key: string): Promise<void>;
    list(options?: { prefix?: string }): Promise<{ keys: { name: string }[] }>;
  }

  interface R2Bucket {
    put(key: string, value: ReadableStream | ArrayBuffer, options?: R2PutOptions): Promise<R2Object>;
    get(key: string): Promise<R2Object | null>;
    delete(key: string): Promise<void>;
    createSignedUrl(key: string, options: { expiresIn: number }): Promise<string>;
  }

  interface R2PutOptions {
    httpMetadata?: { contentType?: string };
    customMetadata?: Record<string, string>;
  }

  interface R2Object {
    key: string;
    size: number;
    body: ReadableStream;
  }

  interface Queue {
    send(message: unknown): Promise<void>;
  }

  interface DurableObjectNamespace {
    idFromName(name: string): DurableObjectId;
    get(id: DurableObjectId): DurableObjectStub;
  }

  interface DurableObjectId {
    toString(): string;
  }

  interface DurableObjectStub {
    fetch(request: Request): Promise<Response>;
  }

  interface ExecutionContext {
    waitUntil(promise: Promise<unknown>): void;
    passThroughOnException(): void;
  }

  class WebSocketPair {
    0: WebSocket;
    1: WebSocket;
  }
}

export {};