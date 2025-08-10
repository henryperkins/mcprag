---
title: "azure-mcp/docs/new-command.md at main · henryperkins/azure-mcp"
source: "https://github.com/henryperkins/azure-mcp/blob/main/docs/new-command.md"
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

[Enhance Azure MCP Server VSIX README with comprehensive service cover…](https://github.com/henryperkins/azure-mcp/commit/ca8709697045dbba702240938165774e2e8b75d3)

[ca87096](https://github.com/henryperkins/azure-mcp/commit/ca8709697045dbba702240938165774e2e8b75d3) ·

This document provides a comprehensive guide for implementing commands in Azure MCP following established patterns.

All new Azure services and their commands should use the Area pattern:

- **Area code** goes in `areas/{area-name}/src/AzureMcp.{AreaName}` (e.g., `areas/storage/src/AzureMcp.Storage`)
- **Tests** go in `areas/{area-name}/tests`, divided into UnitTests and LiveTests:
	- `areas/{area-name}/tests/AzureMcp.{AreaName}.UnitTests`
	- `areas/{area-name}/tests/AzureMcp.{AreaName}.LiveTests`

This keeps all code, options, models, and tests for an area together. See `areas/storage` for a reference implementation.

## Command Architecture

1. **Command Interface**
	- `IBaseCommand` serves as the root interface with core command capabilities:
		- `Name`: Command name for CLI display
		- `Description`: Detailed command description
		- `Title`: Human-readable command title
		- `GetCommand()`: Retrieves System.CommandLine command definition
		- `ExecuteAsync()`: Executes command logic
		- `Validate()`: Validates command inputs
2. **Command Hierarchy** All commands must implement the hierarchy pattern:
	```
	IBaseCommand
	└── BaseCommand
	    └── GlobalCommand<TOptions>
	        └── SubscriptionCommand<TOptions>
	            └── Service-specific base commands (e.g., BaseSqlCommand)
	                └── Resource-specific commands (e.g., SqlIndexRecommendCommand)
	```
	IMPORTANT:
	- Commands use primary constructors with ILogger injection
	- Classes are always sealed unless explicitly intended for inheritance
	- Commands inheriting from SubscriptionCommand must handle subscription parameters
	- Service-specific base commands should add service-wide options
	- Commands return `ToolMetadata` property to define their behavioral characteristics
3. **Command Pattern** Commands follow the Model-Context-Protocol (MCP) pattern with this naming convention:
	```
	azmcp <azure service> <resource> <operation>
	```
	Example: `azmcp storage container list`
	Where:
	- `azure service`: Azure service name (lowercase, e.g., storage, cosmos, kusto)
	- `resource`: Resource type (singular noun, lowercase)
	- `operation`: Action to perform (verb, lowercase)
	Each command is:
	- In code, to avoid ambiguity between service classes and Azure services, we refer to Azure services as Areas
	- Registered in the RegisterCommands method of its area's `areas/{area-name}/src/AzureMcp.{AreaName}/{AreaName}Setup.cs` file
	- Organized in a hierarchy of command groups
	- Documented with a title, description and examples
	- Validated before execution
	- Returns a standardized response format
	**IMPORTANT**: Command group names cannot contain underscores. Use camelCase or concatenated names or dash separator instead:
	- ✅ Good: `new CommandGroup("entraadmin", "Entra admin operations")`
	- ✅ Good: `new CommandGroup("resourcegroup", "Resource group operations")`
	- ✅ Good:`new CommandGroup("entra-admin", "Entra admin operations")`
	- ❌ Bad: `new CommandGroup("entra_admin", "Entra admin operations")`
	**AVOID ANTI-PATTERNS**: When designing commands, avoid mixing resource names with operations in a single command. Instead, use proper command group hierarchy:
	- ✅ Good: `azmcp postgres server param set` (command groups: server → param, operation: set)
	- ❌ Bad: `azmcp postgres server setparam` (mixed operation `setparam` at same level as resource operations)
	- ✅ Good: `azmcp storage container permission set`
	- ❌ Bad: `azmcp storage container setpermission`
	This pattern improves discoverability, maintains consistency, and allows for better grouping of related operations.

### Required Files

A complete command requires:

1. OptionDefinitions static class: `areas/{area-name}/src/AzureMcp.{AreaName}/Options/{AreaName}OptionDefinitions.cs`
2. Options class: `areas/{area-name}/src/AzureMcp.{AreaName}/Options/{Resource}/{Operation}Options.cs`
3. Command class: `areas/{area-name}/src/AzureMcp.{AreaName}/Commands/{Resource}/{Resource}{Operation}Command.cs`
4. Service interface: `areas/{area-name}/src/AzureMcp.{AreaName}/Services/I{ServiceName}Service.cs`
5. Service implementation: `areas/{area-name}/src/AzureMcp.{AreaName}/Services/{ServiceName}Service.cs`
	- It's common for an area to have a single service class named after the area but some areas will have multiple service classes
6. Unit test: `areas/{area-name}/tests/AzureMcp.{AreaName}.UnitTests/{Resource}/{Resource}{Operation}CommandTests.cs`
7. Integration test: `areas/{area-name}/tests/AzureMcp.{AreaName}.LiveTests/{AreaName}CommandTests.cs`
8. Command registration in RegisterCommands(): `areas/{area-name}/src/AzureMcp.{AreaName}/{AreaName}Setup.cs`
9. Area registration in RegisterAreas(): `core/src/AzureMcp.Cli/Program.cs`
10. **Live test infrastructure** (if needed):
- Bicep template: `/areas/{area-name}/tests/test-resources.bicep`
- Optional post-deployment script: `/areas/{area-name}/tests/test-resources-post.ps1`

**IMPORTANT**: All command files and classes must follow the **ObjectVerb** naming pattern for consistency and discoverability:

**Pattern**: `{Resource}{SubResource}{Operation}Command`

**Examples**:

- ✅ `ServerListCommand` (Resource: Server, Operation: List)
- ✅ `ServerConfigGetCommand` (Resource: Server, SubResource: Config, Operation: Get)
- ✅ `ServerParamSetCommand` (Resource: Server, SubResource: Param, Operation: Set)
- ✅ `TableSchemaGetCommand` (Resource: Table, SubResource: Schema, Operation: Get)
- ✅ `DatabaseListCommand` (Resource: Database, Operation: List)

**Anti-patterns to avoid**:

- ❌ `GetConfigCommand` (missing resource prefix)
- ❌ `GetParamCommand` (missing resource prefix)
- ❌ `GetSchemaCommand` (missing resource prefix)

**Apply this pattern to**:

- Command class names: `ServerConfigGetCommand`, `ServerParamSetCommand`
- Options class names: `ServerConfigGetOptions`, `ServerParamSetOptions`
- Test class names: `ServerConfigGetCommandTests`, `ServerParamSetCommandTests`
- File names: `ServerConfigGetCommand.cs`, `ServerParamSetOptions.cs`

This convention ensures:

- Clear identification of the resource being operated on
- Logical grouping of related operations
- Consistent file organization and naming
- Better IDE intellisense and code navigation
- Easier maintenance and discovery

**IMPORTANT**: If implementing a new area, you must also ensure:

- The Azure Resource Manager package is added to `Directory.Packages.props` first
- Models, base commands, and option definitions follow the established patterns
- JSON serialization context includes all new model types
- Service registration in the area setup ConfigureServices method
- **Live test infrastructure**: Add Bicep template to `/areas/{area-name}/tests`
- **Test resource deployment**: Ensure resources are properly configured with RBAC for test application
- **Resource naming**: Follow consistent naming patterns - many services use just `baseName`, while others may need suffixes for disambiguation (e.g., `{baseName}-suffix`)

## Implementation Guidelines

When creating commands that interact with Azure services, you'll need to:

**Package Management:**

- Add the appropriate Azure Resource Manager package to `Directory.Packages.props`
	- Example: `<PackageVersion Include="Azure.ResourceManager.Sql" Version="1.3.0" />`
- Add the package reference in `AzureMcp.{AreaName}.csproj`
	- Example: `<PackageReference Include="Azure.ResourceManager.Sql" />`

**Subscription Resolution:**

- Always use `ISubscriptionService.GetSubscription()` to resolve subscription ID or name
- Inject `ISubscriptionService` into your service constructor
- This handles both subscription IDs and subscription names automatically
- Example pattern:
```
public class MyService(ISubscriptionService subscriptionService, ITenantService tenantService)
    : BaseAzureService(tenantService), IMyService
{
    private readonly ISubscriptionService _subscriptionService = subscriptionService;

    public async Task<MyResource> GetResourceAsync(string subscription, ...)
    {
        var subscriptionResource = await _subscriptionService.GetSubscription(subscription, null, retryPolicy);
        // Use subscriptionResource instead of creating one manually
    }
}
```

**API Pattern Discovery:**

- Study existing services (e.g., Postgres, Redis) to understand resource access patterns
- Use resource collections correctly: `.GetSqlServers().GetAsync(serverName)` not `.GetSqlServerAsync(serverName, cancellationToken)`
- Check Azure SDK documentation for correct method signatures and property names

**Common Azure Resource Manager Patterns:**

```
// Correct pattern for subscription resolution and resource access
var subscriptionResource = await _subscriptionService.GetSubscription(subscription, tenant, retryPolicy);

var resourceGroupResource = await subscriptionResource
    .GetResourceGroupAsync(resourceGroup, cancellationToken);

var sqlServerResource = await resourceGroupResource.Value
    .GetSqlServers()
    .GetAsync(serverName);

var databaseResource = await sqlServerResource.Value
    .GetSqlDatabases()
    .GetAsync(databaseName);
```

**Property Access Issues:**

- Azure SDK property names may differ from expected names (e.g., `CreatedOn` not `CreationDate`)
- Check actual property availability using IntelliSense or SDK documentation
- Some properties are objects that need `.ToString()` conversion (e.g., `Location.ToString()`)
- Be aware of nullable properties and use appropriate null checks

**Compilation Error Resolution:**

- When you see `cannot convert from 'System.Threading.CancellationToken' to 'string'`, check method parameter order
- For `'SqlDatabaseData' does not contain a definition for 'X'`, verify property names in the actual SDK types
- Use existing service implementations as reference for correct property access patterns
```
public class {Resource}{Operation}Options : Base{Area}Options
{
    // Only add properties not in base class
    public string? NewOption { get; set; }
}
```

IMPORTANT:

- Inherit from appropriate base class (Base{Area}Options, GlobalOptions, etc.)
- Never redefine properties from base classes
- Make properties nullable if not required
- Use consistent parameter names across services:
	- **CRITICAL**: Always use `subscription` (never `subscriptionId`) for subscription parameters - this allows the parameter to accept both subscription IDs and subscription names, which are resolved internally by `ISubscriptionService.GetSubscription()`
	- Use `resourceGroup` instead of `resourceGroupName`
	- Use singular nouns for resource names (e.g., `server` not `serverName`)
	- **Remove unnecessary "-name" suffixes**: Use `--account` instead of `--account-name`, `--container` instead of `--container-name`, etc. Only keep "-name" when it provides necessary disambiguation (e.g., `--subscription-name` to distinguish from global `--subscription`)
	- Keep parameter names consistent with Azure SDK parameters when possible
	- If services share similar operations (e.g., ListDatabases), use the same parameter order and names
```
public sealed class {Resource}{Operation}Command(ILogger<{Resource}{Operation}Command> logger)
    : Base{Area}Command<{Resource}{Operation}Options>
{
    private const string CommandTitle = "Human Readable Title";
    private readonly ILogger<{Resource}{Operation}Command> _logger = logger;

    // Define options from OptionDefinitions
    private readonly Option<string> _newOption = {Area}OptionDefinitions.NewOption;

    public override string Name => "operation";

    public override string Description =>
        """
        Detailed description of what the command does.
        Returns description of return format.
          Required options:
        - list required options
        """;

    public override string Title => CommandTitle;

    public override ToolMetadata Metadata => new()
    {
        Destructive = false,    // Set to true for commands that modify resources
        ReadOnly = true         // Set to false for commands that modify resources  
    };

    protected override void RegisterOptions(Command command)
    {
        base.RegisterOptions(command);
        command.AddOption(_newOption);
    }

    protected override {Resource}{Operation}Options BindOptions(ParseResult parseResult)
    {
        var options = base.BindOptions(parseResult);
        options.NewOption = parseResult.GetValueForOption(_newOption);
        return options;
    }

    public override async Task<CommandResponse> ExecuteAsync(CommandContext context, ParseResult parseResult)
    {
        var options = BindOptions(parseResult);

        try
        {
            // Required validation step
            if (!Validate(parseResult.CommandResult, context.Response).IsValid)
            {
                return context.Response;
            }

            context.Activity?.WithSubscriptionTag(options);

            // Get the appropriate service from DI
            var service = context.GetService<I{Area}Service>();

            // Call service operation(s) with required parameters
            var results = await service.{Operation}(
                options.RequiredParam!,  // Required parameters end with !
                options.OptionalParam,   // Optional parameters are nullable
                options.Subscription!,   // From SubscriptionCommand
                options.RetryPolicy);    // From GlobalCommand

            // Set results if any were returned
            context.Response.Results = results?.Count > 0 ?
                ResponseResult.Create(
                    new {Operation}CommandResult(results),
                    {Area}JsonContext.Default.{Operation}CommandResult) :
                null;
        }
        catch (Exception ex)
        {
            // Log error with all relevant context
            _logger.LogError(ex,
                "Error in {Operation}. Required: {Required}, Optional: {Optional}, Options: {@Options}",
                Name, options.RequiredParam, options.OptionalParam, options);
            HandleException(context, ex);
        }

        return context.Response;
    }

    // Implementation-specific error handling
    protected override string GetErrorMessage(Exception ex) => ex switch
    {
        Azure.RequestFailedException reqEx when reqEx.Status == 404 =>
            "Resource not found. Verify the resource exists and you have access.",
        Azure.RequestFailedException reqEx when reqEx.Status == 403 =>
            $"Authorization failed accessing the resource. Details: {reqEx.Message}",
        Azure.RequestFailedException reqEx => reqEx.Message,
        _ => base.GetErrorMessage(ex)
    };

    protected override int GetStatusCode(Exception ex) => ex switch
    {
        Azure.RequestFailedException reqEx => reqEx.Status,
        _ => base.GetStatusCode(ex)
    };

    // Strongly-typed result records
    internal record {Resource}{Operation}CommandResult(List<ResultType> Results);
}

### 4. Service Interface and Implementation

Each area has its own service interface that defines the methods that commands will call. The interface will have an implementation that contains the actual logic.

\`\`\`csharp
public interface I<Area>Service
{
    ...
}
```
```
public class <Area>Service(ISubscriptionService subscriptionService, ITenantService tenantService, ICacheService cacheService) : BaseAzureService(tenantService), I<Area>Service
{
   ...
}
```

All interface methods should follow consistent formatting with proper line breaks and parameter alignment:

```
// Correct formatting - parameters aligned with line breaks
Task<List<string>> GetStorageAccounts(
    string subscription,
    string? tenant = null,
    RetryPolicyOptions? retryPolicy = null);

// Incorrect formatting - all parameters on single line
Task<List<string>> GetStorageAccounts(string subscription, string? tenant = null, RetryPolicyOptions? retryPolicy = null);
```

**Formatting Rules:**

- Parameters indented and aligned
- Add blank lines between method declarations for visual separation
- Maintain consistent indentation across all methods in the interface

Each area has its own hierarchy of base command classes that inherit from `GlobalCommand` or `SubscriptionCommand`. Service classes that work with Azure resources should inject `ISubscriptionService` for subscription resolution. For example:

```
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

using System.Diagnostics.CodeAnalysis;
using AzureMcp.Core.Commands;
using AzureMcp.Core.Commands.Subscription;
using AzureMcp.{Area}.Options;

namespace AzureMcp.{Area}.Commands;

// Base command for all service commands (if no members needed, use concise syntax)
public abstract class Base{Area}Command<
    [DynamicallyAccessedMembers(TrimAnnotations.CommandAnnotations)] TOptions>
    : SubscriptionCommand<TOptions> where TOptions : Base{Area}Options, new();

// Base command for all service commands (if members are needed, use full syntax)
public abstract class Base{Area}Command<
    [DynamicallyAccessedMembers(TrimAnnotations.CommandAnnotations)] TOptions>
    : SubscriptionCommand<TOptions> where TOptions : Base{Area}Options, new()
{
    protected readonly Option<string> _commonOption = {Area}OptionDefinitions.CommonOption;
    protected readonly Option<string> _resourceGroupOption = OptionDefinitions.Common.ResourceGroup;
    protected virtual bool RequiresResourceGroup => true;

    protected override void RegisterOptions(Command command)
    {
        base.RegisterOptions(command);
        command.AddOption(_commonOption);

        // Add resource group option if required
        if (RequiresResourceGroup)
        {
            command.AddOption(_resourceGroupOption);
        }
    }

    protected override TOptions BindOptions(ParseResult parseResult)
    {
        var options = base.BindOptions(parseResult);
        options.CommonOption = parseResult.GetValueForOption(_commonOption);

        if (RequiresResourceGroup)
        {
            options.ResourceGroup = parseResult.GetValueForOption(_resourceGroupOption);
        }

        return options;
    }
}

// Service implementation example with subscription resolution
public class {Area}Service(ISubscriptionService subscriptionService, ITenantService tenantService)
    : BaseAzureService(tenantService), I{Area}Service
{
    private readonly ISubscriptionService _subscriptionService = subscriptionService ?? throw new ArgumentNullException(nameof(subscriptionService));

    public async Task<{Resource}> GetResourceAsync(string subscription, string resourceGroup, string resourceName, RetryPolicyOptions? retryPolicy)
    {
        // Always use subscription service for resolution
        var subscriptionResource = await _subscriptionService.GetSubscription(subscription, null, retryPolicy);

        var resourceGroupResource = await subscriptionResource
            .GetResourceGroupAsync(resourceGroup, cancellationToken);
        // Continue with resource access...
    }
}
```

Unit tests follow a standardized pattern that tests initialization, validation, and execution:

```
public class {Resource}{Operation}CommandTests
{
    private readonly IServiceProvider _serviceProvider;
    private readonly I{Area}Service _service;
    private readonly ILogger<{Resource}{Operation}Command> _logger;
    private readonly {Resource}{Operation}Command _command;
    private readonly CommandContext _context;
    private readonly Parser _parser;

    public {Resource}{Operation}CommandTests()
    {
        _service = Substitute.For<I{Area}Service>();
        _logger = Substitute.For<ILogger<{Resource}{Operation}Command>>();

        var collection = new ServiceCollection().AddSingleton(_service);
        _serviceProvider = collection.BuildServiceProvider();
        _command = new(_logger);
        _context = new(_serviceProvider);
        _parser = new(_command.GetCommand());
    }

    [Fact]
    public void Constructor_InitializesCommandCorrectly()
    {
        var command = _command.GetCommand();
        Assert.Equal("operation", command.Name);
        Assert.NotNull(command.Description);
        Assert.NotEmpty(command.Description);
    }

    [Theory]
    [InlineData("--required value", true)]
    [InlineData("--optional-param value --required value", true)]
    [InlineData("", false)]
    public async Task ExecuteAsync_ValidatesInputCorrectly(string args, bool shouldSucceed)
    {
        // Arrange
        if (shouldSucceed)
        {
            _service.{Operation}(Arg.Any<string>(), Arg.Any<string>(), Arg.Any<RetryPolicyOptions>())
                .Returns(new List<ResultType>());
        }

        var parseResult = _parser.Parse(args.Split(' ', StringSplitOptions.RemoveEmptyEntries));

        // Act
        var response = await _command.ExecuteAsync(_context, parseResult);

        // Assert
        Assert.Equal(shouldSucceed ? 200 : 400, response.Status);
        if (shouldSucceed)
        {
            Assert.NotNull(response.Results);
            Assert.Equal("Success", response.Message);
        }
        else
        {
            Assert.Contains("required", response.Message.ToLower());
        }
    }

    [Fact]
    public async Task ExecuteAsync_HandlesServiceErrors()
    {
        // Arrange
        _service.{Operation}(Arg.Any<string>(), Arg.Any<string>(), Arg.Any<RetryPolicyOptions>())
            .Returns(Task.FromException<List<ResultType>>(new Exception("Test error")));

        var parseResult = _parser.Parse(["--required", "value"]);

        // Act
        var response = await _command.ExecuteAsync(_context, parseResult);

        // Assert
        Assert.Equal(500, response.Status);
        Assert.Contains("Test error", response.Message);
        Assert.Contains("troubleshooting", response.Message);
    }
}
```

Integration tests inherit from `CommandTestsBase` and use test fixtures:

```
public class {Area}CommandTests(LiveTestFixture liveTestFixture, ITestOutputHelper output)
    : CommandTestsBase(liveTestFixture, output), IClassFixture<LiveTestFixture>
{
    [Theory]
    [InlineData(AuthMethod.Credential)]
    [InlineData(AuthMethod.Key)]
    public async Task Should_{Operation}_{Resource}_WithAuth(AuthMethod authMethod)
    {
        // Arrange
        var result = await CallToolAsync(
            "azmcp_{area}_{resource}_{operation}",
            new()
            {
                { "subscription", Settings.Subscription },
                { "resource-group", Settings.ResourceGroup },
                { "auth-method", authMethod.ToString().ToLowerInvariant() }
            });

        // Assert
        var items = result.AssertProperty("items");
        Assert.Equal(JsonValueKind.Array, items.ValueKind);

        // Check results format
        foreach (var item in items.EnumerateArray())
        {
            Assert.True(item.TryGetProperty("name", out _));
            Assert.True(item.TryGetProperty("type", out _));
        }
    }

    [Theory]
    [InlineData("--invalid-param")]
    [InlineData("--subscription invalidSub")]
    public async Task Should_Return400_WithInvalidInput(string args)
    {
        var result = await CallToolAsync(
            $"azmcp_{area}_{resource}_{operation} {args}");

        Assert.Equal(400, result.GetProperty("status").GetInt32());
        Assert.Contains("required",
            result.GetProperty("message").GetString()!.ToLower());
    }
}
```

**IMPORTANT**: Command group names cannot contain underscores. Use camelCase or concatenated names or dash separator instead:

- ✅ Good: `"entraadmin"`, `"resourcegroup"`, `"storageaccount"`, `"entra-admin"`
- ❌ Bad: `"entra_admin"`, `"resource_group"`, `"storage_account"`

The area list in should `RegisterAreas()` should stay sorted alphabetically.

## Error Handling

Commands in Azure MCP follow a standardized error handling approach using the base `HandleException` method inherited from `BaseCommand`. Here are the key aspects:

The base implementation handles common status codes:

Error messages should be user-actionable and help debug issues:

The base `HandleException` combines status, message and details:

```
protected virtual void HandleException(CommandContext context, Exception ex)
{
    // Create a strongly typed exception result
    var result = new ExceptionResult(
        Message: ex.Message,
        StackTrace: ex.StackTrace,
        Type: ex.GetType().Name);

    response.Status = GetStatusCode(ex);
    // Add link to troubleshooting guide
    response.Message = GetErrorMessage(ex) +
        ". To mitigate this issue, please refer to the troubleshooting guidelines at https://aka.ms/azmcp/troubleshooting.";
    response.Results = ResponseResult.Create(
        result, JsonSourceGenerationContext.Default.ExceptionResult);
}
```

Commands should override error handlers to add service-specific mappings:

```
protected override string GetErrorMessage(Exception ex) => ex switch
{
    // Add service-specific cases
    ResourceNotFoundException =>
        "Resource not found. Verify name and permissions.",
    ServiceQuotaExceededException =>
        "Service quota exceeded. Request quota increase.",
    _ => base.GetErrorMessage(ex) // Fall back to base implementation
};
```

Always log errors with relevant context information:

```
catch (Exception ex)
{
    _logger.LogError(ex,
        "Error in {Operation}. Resource: {Resource}, Options: {@Options}",
        Name, resourceId, options);
    HandleException(context.Response, ex);
}
```
1. **Authentication/Authorization**
	- Azure credential expiry
	- Missing RBAC permissions
	- Invalid connection strings
2. **Validation**
	- Missing required parameters
	- Invalid parameter formats
	- Conflicting options
3. **Resource State**
	- Resource not found
	- Resource locked/in use
	- Invalid resource state
4. **Service Limits**
	- Throttling/rate limits
	- Quota exceeded
	- Service capacity
5. **Network/Connectivity**
	- Service unavailable
	- Request timeouts
	- Network failures

## Testing Requirements

### Unit Tests

Core test cases for every command:

```
[Theory]
[InlineData("", false, "Missing required options")]  // Validation
[InlineData("--param invalid", false, "Invalid format")] // Input format
[InlineData("--param value", true, null)]  // Success case
public async Task ExecuteAsync_ValidatesInput(
    string args, bool shouldSucceed, string expectedError)
{
    var response = await ExecuteCommand(args);
    Assert.Equal(shouldSucceed ? 200 : 400, response.Status);
    if (!shouldSucceed)
        Assert.Contains(expectedError, response.Message);
}

[Fact]
public async Task ExecuteAsync_HandlesServiceError()
{
    // Arrange
    _service.Operation()
        .Returns(Task.FromException(new ServiceException("Test error")));

    // Act
    var response = await ExecuteCommand("--param value");

    // Assert
    Assert.Equal(500, response.Status);
    Assert.Contains("Test error", response.Message);
    Assert.Contains("troubleshooting", response.Message);
}
```

**Running Tests Efficiently:**When developing new commands, run only your specific tests to save time:

```
# Run all tests from the test project directory:
pushd ./areas/your-area/tests/AzureMcp.YourArea.UnitTests  #or .LiveTests

# Run only tests for your specific command class
dotnet test --filter "FullyQualifiedName~YourCommandNameTests" --verbosity normal

# Example: Run only SQL AD Admin tests
dotnet test --filter "FullyQualifiedName~EntraAdminListCommandTests" --verbosity normal

# Run all tests for a specific area
dotnet test --verbosity normal
```

### Integration Tests

Areas requiring test resource deployment should add a bicep template, `tests/test-resources.bicep`, to their area directory. If additional logic needs to be performed after resource deployment, but before any live tests are run, add a `test-resources-post.ps1` in the same directory. See `/areas/storage/tests/test-resources.bicep` and `/areas/storage/tests/test-resources-post.ps1` for canonical examples.

**1\. Create Area Bicep Template (`/areas/{area-name}/tests/test-resources.bicep`)**

Follow this pattern for your area's infrastructure:

```
targetScope = 'resourceGroup'

@minLength(3)
@maxLength(17)  // Adjust based on service naming limits
@description('The base resource name. Service names have specific length restrictions.')
param baseName string = resourceGroup().name

@description('The client OID to grant access to test resources.')
param testApplicationOid string = deployer().objectId

// The test infrastructure will only provide baseName and testApplicationOid.
// Any additional parameters are for local deployments only and require default values.

@description('The location of the resource. By default, this is the same as the resource group.')
param location string = resourceGroup().location

// Main service resource
resource serviceResource 'Microsoft.{Provider}/{resourceType}@{apiVersion}' = {
  name: baseName
  location: location
  properties: {
    // Service-specific properties
  }

  // Child resources (databases, containers, etc.)
  resource testResource 'childResourceType@{apiVersion}' = {
    name: 'test{resource}'
    properties: {
      // Test resource properties
    }
  }
}

// Role assignment for test application
resource serviceRoleDefinition 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: subscription()
  // Use appropriate built-in role for your service
  // See https://learn.microsoft.com/azure/role-based-access-control/built-in-roles
  name: '{role-guid}'
}

resource appServiceRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(serviceRoleDefinition.id, testApplicationOid, serviceResource.id)
  scope: serviceResource
  properties: {
    principalId: testApplicationOid
    roleDefinitionId: serviceRoleDefinition.id
    description: '{Role Name} for testApplicationOid'
  }
}

// Outputs for test consumption
output serviceResourceName string = serviceResource.name
output testResourceName string = serviceResource::testResource.name
// Add other outputs as needed for tests
```

**Key Bicep Template Requirements:**

- Use `baseName` parameter with appropriate length restrictions
- Include `testApplicationOid` for RBAC assignments
- Deploy test resources (databases, containers, etc.) needed for integration tests
- Assign appropriate built-in roles to the test application
- Output resource names and identifiers for test consumption

**Cost and Resource Considerations:**

- Use minimal SKUs (Basic, Standard S0, etc.) for cost efficiency
- Deploy only resources needed for command testing
- Consider using shared resources where possible
- Set appropriate retention policies and limits
- Use resource naming that clearly identifies test purposes

**Common Resource Naming Patterns:**

- Deployments are on a per-area basis. Name collisions should not occur across area templates.
- Main service: `baseName` (most common, e.g., `mcp12345`) or `{baseName}{suffix}` if disambiguation needed
- Child resources: `test{resource}` (e.g., `testdb`, `testcontainer`)
- Follow Azure naming conventions and length limits
- Ensure names are unique within resource group scope
- Check existing `test-resources.bicep` files for consistent patterns

**2\. Optional: Post-Deployment Script (`/area/{area-name}/tests/test-resources-post.ps1`)**

Create if additional setup is needed after resource deployment:

```
#!/usr/bin/env pwsh

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

#Requires -Version 6.0
#Requires -PSEdition Core

[CmdletBinding()]
param (
    [Parameter(Mandatory)]
    [hashtable] $DeploymentOutputs,

    [Parameter(Mandatory)]
    [hashtable] $AdditionalParameters
)

Write-Host "Running {Area} post-deployment setup..."

try {
    # Extract outputs from deployment
    $serviceName = $DeploymentOutputs['{area}']['serviceResourceName']['value']
    $resourceGroup = $AdditionalParameters['ResourceGroupName']

    # Perform additional setup (e.g., create sample data, configure settings)
    Write-Host "Setting up test data for $serviceName..."

    # Example: Run Azure CLI commands for additional setup
    # az {service} {operation} --name $serviceName --resource-group $resourceGroup

    Write-Host "{Area} post-deployment setup completed successfully."
}
catch {
    Write-Error "Failed to complete {Area} post-deployment setup: $_"
    throw
}
```

**4\. Update Live Tests to Use Deployed Resources**

Integration tests should use the deployed infrastructure:

```
[Trait("Area", "{Area}")]
[Trait("Category", "Live")]
public class {Area}CommandTests(LiveTestFixture liveTestFixture, ITestOutputHelper output)
    : CommandTestsBase(liveTestFixture, output), IClassFixture<LiveTestFixture>
{
    [Fact]
    public async Task Should_Get{Resource}_Successfully()
    {
        // Use the deployed test resources
        var serviceName = Settings.ResourceBaseName;
        var resourceName = "test{resource}";

        var result = await CallToolAsync(
            "azmcp_{area}_{resource}_show",
            new()
            {
                { "subscription", Settings.SubscriptionId },
                { "resource-group", Settings.ResourceGroupName },
                { "service-name", serviceName },
                { "resource-name", resourceName }
            });

        // Verify successful response
        var resource = result.AssertProperty("{resource}");
        Assert.Equal(JsonValueKind.Object, resource.ValueKind);

        // Verify resource properties
        var name = resource.GetProperty("name").GetString();
        Assert.Equal(resourceName, name);
    }

    [Theory]
    [InlineData("--invalid-param", new string[0])]
    [InlineData("--subscription", new[] { "invalidSub" })]
    [InlineData("--subscription", new[] { "sub", "--resource-group", "rg" })]  // Missing required params
    public async Task Should_Return400_WithInvalidInput(string firstArg, string[] remainingArgs)
    {
        var allArgs = new[] { firstArg }.Concat(remainingArgs);
        var argsString = string.Join(" ", allArgs);

        var result = await CallToolAsync(
            "azmcp_{area}_{resource}_show",
            new()
            {
                { "args", argsString }
            });

        // Should return validation error
        Assert.NotEqual(200, result.Status);
    }
}
```

**5\. Deploy and Test Resources**

Use the deployment script with your area:

```
# Deploy test resources for your area
./eng/scripts/Deploy-TestResources.ps1 -Areas "{Area}"

# Run live tests
dotnet test --filter "Category=Live&Area={Area}"
```

Live test scenarios should include:

```
[Theory]
[InlineData(AuthMethod.Credential)]  // Default auth
[InlineData(AuthMethod.Key)]         // Key based auth
public async Task Should_HandleAuth(AuthMethod method)
{
    var result = await CallCommand(new()
    {
        { "auth-method", method.ToString() }
    });
    // Verify auth worked
    Assert.Equal(200, result.Status);
}

[Theory]
[InlineData("--invalid-value")]    // Bad input
[InlineData("--missing-required")] // Missing params
public async Task Should_Return400_ForInvalidInput(string args)
{
    var result = await CallCommand(args);
    Assert.Equal(400, result.Status);
    Assert.Contains("validation", result.Message.ToLower());
}
```

If your live test class needs to implement `IAsyncLifetime` or override `Dispose`, you must call `Dispose` on your base class:

```
public class MyCommandTests(LiveTestFixture liveTestFixture, ITestOutputHelper output)
    : CommandTestsBase(liveTestFixture, output),
    IClassFixture<LiveTestFixture>, IAsyncLifetime
{
    public ValueTask DisposeAsync()
    {
        base.Dispose();
        return ValueTask.CompletedTask;
    }
}
```

Failure to call `base.Dispose()` will prevent request and response data from `CallCommand` from being written to failing test results.

## Best Practices

1. Command Structure:
	- Make command classes sealed
	- Use primary constructors
	- Follow exact namespace hierarchy
	- Register all options in RegisterOptions
	- Handle all exceptions
2. Error Handling:
	- Return 400 for validation errors
	- Return 401 for authentication failures
	- Return 500 for unexpected errors
	- Return service-specific status codes from RequestFailedException
	- Add troubleshooting URL to error messages
	- Log errors with context information
	- Override GetErrorMessage and GetStatusCode for custom error handling
3. Response Format:
	- Always set Results property for success
	- Set Status and Message for errors
	- Use consistent JSON property names
	- Follow existing response patterns
4. Documentation:
	- Clear command description without repeating the service name (e.g., use "List and manage clusters" instead of "AKS operations - List and manage AKS clusters")
	- List all required options
	- Describe return format
	- Include examples in description
	- **Maintain alphabetical sorting in e2eTestPrompts.md**: Insert new test prompts in correct alphabetical position by Tool Name within each service section
5. Tool Description Quality Validation:
	- Test your command descriptions for quality using the validation tool before submitting:
		- **Single prompt validation** (test one description against one prompt):
			```
			cd eng/tools/ToolDescriptionConfidenceScore
			dotnet run -- --validate --tool-description "Your command description here" --prompt "typical user request"
			```
		- **Multiple prompt validation** (test one description against multiple prompts):
			```
			dotnet run -- --validate \
			--tool-description "Lists all storage accounts in a subscription" \
			--prompt "show me my storage accounts" \
			--prompt "list storage accounts" \
			--prompt "what storage do I have"
			```
		- **Custom tools and prompts files** (use your own files for comprehensive testing):
			```
			# Prompts:
			# Use markdown format (same as e2eTests/e2eTestPrompts.md):
			dotnet run -- --prompts-file my-prompts.md
			# Use JSON format:
			dotnet run -- --prompts-file my-prompts.json
			# Tools:
			# Use JSON format (same as eng/tools/ToolDescriptionConfidenceScore/tools.json):
			dotnet run -- --tools-file my-tools.json
			# Combine both:
			# Use custom tools and prompts files together:
			dotnet run -- --tools-file my-tools.json --prompts-file my-prompts.md
			```
	- Quality assessment guidelines:
		- Aim for your description to rank in the top 3 results (GOOD or EXCELLENT rating)
		- Test with multiple different prompts that users might use
		- Consider common synonyms and alternative phrasings in your descriptions
		- If validation shows POOR results or a confidence score of < 0.4, refine your description and test again
	- Custom prompts file formats:
		- **Markdown format**: Use same table format as `e2eTests/e2eTestPrompts.md`:
			```
			| Tool Name | Test Prompt |
			|:----------|:----------|
			| azmcp-your-command | Your test prompt |
			| azmcp-your-command | Another test prompt |
			```
		- **JSON format**: Tool name as key, array of prompts as value:
			```
			{
			    "azmcp-your-command": [
			    "Your test prompt",
			    "Another test prompt"
			    ]
			}
			```
	- Custom tools file format:
		- Use the JSON format returned by calling the server command `azmcp-tools-list` or found in `eng/tools/ToolDescriptionConfidenceScore/tools.json`.
6. Live Test Infrastructure:
	- Use minimal resource configurations for cost efficiency
	- Follow naming conventions: `baseName` (most common) or `{baseName}-{area}` if needed
	- Include proper RBAC assignments for test application
	- Output all necessary identifiers for test consumption
	- Use appropriate Azure service API versions
	- Consider resource location constraints and availability
1. Do not:
	- **CRITICAL**: Use `subscriptionId` as parameter name - Always use `subscription` to support both IDs and names
	- Redefine base class properties in Options classes
	- Skip base.RegisterOptions() call
	- Skip base.Dispose() call
	- Use hardcoded option strings
	- Return different response formats
	- Leave command unregistered
	- Skip error handling
	- Miss required tests
	- Deploy overly expensive test resources
	- Forget to assign RBAC permissions to test application
	- Hard-code resource names in live tests
	- Use dashes in command group names
2. Always:
	- Create a static {Area}OptionDefinitions class for the area
	- Use OptionDefinitions for options
	- Follow exact file structure
	- Implement all base members
	- Add both unit and integration tests
	- Register in CommandFactory
	- Handle all error cases
	- Use primary constructors
	- Make command classes sealed
	- Include live test infrastructure for Azure services
	- Use consistent resource naming patterns (check existing `test-resources.bicep` files)
	- Output resource identifiers from Bicep templates
	- Use concatenated all lowercase names for command groups (no dashes)

**Issue: Subscription not properly resolved**

- **Cause**: Using direct ARM client creation instead of subscription service
- **Solution**: Always inject and use `ISubscriptionService.GetSubscription()`
- **Fix**: Replace manual subscription resource creation with service call
- **Pattern**:
```
// Wrong - manual creation
var armClient = await CreateArmClientAsync(null, retryPolicy);
var subscriptionResource = armClient.GetSubscriptionResource(new ResourceIdentifier($"/subscriptions/{subscription}"));

// Correct - use service
var subscriptionResource = await _subscriptionService.GetSubscription(subscription, null, retryPolicy);
```

**Issue: `cannot convert from 'System.Threading.CancellationToken' to 'string'`**

- **Cause**: Wrong parameter order in resource manager method calls
- **Solution**: Check method signatures; many Azure SDK methods don't take CancellationToken as second parameter
- **Fix**: Use `.GetAsync(resourceName)` instead of `.GetAsync(resourceName, cancellationToken)`

**Issue: `'SqlDatabaseData' does not contain a definition for 'CreationDate'`**

- **Cause**: Property names in Azure SDK differ from expected/documented names
- **Solution**: Use IntelliSense to explore actual property names
- **Common fixes**:
	- `CreationDate` → `CreatedOn`
	- `EarliestRestoreDate` → `EarliestRestoreOn`
	- `Edition` → `CurrentSku?.Name`

**Issue: `Operator '?' cannot be applied to operand of type 'AzureLocation'`**

- **Cause**: Some Azure SDK types are structs, not nullable reference types
- **Solution**: Convert to string: `Location.ToString()` instead of `Location?.Name`

**Issue: Wrong resource access pattern**

- **Problem**: Using `.GetSqlServerAsync(name, cancellationToken)`
- **Solution**: Use resource collections: `.GetSqlServers().GetAsync(name)`
- **Pattern**: Always access through collections, not direct async methods

**Issue: Bicep template validation fails**

- **Cause**: Invalid parameter constraints, missing required properties, or API version issues
- **Solution**: Use `az bicep build --file areas/{area-name}/tests/test-resources.bicep` to validate template
- **Fix**: Check Azure Resource Manager template reference for correct syntax and required properties

**Issue: Live tests fail with "Resource not found"**

- **Cause**: Test resources not deployed or wrong naming pattern used
- **Solution**: Verify resource deployment and naming in Azure portal
- **Fix**: Ensure live tests use `Settings.ResourceBaseName` pattern for resource names (or appropriate service-specific pattern)

**Issue: Permission denied errors in live tests**

- **Cause**: Missing or incorrect RBAC assignments in Bicep template
- **Solution**: Verify role assignment scope and principal ID
- **Fix**: Check that `testApplicationOid` is correctly passed and role definition GUID is valid

**Issue: Deployment fails with template validation errors**

- **Cause**: Parameter constraints, resource naming conflicts, or invalid configurations
- **Solution**:
	- Review deployment logs and error messages
	- Use `./eng/scripts/Deploy-TestResources.ps1 -Area {area-name} -Debug` for verbose deployment logs including resource provider errors.
- **Common fixes**:
	- Adjust `@minLength` / `@maxLength` for service naming limits
	- Ensure unique resource names within scope
	- Use supported API versions for resource types
	- Verify location support for specific resource types

**Issue: High deployment costs during testing**

- **Cause**: Using expensive SKUs or resource configurations
- **Solution**: Use minimal configurations for test resources
- **Best practices**:
	- SQL: Use Basic tier with small capacity
	- Storage: Use Standard LRS with minimal replication
	- Cosmos: Use serverless or minimal RU/s allocation
	- Always specify cost-effective options in Bicep templates

**Issue: HandleException parameter mismatch**

- **Cause**: Different base classes have different HandleException signatures
- **Solution**: Check base class implementation; use `HandleException(context.Response, ex)` not `HandleException(context, ex)`

**Issue: Missing AddSubscriptionInformation**

- **Cause**: Subscription commands need telemetry context
- **Solution**: Add `context.Activity?.WithSubscriptionTag(options);` or use `AddSubscriptionInformation(context.Activity, options);`

**Issue: Service not registered in DI**

- **Cause**: Forgot to register service in area setup
- **Solution**: Add `services.AddSingleton<IServiceInterface, ServiceImplementation>();` in ConfigureServices

**Issue: Wrong logger type in base command constructor**

- **Example**: `ILogger<BaseSqlCommand<TOptions>>` in `BaseDatabaseCommand`
- **Solution**: Use correct generic type: `ILogger<BaseDatabaseCommand<TOptions>>`

**Issue: Missing using statements for TrimAnnotations**

- **Solution**: Add `using AzureMcp.Core.Commands;` for `TrimAnnotations.CommandAnnotations`

## Checklist

Before submitting:

- Options class follows inheritance pattern
- Command class implements all required members
- Command uses proper OptionDefinitions
- Service interface and implementation complete
- Unit tests cover all paths
- Integration tests added
- Registered in CommandFactory
- Follows file structure exactly
- Error handling implemented
- Documentation complete
- No compiler warnings
- Tests pass (run specific tests: `dotnet test --filter "FullyQualifiedName~YourCommandTests"`)
- Build succeeds with `dotnet build`
- Code formatting applied with `dotnet format`
- Spelling check passes with `.\eng\common\spelling\Invoke-Cspell.ps1`
- **Remove unnecessary using statements from all C# files** (use IDE cleanup or `dotnet format analyzers`)
- Azure Resource Manager package added to both `Directory.Packages.props` and `AzureMcp.{Area}.csproj`
- All Azure SDK property names verified and correct
- Resource access patterns use collections (e.g., `.GetSqlServers().GetAsync()`)
- Subscription resolution uses `ISubscriptionService.GetSubscription()`
- Service constructor includes `ISubscriptionService` injection for Azure resources
- JSON serialization context includes all new model types
- Live test infrastructure created (`test-resources.bicep` template in `areas/{area-name}/tests`)
- Live test resource template test with `./eng/scripts/Deploy-TestResources.ps1 -Area {area-name}`
- RBAC permissions configured for test application in Bicep template
- Live tests use deployed resources via `Settings.ResourceBaseName` pattern
- Resource outputs defined in Bicep template for `test-resources-post.ps1` script consumption
- Fix formatting issues with `dotnet format ./AzureMcp.sln` and ensure no warnings

### Documentation Requirements

**REQUIRED**: All new commands must update the following documentation files:

- **CHANGELOG.md**: Add entry under "Unreleased" section describing the new command(s)
- **docs/azmcp-commands.md**: Add command documentation with description, syntax, parameters, and examples
- **README.md**: Update the supported services table and add example prompts demonstrating the new command(s) in the appropriate area section
- **eng/vscode/README.md**: Update the VSIX README with new service area (if applicable) and add sample prompts to showcase new command capabilities
- **e2eTests/e2eTestPrompts.md**: Add test prompts for end-to-end validation of the new command(s)

**Documentation Standards**:

- Use consistent command paths in all documentation (e.g., `azmcp sql db show`, not `azmcp sql database show`)
- Organize example prompts by service in README.md under service-specific sections (e.g., `### 🗄️ Azure SQL Database`)
- Place new commands in the appropriate area section, or create a new area section if needed
- Provide clear, actionable examples that users can run with placeholder values
- Include parameter descriptions and required vs optional indicators in azmcp-commands.md
- Keep CHANGELOG.md entries concise but descriptive of the capability added
- Add test prompts to e2eTestPrompts.md following the established naming convention and provide multiple prompt variations
- **eng/vscode/README.md Updates**: When adding new services or commands, update the VSIX README to maintain accurate service coverage and compelling sample prompts for marketplace visibility
- **IMPORTANT**: Maintain alphabetical sorting in e2eTestPrompts.md:
	- Service sections must be in alphabetical order by service name
	- Tool Names within each table must be sorted alphabetically
	- When adding new tools, insert them in the correct alphabetical position to maintain sort order

**README.md Table Formatting Standards**:

- Badge text must use the pattern `Install_{namespace}` (e.g., `Install_storage`, `Install_cosmos`)
- All badge URLs must use stable `vscode.dev` format with proper URL encoding
- Use blue badge color `#0098FF` consistently across all install buttons
- Service descriptions should be concise (under 50 characters), action-oriented, and end with a period
- Follow the pattern: "Manage/Query/Monitor \[what\] \[and/or additional context\]."
- Examples: "Manage storage accounts and blob data.", "Query AI Search services and indexes."
- Ensure proper URL encoding in badge links (e.g., `Azure%20Foundry` not `Azure%Foundry`)