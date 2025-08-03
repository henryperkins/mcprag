"""
Template management for code generation
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CodeTemplate:
    """Represents a code template"""
    name: str
    language: str
    description: str
    pattern_type: str  # 'function', 'class', 'module', 'test', etc.
    template_code: str
    placeholders: Dict[str, str]  # placeholder -> description
    required_imports: List[str]
    tags: List[str]
    usage_count: int = 0
    confidence_score: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'language': self.language,
            'description': self.description,
            'pattern_type': self.pattern_type,
            'template_code': self.template_code,
            'placeholders': self.placeholders,
            'required_imports': self.required_imports,
            'tags': self.tags,
            'usage_count': self.usage_count,
            'confidence_score': self.confidence_score
        }


class TemplateManager:
    """
    Manages code templates for generation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize template manager"""
        self.config = config or {}
        
        # Template storage
        self.templates: Dict[str, List[CodeTemplate]] = defaultdict(list)
        
        # Load built-in templates
        self._load_builtin_templates()
        
        # Load custom templates if available
        custom_templates_path = self.config.get('custom_templates_path')
        if custom_templates_path:
            self._load_custom_templates(custom_templates_path)
        
        # Template matching patterns
        self.matching_patterns = self._initialize_matching_patterns()
    
    def _load_builtin_templates(self):
        """Load built-in code templates"""
        # Python templates
        self.templates['python'].extend([
            CodeTemplate(
                name='python_class_basic',
                language='python',
                description='Basic Python class with constructor',
                pattern_type='class',
                template_code='''class {{CLASS_NAME}}:
    """{{CLASS_DESCRIPTION}}"""
    
    def __init__(self{{INIT_PARAMS}}):
        """Initialize {{CLASS_NAME}}
        
        Args:
            {{INIT_ARGS_DOCS}}
        """
        {{INIT_BODY}}
    
    {{METHODS}}''',
                placeholders={
                    'CLASS_NAME': 'Name of the class',
                    'CLASS_DESCRIPTION': 'Class description',
                    'INIT_PARAMS': 'Constructor parameters',
                    'INIT_ARGS_DOCS': 'Constructor arguments documentation',
                    'INIT_BODY': 'Constructor body',
                    'METHODS': 'Class methods'
                },
                required_imports=[],
                tags=['class', 'oop', 'basic']
            ),
            
            CodeTemplate(
                name='python_function_async',
                language='python',
                description='Async Python function',
                pattern_type='function',
                template_code='''async def {{FUNCTION_NAME}}({{PARAMS}}) -> {{RETURN_TYPE}}:
    """{{FUNCTION_DESCRIPTION}}
    
    Args:
        {{ARGS_DOCS}}
    
    Returns:
        {{RETURN_DOCS}}
    """
    {{FUNCTION_BODY}}''',
                placeholders={
                    'FUNCTION_NAME': 'Function name',
                    'PARAMS': 'Function parameters',
                    'RETURN_TYPE': 'Return type annotation',
                    'FUNCTION_DESCRIPTION': 'Function description',
                    'ARGS_DOCS': 'Arguments documentation',
                    'RETURN_DOCS': 'Return value documentation',
                    'FUNCTION_BODY': 'Function implementation'
                },
                required_imports=['import asyncio'],
                tags=['async', 'function', 'coroutine']
            ),
            
            CodeTemplate(
                name='python_dataclass',
                language='python',
                description='Python dataclass',
                pattern_type='class',
                template_code='''@dataclass
class {{CLASS_NAME}}:
    """{{CLASS_DESCRIPTION}}"""
    {{FIELDS}}
    
    def {{METHOD_NAME}}(self) -> {{RETURN_TYPE}}:
        """{{METHOD_DESCRIPTION}}"""
        {{METHOD_BODY}}''',
                placeholders={
                    'CLASS_NAME': 'Dataclass name',
                    'CLASS_DESCRIPTION': 'Dataclass description',
                    'FIELDS': 'Dataclass fields',
                    'METHOD_NAME': 'Method name',
                    'RETURN_TYPE': 'Method return type',
                    'METHOD_DESCRIPTION': 'Method description',
                    'METHOD_BODY': 'Method implementation'
                },
                required_imports=['from dataclasses import dataclass'],
                tags=['dataclass', 'class', 'data']
            ),
            
            CodeTemplate(
                name='python_context_manager',
                language='python',
                description='Python context manager',
                pattern_type='class',
                template_code='''class {{CLASS_NAME}}:
    """Context manager for {{PURPOSE}}"""
    
    def __init__(self{{INIT_PARAMS}}):
        {{INIT_BODY}}
    
    def __enter__(self):
        """Enter the context"""
        {{ENTER_BODY}}
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context"""
        {{EXIT_BODY}}
        return False''',
                placeholders={
                    'CLASS_NAME': 'Context manager class name',
                    'PURPOSE': 'Purpose of the context manager',
                    'INIT_PARAMS': 'Initialization parameters',
                    'INIT_BODY': 'Initialization logic',
                    'ENTER_BODY': 'Enter logic',
                    'EXIT_BODY': 'Exit/cleanup logic'
                },
                required_imports=[],
                tags=['context', 'manager', 'resource']
            ),
            
            CodeTemplate(
                name='python_test_class',
                language='python',
                description='Python test class with pytest',
                pattern_type='test',
                template_code='''import pytest
{{IMPORTS}}

