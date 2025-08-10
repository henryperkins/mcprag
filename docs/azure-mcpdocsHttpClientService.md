---
title: "azure-mcp/docs/HttpClientService.md at main · henryperkins/azure-mcp"
source: "https://github.com/henryperkins/azure-mcp/blob/main/docs/HttpClientService.md"
author:
  - "[[Copilot]]"
  - "[[jongio]]"
published:
created: 2025-08-09
description:
tags:
  - "clippings"
---
#### We are having a problem billing your account. Please update your payment method or check with your payment provider for details on why the transaction failed.

You can always [contact support](https://github.com/contact) with any questions.

[Open in github.dev](https://github.dev/) [Open in a new github.dev tab](https://github.dev/) [Open in codespace](https://github.com/codespaces/new/henryperkins/azure-mcp/tree/main?resume=1)

and

[Implement centralized HttpClient service with proxy support (](https://github.com/henryperkins/azure-mcp/commit/01da131db7899f9cf3334e2641637bdd2e74f89a)[Azure#857](https://github.com/Azure/azure-mcp/pull/857)[)](https://github.com/henryperkins/azure-mcp/commit/01da131db7899f9cf3334e2641637bdd2e74f89a)

[01da131](https://github.com/henryperkins/azure-mcp/commit/01da131db7899f9cf3334e2641637bdd2e74f89a) ·

This document describes the centralized HttpClient service implementation for Azure MCP.

## Overview

The Azure MCP now provides a centralized `IHttpClientService` that allows for global control of HTTP options, proxy configuration, and resource management. This addresses the issue where many commands were creating HttpClient instances directly without centralized configuration.

## Key Features

- **Centralized Configuration**: All HttpClient instances are configured consistently
- **Proxy Support**: Automatic proxy configuration from environment variables
- **Resource Management**: Proper lifecycle management and disposal
- **Dependency Injection**: Injectable service for better testability
- **AOT Compatibility**: Designed to work with AOT compilation

## Environment Variables

The service automatically reads and applies the following environment variables:

- `ALL_PROXY`: Global proxy for all protocols
- `HTTP_PROXY`: Proxy for HTTP requests only
- `HTTPS_PROXY`: Proxy for HTTPS requests only
- `NO_PROXY`: Comma-separated list of hosts that should bypass the proxy

## Usage

### Service Registration

The HttpClient service is automatically registered in the Core dependency injection container:

```
// In ServiceCollectionExtensions.cs
services.AddHttpClientServices();
```

### Custom Configuration

You can provide custom configuration when registering the service:

```
services.AddHttpClientServices(options =>
{
    options.DefaultTimeout = TimeSpan.FromSeconds(30);
    options.DefaultUserAgent = "MyCustomAgent/1.0";
});
```

Services should inject `IHttpClientService` and use it to create HttpClient instances:

```
public class MyService(IHttpClientService httpClientService)
{
    private readonly IHttpClientService _httpClientService = httpClientService;

    public async Task MakeRequestAsync()
    {
        // Use the default client
        var response = await _httpClientService.DefaultClient.GetAsync("https://api.example.com");

        // Or create a client with specific base address
        using var client = _httpClientService.CreateClient(new Uri("https://management.azure.com"));
        var mgmtResponse = await client.GetAsync("/subscriptions");
    }
}
```
```
public class UpdatedService(IHttpClientService httpClientService)
{
    private readonly IHttpClientService _httpClientService = httpClientService;

    public async Task MakeRequestAsync()
    {
        // For general requests
        var response = await _httpClientService.DefaultClient.GetAsync(url);

        // For requests to a specific base address
        using var client = _httpClientService.CreateClient(new Uri("https://api.service.com"));
        var serviceResponse = await client.GetAsync("/endpoint");
    }
}
```

## Configuration Options

The `HttpClientOptions` class provides the following configuration:

```
public sealed class HttpClientOptions
{
    public string? HttpProxy { get; set; }           // HTTP_PROXY env var
    public string? HttpsProxy { get; set; }          // HTTPS_PROXY env var
    public string? AllProxy { get; set; }            // ALL_PROXY env var
    public string? NoProxy { get; set; }             // NO_PROXY env var
    public TimeSpan DefaultTimeout { get; set; }    // Default: 100 seconds
    public string? DefaultUserAgent { get; set; }   // Custom User-Agent
}
```

## Updated Services

The following services have been updated to use the new HttpClient service:

1. **MonitorHealthModelService**: Replaced static HttpClient with injected service
2. **KustoClient**: Updated to accept IHttpClientService and create clients with base address
3. **FoundryService**: Eliminated per-request HttpClient creation

## Benefits

- **Performance**: Eliminates expensive per-request HttpClient creation
- **Resource Management**: Proper disposal and lifecycle management
- **Consistency**: All HTTP requests use the same configuration
- **Proxy Support**: Centralized proxy configuration for corporate environments
- **Testability**: Injectable service makes unit testing easier
- **Maintainability**: Single place to modify HTTP behavior

## Testing

Comprehensive unit tests are provided in:

- `HttpClientServiceTests.cs`: Core service functionality
- `HttpClientServiceCollectionExtensionsTests.cs`: Dependency injection registration
- `HttpClientServiceIntegrationTests.cs`: End-to-end scenarios
```
# Set proxy environment variables
export ALL_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,*.internal

# Start Azure MCP - proxy configuration is automatically applied
./azmcp server start
```

All HTTP requests made by Azure MCP services will now use the configured proxy settings automatically.