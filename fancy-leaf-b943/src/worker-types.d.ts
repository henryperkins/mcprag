// Cloudflare Worker type declarations
// These would normally come from @cloudflare/workers-types

declare global {
  interface D1Database {
    prepare(query: string): D1PreparedStatement;
    // D1 Sessions API
    session(): D1Session;
  }
  
  interface D1Session {
    prepare(query: string): D1PreparedStatement;
    exec(query: string): Promise<void>;
    close(): Promise<void>;
  }
  

  interface D1PreparedStatement {
    bind(...values: unknown[]): D1PreparedStatement;
    run(): Promise<D1Result>;
    first<T = unknown>(): Promise<T | null>;
    all<T = unknown>(): Promise<D1ResultSet<T>>;
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

  // Cloudflare Queues types (minimal)
  interface Message<T = unknown> {
    body: T;
    retries: number;
    ack(): Promise<void>;
    retry(delaySeconds?: number): Promise<void>;
  }
  interface MessageBatch<T = unknown> {
    messages: Message<T>[];
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

  interface DurableObjectState {
    storage: {
      get<T = unknown>(key: string): Promise<T | undefined>;
      put<T = unknown>(key: string, value: T): Promise<void>;
      delete(key: string): Promise<void>;
    };
    waitUntil(promise: Promise<unknown>): void;
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