class Test{{CLASS_NAME}}:
    """Test cases for {{CLASS_NAME}}"""
    
    @pytest.fixture
    def {{FIXTURE_NAME}}(self):
        """{{FIXTURE_DESCRIPTION}}"""
        {{FIXTURE_BODY}}
    
    def test_{{TEST_NAME}}(self, {{FIXTURE_NAME}}):
        """Test {{TEST_DESCRIPTION}}"""
        # Arrange
        {{ARRANGE}}
        
        # Act
        {{ACT}}
        
        # Assert
        {{ASSERT}}''',
                placeholders={
                    'CLASS_NAME': 'Class being tested',
                    'IMPORTS': 'Additional imports',
                    'FIXTURE_NAME': 'Test fixture name',
                    'FIXTURE_DESCRIPTION': 'Fixture description',
                    'FIXTURE_BODY': 'Fixture setup',
                    'TEST_NAME': 'Test method name',
                    'TEST_DESCRIPTION': 'What is being tested',
                    'ARRANGE': 'Test setup',
                    'ACT': 'Test action',
                    'ASSERT': 'Test assertions'
                },
                required_imports=['import pytest'],
                tags=['test', 'pytest', 'unit']
            )
        ])
        
        # JavaScript/TypeScript templates
        self.templates['javascript'].extend([
            CodeTemplate(
                name='js_class_es6',
                language='javascript',
                description='ES6 JavaScript class',
                pattern_type='class',
                template_code='''class {{CLASS_NAME}} {
    /**
     * {{CLASS_DESCRIPTION}}
     */
    constructor({{CONSTRUCTOR_PARAMS}}) {
        {{CONSTRUCTOR_BODY}}
    }
    
    /**
     * {{METHOD_DESCRIPTION}}
     * @returns {{RETURN_DESCRIPTION}}
     */
    {{METHOD_NAME}}({{METHOD_PARAMS}}) {
        {{METHOD_BODY}}
    }
}''',
                placeholders={
                    'CLASS_NAME': 'Class name',
                    'CLASS_DESCRIPTION': 'Class description',
                    'CONSTRUCTOR_PARAMS': 'Constructor parameters',
                    'CONSTRUCTOR_BODY': 'Constructor implementation',
                    'METHOD_NAME': 'Method name',
                    'METHOD_DESCRIPTION': 'Method description',
                    'METHOD_PARAMS': 'Method parameters',
                    'RETURN_DESCRIPTION': 'Return value description',
                    'METHOD_BODY': 'Method implementation'
                },
                required_imports=[],
                tags=['class', 'es6', 'oop']
            ),
            
            CodeTemplate(
                name='js_async_function',
                language='javascript',
                description='Async JavaScript function',
                pattern_type='function',
                template_code='''/**
 * {{FUNCTION_DESCRIPTION}}
 * @param {{PARAM_DOCS}}
 * @returns {Promise<{{RETURN_TYPE}}>} {{RETURN_DESCRIPTION}}
 */
