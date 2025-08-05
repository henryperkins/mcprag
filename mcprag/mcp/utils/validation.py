"""Input validation framework for MCP tools."""

from typing import Any, Dict, List, Optional, Union, Type, get_origin, get_args
from dataclasses import dataclass
from enum import Enum
import re
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Field name that failed validation
            value: Value that failed validation
        """
        super().__init__(message)
        self.field = field
        self.value = value


@dataclass
class ValidationRule:
    """Base validation rule."""
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        """Validate a value.
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            
        Returns:
            Validated (potentially transformed) value
            
        Raises:
            ValidationError: If validation fails
        """
        raise NotImplementedError


@dataclass
class RequiredRule(ValidationRule):
    """Rule to ensure a field is present and not None."""
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            raise ValidationError(f"Field '{field_name}' is required", field_name, value)
        return value


@dataclass
class TypeRule(ValidationRule):
    """Rule to validate type."""
    
    expected_type: Type
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return None  # Allow None values unless RequiredRule is also applied
        if not isinstance(value, self.expected_type):
            raise ValidationError(
                f"Field '{field_name}' must be of type {self.expected_type.__name__}, got {type(value).__name__}",
                field_name, value
            )
        return value


@dataclass
class StringRule(ValidationRule):
    """Rule to validate strings."""
    
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return None  # Allow None values unless RequiredRule is also applied
        if not isinstance(value, str):
            raise ValidationError(f"Field '{field_name}' must be a string", field_name, value)
        
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(
                f"Field '{field_name}' must be at least {self.min_length} characters",
                field_name, value
            )
        
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(
                f"Field '{field_name}' must be at most {self.max_length} characters",
                field_name, value
            )
        
        if self.pattern and not re.match(self.pattern, value):
            raise ValidationError(
                f"Field '{field_name}' does not match required pattern",
                field_name, value
            )
        
        if self.allowed_values and value not in self.allowed_values:
            raise ValidationError(
                f"Field '{field_name}' must be one of {self.allowed_values}",
                field_name, value
            )
        
        return value.strip()


@dataclass
class NumberRule(ValidationRule):
    """Rule to validate numbers."""
    
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    number_type: Type = int
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if value is None:
            return None  # Allow None values unless RequiredRule is also applied
        
        # Try to convert to the expected number type
        try:
            if self.number_type == int:
                value = int(value)
            elif self.number_type == float:
                value = float(value)
            else:
                raise ValidationError(f"Unsupported number type: {self.number_type}", field_name, value)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Field '{field_name}' must be a valid {self.number_type.__name__}",
                field_name, value
            )
        
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f"Field '{field_name}' must be at least {self.min_value}",
                field_name, value
            )
        
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f"Field '{field_name}' must be at most {self.max_value}",
                field_name, value
            )
        
        return value


@dataclass
class ListRule(ValidationRule):
    """Rule to validate lists."""
    
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    item_rules: Optional[List[ValidationRule]] = None
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> Any:
        if not isinstance(value, list):
            raise ValidationError(f"Field '{field_name}' must be a list", field_name, value)
        
        if self.min_items is not None and len(value) < self.min_items:
            raise ValidationError(
                f"Field '{field_name}' must have at least {self.min_items} items",
                field_name, value
            )
        
        if self.max_items is not None and len(value) > self.max_items:
            raise ValidationError(
                f"Field '{field_name}' must have at most {self.max_items} items",
                field_name, value
            )
        
        # Validate each item
        if self.item_rules:
            validated_items = []
            for i, item in enumerate(value):
                for rule in self.item_rules:
                    item = rule.validate(item, f"{field_name}[{i}]")
                validated_items.append(item)
            return validated_items
        
        return value


class Validator:
    """Schema-based validator for MCP tool inputs."""
    
    def __init__(self, schema: Dict[str, List['ValidationRule']]):
        """Initialize validator with schema.
        
        Args:
            schema: Dictionary mapping field names to validation rules
        """
        self.schema = schema
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Validated (potentially transformed) data
            
        Raises:
            ValidationError: If validation fails
        """
        validated_data = {}
        
        for field_name, rules in self.schema.items():
            value = data.get(field_name)
            
            # Apply each rule in sequence
            for rule in rules:
                try:
                    value = rule.validate(value, field_name)
                except ValidationError as e:
                    logger.warning(f"Validation failed for field '{field_name}': {e}")
                    raise
            
            validated_data[field_name] = value
        
        # Check for unexpected fields
        unexpected_fields = set(data.keys()) - set(self.schema.keys())
        if unexpected_fields:
            logger.warning(f"Unexpected fields in input: {unexpected_fields}")
        
        return validated_data


def validate_input(schema: Dict[str, List['ValidationRule']]):
    """Decorator to validate function inputs.
    
    Args:
        schema: Validation schema
    """
    validator = Validator(schema)
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Validate kwargs (assumes first arg is self and kwargs contain the input)
            validated_kwargs = validator.validate(kwargs)
            return await func(*args, **validated_kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            validated_kwargs = validator.validate(kwargs)
            return func(*args, **validated_kwargs)
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Common validation schemas for MCP tools
SEARCH_CODE_SCHEMA = {
    "query": [
        RequiredRule(),
        StringRule(min_length=1, max_length=500)
    ],
    "max_results": [
        NumberRule(min_value=1, max_value=100, number_type=int)
    ],
    "language": [
        StringRule(pattern=r"^[a-z]+$", max_length=20)
    ]
}

ANALYZE_CONTEXT_SCHEMA = {
    "file_path": [
        RequiredRule(),
        StringRule(min_length=1, max_length=1000)
    ],
    "depth": [
        NumberRule(min_value=1, max_value=10, number_type=int)
    ],
    "include_dependencies": [
        TypeRule(bool)
    ]
}

GENERATE_CODE_SCHEMA = {
    "description": [
        RequiredRule(),
        StringRule(min_length=10, max_length=2000)
    ],
    "language": [
        StringRule(allowed_values=["python", "javascript", "typescript", "java", "go", "rust", "cpp"])
    ],
    "include_tests": [
        TypeRule(bool)
    ]
}


def create_mcp_validator(tool_name: str) -> Optional['Validator']:
    """Create a validator for a specific MCP tool.
    
    Args:
        tool_name: Name of the MCP tool
        
    Returns:
        Validator instance or None if no schema defined
    """
    schemas = {
        "search_code": SEARCH_CODE_SCHEMA,
        "analyze_context": ANALYZE_CONTEXT_SCHEMA,
        "generate_code": GENERATE_CODE_SCHEMA
    }
    
    schema = schemas.get(tool_name)
    if schema:
        return Validator(schema)
    
    logger.warning(f"No validation schema defined for tool: {tool_name}")
    return None


def sanitize_input(value: Any) -> Any:
    """Sanitize input to prevent injection attacks.
    
    Args:
        value: Input value to sanitize
        
    Returns:
        Sanitized value
    """
    if isinstance(value, str):
        # Remove potentially dangerous characters
        # This is a basic implementation - extend as needed
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',               # JavaScript URLs
            r'on\w+\s*=',                # Event handlers
            r'<iframe[^>]*>.*?</iframe>', # Iframes
        ]
        
        for pattern in dangerous_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Limit length to prevent DoS
        if len(value) > 10000:
            value = value[:10000] + "... [truncated]"
    
    elif isinstance(value, dict):
        return {k: sanitize_input(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_input(item) for item in value]
    
    return value