async function {{FUNCTION_NAME}}({{PARAMS}}) {
    try {
        {{TRY_BODY}}
    } catch (error) {
        {{CATCH_BODY}}
    }
}''',
                placeholders={
                    'FUNCTION_NAME': 'Function name',
                    'FUNCTION_DESCRIPTION': 'Function description',
                    'PARAMS': 'Function parameters',
                    'PARAM_DOCS': 'Parameter documentation',
                    'RETURN_TYPE': 'Return type',
                    'RETURN_DESCRIPTION': 'Return description',
                    'TRY_BODY': 'Try block implementation',
                    'CATCH_BODY': 'Error handling'
                },
                required_imports=[],
                tags=['async', 'function', 'promise']
            ),
            
            CodeTemplate(
                name='js_react_component',
                language='javascript',
                description='React functional component',
                pattern_type='component',
                template_code='''import React{{HOOKS_IMPORT}} from 'react';
{{IMPORTS}}

/**
 * {{COMPONENT_DESCRIPTION}}
 */
const {{COMPONENT_NAME}} = ({{PROPS}}) => {
    {{HOOKS}}
    
    {{HANDLERS}}
    
    return (
        {{JSX}}
    );
};

export default {{COMPONENT_NAME}};''',
                placeholders={
                    'COMPONENT_NAME': 'Component name',
                    'COMPONENT_DESCRIPTION': 'Component description',
                    'HOOKS_IMPORT': 'React hooks to import',
                    'IMPORTS': 'Additional imports',
                    'PROPS': 'Component props',
                    'HOOKS': 'React hooks usage',
                    'HANDLERS': 'Event handlers',
                    'JSX': 'JSX template'
                },
                required_imports=["import React from 'react'"],
                tags=['react', 'component', 'functional']
            )
        ])
        
        # TypeScript templates
        self.templates['typescript'].extend([
            CodeTemplate(
                name='ts_interface',
                language='typescript',
                description='TypeScript interface',
                pattern_type='interface',
                template_code='''/**
 * {{INTERFACE_DESCRIPTION}}
 */
export interface {{INTERFACE_NAME}} {
    {{PROPERTIES}}
}''',
                placeholders={
                    'INTERFACE_NAME': 'Interface name',
                    'INTERFACE_DESCRIPTION': 'Interface description',
                    'PROPERTIES': 'Interface properties'
                },
                required_imports=[],
                tags=['interface', 'type', 'contract']
            ),
            
            CodeTemplate(
                name='ts_generic_class',
                language='typescript',
                description='TypeScript generic class',
                pattern_type='class',
                template_code='''/**
 * {{CLASS_DESCRIPTION}}
 */
export class {{CLASS_NAME}}<{{TYPE_PARAMS}}> {
    private {{PRIVATE_PROPERTIES}};
    
    constructor({{CONSTRUCTOR_PARAMS}}) {
        {{CONSTRUCTOR_BODY}}
    }
    
    /**
     * {{METHOD_DESCRIPTION}}
     */
    public {{METHOD_NAME}}({{METHOD_PARAMS}}): {{RETURN_TYPE}} {
        {{METHOD_BODY}}
    }
}''',
                placeholders={
                    'CLASS_NAME': 'Class name',
                    'CLASS_DESCRIPTION': 'Class description',
                    'TYPE_PARAMS': 'Generic type parameters',
                    'PRIVATE_PROPERTIES': 'Private properties',
                    'CONSTRUCTOR_PARAMS': 'Constructor parameters',
                    'CONSTRUCTOR_BODY': 'Constructor implementation',
                    'METHOD_NAME': 'Method name',
                    'METHOD_DESCRIPTION': 'Method description',
                    'METHOD_PARAMS': 'Method parameters',
                    'RETURN_TYPE': 'Return type',
                    'METHOD_BODY': 'Method implementation'
                },
                required_imports=[],
                tags=['generic', 'class', 'typed']
            )
        ])
    
    def _load_custom_templates(self, templates_path: str):
        """Load custom templates from file"""
        path = Path(templates_path)
        if not path.exists():
            logger.warning(f"Custom templates path not found: {templates_path}")
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                custom_templates = json.load(f)
            
            for template_data in custom_templates:
                template = CodeTemplate(**template_data)
                self.templates[template.language].append(template)
            
            logger.info(f"Loaded {len(custom_templates)} custom templates")
        except Exception as e:
            logger.error(f"Error loading custom templates: {e}")
    
    def _initialize_matching_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for template matching"""
        return {
            'class': [
                r'\bclass\b',
                r'\bobject\b',
                r'\btype\b',
                r'\bmodel\b',
                r'\bentity\b'
            ],
            'function': [
                r'\bfunction\b',
                r'\bmethod\b',
                r'\bdef\b',
                r'\bcallable\b',
                r'\bhandler\b'
            ],
            'async': [
                r'\basync\b',
                r'\bawait\b',
                r'\bpromise\b',
                r'\bcoroutine\b',
                r'\bconcurrent\b'
            ],
            'test': [
                r'\btest\b',
                r'\bunit\s*test\b',
                r'\bspec\b',
                r'\bassert\b',
                r'\bexpect\b'
            ],
            'component': [
                r'\bcomponent\b',
                r'\bwidget\b',
                r'\bview\b',
                r'\belement\b',
                r'\bui\b'
            ],
            'api': [
                r'\bapi\b',
                r'\bendpoint\b',
                r'\broute\b',
                r'\brest\b',
                r'\bhttp\b'
            ],
            'data': [
                r'\bdata\b',
                r'\bmodel\b',
                r'\bschema\b',
                r'\btable\b',
                r'\bdatabase\b'
            ]
        }
    
    async def get_template(
        self,
        description: str,
        language: str,
        patterns: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most appropriate template
        
        Args:
            description: Task description
            language: Programming language
            patterns: Extracted patterns from examples
            
        Returns:
            Template dict or None
        """
        language = language.lower()
        
        # Get language-specific templates
        available_templates = self.templates.get(language, [])
        if not available_templates:
            logger.warning(f"No templates available for language: {language}")
            return None
        
        # Score each template
        template_scores = []
        
        for template in available_templates:
            score = self._score_template(template, description, patterns)
            template_scores.append((template, score))
        
        # Sort by score
        template_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return best match if score is high enough
        if template_scores and template_scores[0][1] > 0.3:
            best_template = template_scores[0][0]
            
            # Increment usage count
            best_template.usage_count += 1
            
            return best_template.to_dict()
        
        return None
    
    def _score_template(
        self,
        template: CodeTemplate,
        description: str,
        patterns: Dict[str, Any]
    ) -> float:
        """Score a template based on relevance"""
        score = 0.0
        description_lower = description.lower()
        
        # Check pattern type match
        pattern_types = set()
        for pattern_list in patterns.values():
            for pattern in pattern_list:
                if isinstance(pattern, dict) and 'type' in pattern:
                    pattern_types.add(pattern['type'])
        
        if template.pattern_type in pattern_types:
            score += 0.3
        
        # Check description keywords
        for pattern_type, keywords in self.matching_patterns.items():
            if pattern_type == template.pattern_type:
                for keyword in keywords:
                    if re.search(keyword, description_lower):
                        score += 0.1
                        break
        
        # Check tag matches
        for tag in template.tags:
            if tag in description_lower:
                score += 0.1
        
        # Boost for specific patterns
        if 'async' in template.tags and 'async' in description_lower:
            score += 0.2
        
        if 'test' in template.tags and any(word in description_lower for word in ['test', 'spec', 'unit']):
            score += 0.2
        
        # Consider template confidence and usage
        score *= template.confidence_score
        
        # Small boost for frequently used templates
        if template.usage_count > 10:
            score += 0.05
        
        return min(score, 1.0)
    
    def fill_template(
        self,
        template: Dict[str, Any],
        values: Dict[str, str]
    ) -> str:
        """
        Fill template placeholders with values
        
        Args:
            template: Template dictionary
            values: Placeholder values
            
        Returns:
            Filled template code
        """
        code = template['template_code']
        
        # Replace placeholders
        for placeholder, value in values.items():
            placeholder_pattern = f'{{{{{placeholder}}}}}'
            code = code.replace(placeholder_pattern, value)
        
        # Remove any unfilled placeholders
        code = re.sub(r'\{\{[^}]+\}\}', '# TODO: Fill in', code)
        
        return code
    
    def create_template_from_code(
        self,
        code: str,
        language: str,
        name: str,
        description: str,
        pattern_type: str
    ) -> CodeTemplate:
        """
        Create a new template from existing code
        
        Args:
            code: Example code
            language: Programming language
            name: Template name
            description: Template description
            pattern_type: Type of pattern
            
        Returns:
            New CodeTemplate
        """
        # Extract placeholders from code
        placeholders = {}
        template_code = code
        
        # Common patterns to replace with placeholders
        replacements = {
            # Variable/function names
            r'\b([A-Z][a-zA-Z0-9]+)\b': 'CLASS_NAME',
            r'\b([a-z][a-zA-Z0-9]+)\s*\(': 'FUNCTION_NAME',
            r'\b([a-z_][a-z0-9_]+)\s*=': 'VARIABLE_NAME',
            
            # String literals
            r'"[^"]*"': 'STRING_VALUE',
            r"'[^']*'": 'STRING_VALUE',
            
            # Comments/docstrings
            r'"""[^"]*"""': 'DOCSTRING',
            r'#.*$': 'COMMENT',
            r'/\*[\s\S]*?\*/': 'BLOCK_COMMENT',
            r'//.*$': 'LINE_COMMENT',
        }
        
        # Apply replacements
        placeholder_count = {}
        for pattern, placeholder_base in replacements.items():
            matches = re.finditer(pattern, template_code, re.MULTILINE)
            for match in matches:
                # Generate unique placeholder
                count = placeholder_count.get(placeholder_base, 0) + 1
                placeholder_count[placeholder_base] = count
                
                placeholder = f"{placeholder_base}_{count}" if count > 1 else placeholder_base
                placeholders[placeholder] = f"TODO: Describe {placeholder_base.lower().replace('_', ' ')}"
                
                # Replace in template
                template_code = template_code.replace(
                    match.group(0),
                    f'{{{{{placeholder}}}}}',
                    1
                )
        
        # Extract imports
        required_imports = []
        import_pattern = r'^(?:import|from)\s+.*$'
        imports = re.findall(import_pattern, code, re.MULTILINE)
        required_imports.extend(imports)
        
        # Create template
        return CodeTemplate(
            name=name,
            language=language,
            description=description,
            pattern_type=pattern_type,
            template_code=template_code,
            placeholders=placeholders,
            required_imports=required_imports,
            tags=self._extract_tags(description, pattern_type),
            confidence_score=0.7  # Lower confidence for auto-generated
        )
    
    def _extract_tags(self, description: str, pattern_type: str) -> List[str]:
        """Extract tags from description and pattern type"""
        tags = [pattern_type]
        
        # Common tag keywords
        tag_keywords = {
            'async': ['async', 'await', 'promise', 'concurrent'],
            'test': ['test', 'spec', 'unit', 'integration'],
            'api': ['api', 'endpoint', 'rest', 'http'],
            'data': ['data', 'model', 'schema', 'database'],
            'ui': ['ui', 'component', 'view', 'widget'],
            'util': ['util', 'helper', 'utility', 'tool'],
        }
        
        description_lower = description.lower()
        for tag, keywords in tag_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                tags.append(tag)
        
        return list(set(tags))
    
    def save_templates(self, output_path: str):
        """Save templates to file"""
        templates_data = []
        
        for language, language_templates in self.templates.items():
            for template in language_templates:
                templates_data.append(template.to_dict())
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, indent=2)
            logger.info(f"Saved {len(templates_data)} templates to {output_path}")
        except Exception as e:
            logger.error(f"Error saving templates: {e}")
    
    def get_template_suggestions(
        self,
        description: str,
        language: str,
        max_suggestions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get multiple template suggestions
        
        Args:
            description: Task description
            language: Programming language
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of template suggestions
        """
        language = language.lower()
        available_templates = self.templates.get(language, [])
        
        if not available_templates:
            return []
        
        # Score all templates
        suggestions = []
        for template in available_templates:
            score = self._score_template(template, description, {})
            if score > 0.1:  # Minimum threshold
                suggestions.append({
                    'template': template.to_dict(),
                    'score': score,
                    'reason': self._explain_template_choice(template, description)
                })
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:max_suggestions]
    
    def _explain_template_choice(
        self,
        template: CodeTemplate,
        description: str
    ) -> str:
        """Explain why a template was chosen"""
        reasons = []
        
        description_lower = description.lower()
        
        # Pattern type match
        if template.pattern_type in description_lower:
            reasons.append(f"Matches {template.pattern_type} pattern")
        
        # Tag matches
        matching_tags = [tag for tag in template.tags if tag in description_lower]
        if matching_tags:
            reasons.append(f"Contains tags: {', '.join(matching_tags)}")
        
        # Special features
        if 'async' in template.tags and 'async' in description_lower:
            reasons.append("Supports async operations")
        
        if 'test' in template.tags:
            reasons.append("Provides testing structure")
        
        return "; ".join(reasons) if reasons else "General purpose template"