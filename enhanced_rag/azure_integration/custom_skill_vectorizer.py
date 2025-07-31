"""
Custom Skill and Vectorizer Implementation
Based on customskill.md documentation for enhanced RAG
"""

import logging
import os
import subprocess
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import aiohttp
import asyncio
import base64
from abc import ABC, abstractmethod
import json
import re

from azure.search.documents.indexes.models import (
    WebApiSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry
)

from ..core.config import get_config
from ..core.models import CodeContext
from ..semantic.query_enhancer import ContextualQueryEnhancer

logger = logging.getLogger(__name__)


class CustomSkillBase(ABC):
    """Base class for custom skills"""
    
    @abstractmethod
    async def process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single record"""
        pass
    
    async def process_batch(self, values: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Process a batch of records"""
        results = []
        
        for record in values:
            try:
                result = await self.process_record(record['data'])
                results.append({
                    'recordId': record['recordId'],
                    'data': result,
                    'errors': [],
                    'warnings': []
                })
            except Exception as e:
                logger.error(f"Error processing record {record.get('recordId')}: {e}")
                results.append({
                    'recordId': record['recordId'],
                    'data': {},
                    'errors': [{'message': str(e)}],
                    'warnings': []
                })
        
        return {'values': results}


class CodeAnalyzerSkill(CustomSkillBase):
    """
    Custom skill for analyzing code structure
    Extracts AST information, complexity metrics, and patterns
    """
    
    def __init__(self):
        self.query_enhancer = ContextualQueryEnhancer()
    
    async def process_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze code and extract structured information
        
        Expected input:
        - code: The code content
        - language: Programming language
        - filePath: File path for context
        
        Returns:
        - functions: List of function definitions
        - classes: List of class definitions
        - imports: List of imports
        - complexity: Complexity score
        - patterns: Detected patterns
        """
        code = data.get('code', '')
        language = data.get('language', 'unknown')
        file_path = data.get('filePath', '')
        
        # Create a minimal context for analysis
        context = CodeContext(
            current_file=file_path,
            file_content=code,
            language=language,
            imports=[],
            functions=[],
            classes=[]
        )
        
        # Use existing analyzers from our system
        # This is a simplified version - in production, you'd use proper AST parsing
        
        functions = self._extract_functions(code, language)
        classes = self._extract_classes(code, language)
        imports = self._extract_imports(code, language)
        complexity = self._calculate_complexity(code, functions, classes)
        patterns = self._detect_patterns(code, language, functions, classes)
        
        return {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'complexity': complexity,
            'patterns': patterns
        }
    
    def _extract_functions(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Extract function definitions"""
        functions = []
        
        if language.lower() == 'python':
            import re
            # Simple regex-based extraction (production would use AST)
            pattern = r'def\s+(\w+)\s*\(([^)]*)\):'
            for match in re.finditer(pattern, code):
                functions.append({
                    'name': match.group(1),
                    'parameters': [p.strip() for p in match.group(2).split(',') if p.strip()],
                    'type': 'function'
                })
        elif language.lower() in ['javascript', 'typescript']:
            import re
            # Function declarations and arrow functions
            patterns = [
                r'function\s+(\w+)\s*\(([^)]*)\)',
                r'const\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>'
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, code):
                    functions.append({
                        'name': match.group(1),
                        'parameters': [p.strip() for p in match.group(2).split(',') if p.strip()],
                        'type': 'function'
                    })
        
        return functions
    
    def _extract_classes(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Extract class definitions"""
        classes = []
        
        if language.lower() in ['python', 'javascript', 'typescript', 'java']:
            import re
            pattern = r'class\s+(\w+)'
            for match in re.finditer(pattern, code):
                classes.append({
                    'name': match.group(1),
                    'type': 'class'
                })
        
        return classes
    
    def _extract_imports(self, code: str, language: str) -> List[str]:
        """Extract import statements"""
        imports = []
        
        if language.lower() == 'python':
            import re
            patterns = [
                r'import\s+([\w.]+)',
                r'from\s+([\w.]+)\s+import'
            ]
            for pattern in patterns:
                imports.extend(re.findall(pattern, code))
        elif language.lower() in ['javascript', 'typescript']:
            import re
            patterns = [
                r'import\s+.*?\s+from\s+[\'"]([^\'")]+)[\'"]',
                r'require\s*\([\'"]([^\'")]+)[\'"]\)'
            ]
            for pattern in patterns:
                imports.extend(re.findall(pattern, code))
        
        return list(set(imports))
    
    def _calculate_complexity(
        self,
        code: str,
        functions: List[Dict[str, Any]],
        classes: List[Dict[str, Any]]
    ) -> float:
        """Calculate code complexity score"""
        # Simplified complexity calculation
        lines = code.split('\n')
        
        # Base complexity from line count
        base_complexity = min(len(lines) / 100, 1.0)
        
        # Add complexity for control structures
        control_keywords = ['if', 'else', 'elif', 'for', 'while', 'try', 'catch', 'switch']
        control_count = sum(1 for line in lines for keyword in control_keywords if keyword in line)
        control_complexity = min(control_count / 20, 1.0)
        
        # Add complexity for nesting
        max_indent = 0
        for line in lines:
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)
        indent_complexity = min(max_indent / 40, 1.0)
        
        # Combine scores
        complexity = (base_complexity + control_complexity + indent_complexity) / 3
        
        return round(complexity, 2)
    
    def _detect_patterns(
        self,
        code: str,
        language: str,
        functions: List[Dict[str, Any]],
        classes: List[Dict[str, Any]]
    ) -> List[str]:
        """Detect code patterns"""
        patterns = []
        
        # Check for common patterns
        code_lower = code.lower()
        
        # Design patterns
        if 'singleton' in code_lower or '_instance' in code_lower:
            patterns.append('singleton')
        if 'factory' in code_lower and any('create' in f['name'].lower() for f in functions):
            patterns.append('factory')
        if 'observer' in code_lower or 'subscribe' in code_lower:
            patterns.append('observer')
        
        # Async patterns
        if language.lower() in ['python', 'javascript', 'typescript']:
            if 'async' in code_lower:
                patterns.append('async')
            if 'await' in code_lower:
                patterns.append('async-await')
        
        # Framework patterns
        if '@component' in code_lower or 'React.Component' in code:
            patterns.append('component-based')
        if '@injectable' in code_lower or 'dependency injection' in code_lower:
            patterns.append('dependency-injection')
        
        return patterns


class EmbeddingGeneratorSkill(CustomSkillBase):
    """
    Custom skill for generating embeddings
    Can use various embedding models based on configuration
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config().embedding.model_dump()
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def process_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate embeddings for text or code
        
        Expected input:
        - text: The text to embed
        - language: Optional programming language for code
        
        Returns:
        - embedding: Vector embedding
        """
        text = data.get('text', '')
        language = data.get('language', 'text')
        
        # Add language context to improve embeddings
        if language != 'text':
            text = f"[{language}] {text}"
        
        # Generate embedding based on provider
        if self.config['provider'] == 'azure_openai':
            embedding = await self._generate_azure_openai_embedding(text)
        else:
            # Fallback to a simple embedding (in production, use proper models)
            embedding = self._generate_simple_embedding(text)
        
        return {
            'embedding': embedding
        }
    
    async def _generate_azure_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        endpoint = f"{self.config['azure_endpoint']}/openai/deployments/{self.config['model']}/embeddings"
        headers = {
            'api-key': self.config['api_key'],
            'Content-Type': 'application/json'
        }
        
        payload = {
            'input': text,
            'model': self.config['model']
        }
        
        try:
            async with self.session.post(
                endpoint,
                headers=headers,
                json=payload,
                params={'api-version': self.config['api_version']}
            ) as response:
                result = await response.json()
                return result['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector on error
            return [0.0] * self.config['dimensions']
    
    def _generate_simple_embedding(self, text: str) -> List[float]:
        """Generate a simple embedding for testing"""
        # This is just for testing - use real embeddings in production
        import hashlib
        
        # Generate deterministic "embedding" from text
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float values
        embedding = []
        for i in range(0, len(hash_bytes), 2):
            if i + 1 < len(hash_bytes):
                value = (hash_bytes[i] + hash_bytes[i + 1]) / 510.0  # Normalize to [0, 1]
                embedding.append(value)
        
        # Pad or truncate to desired dimensions
        dimensions = self.config['dimensions']
        if len(embedding) < dimensions:
            embedding.extend([0.0] * (dimensions - len(embedding)))
        else:
            embedding = embedding[:dimensions]
        
        return embedding


class CustomWebApiVectorizer:
    """
    Custom Web API Vectorizer for query-time embeddings
    Based on the customskill.md vectorizer documentation
    """
    
    def __init__(
        self,
        name: str,
        uri: str,
        http_method: str = "POST",
        http_headers: Optional[Dict[str, str]] = None,
        timeout: Optional[timedelta] = None,
        auth_resource_id: Optional[str] = None,
        auth_identity: Optional[str] = None
    ):
        self.name = name
        self.uri = uri
        self.http_method = http_method
        self.http_headers = http_headers or {}
        self.timeout = timeout or timedelta(seconds=30)
        self.auth_resource_id = auth_resource_id
        self.auth_identity = auth_identity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Azure Search vectorizer definition"""
        return {
            "name": self.name,
            "kind": "customWebApi",
            "customWebApiParameters": {
                "uri": self.uri,
                "httpMethod": self.http_method,
                "httpHeaders": self.http_headers,
                "timeout": f"PT{int(self.timeout.total_seconds())}S",
                "authResourceId": self.auth_resource_id,
                "authIdentity": self.auth_identity
            }
        }
    
    async def vectorize_query(
        self,
        query: str,
        query_type: str = "text"
    ) -> List[float]:
        """
        Vectorize a query using the custom endpoint
        
        Args:
            query: Query text
            query_type: Type of query (text, imageUrl, imageBinary)
            
        Returns:
            Vector embedding
        """
        async with aiohttp.ClientSession() as session:
            # Prepare payload according to spec
            payload = {
                "values": [
                    {
                        "recordId": "0",
                        "data": {
                            query_type: query if query_type != "imageBinary" else {
                                "data": base64.b64encode(query.encode()).decode()
                            }
                        }
                    }
                ]
            }
            
            headers = self.http_headers.copy()
            headers['Content-Type'] = 'application/json'
            
            try:
                async with session.request(
                    method=self.http_method,
                    url=self.uri,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout.total_seconds())
                ) as response:
                    result = await response.json()
                    
                    # Extract embedding from response
                    if 'values' in result and len(result['values']) > 0:
                        return result['values'][0]['data'].get('vector', [])
                    else:
                        logger.error(f"Invalid response from vectorizer: {result}")
                        return []
                        
            except Exception as e:
                logger.error(f"Error calling custom vectorizer: {e}")
                return []


class GitMetadataExtractorSkill(CustomSkillBase):
    """
    Custom skill for extracting git metadata
    """
    
    async def process_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract git metadata for a file
        
        Expected input:
        - filePath: Path to the file
        
        Returns:
        - lastCommit: Last commit hash
        - authors: List of authors
        - commitCount: Number of commits
        - lastModified: Last modification date
        """
        file_path = data.get('filePath', '')
        
        # Try to extract git metadata
        try:
            # Get last commit hash
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H', '--', file_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(file_path) if file_path else '.',
                timeout=5
            )
            last_commit = result.stdout.strip() if result.returncode == 0 else 'unknown'
            
            # Get authors
            result = subprocess.run(
                ['git', 'log', '--format=%an', '--', file_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(file_path) if file_path else '.',
                timeout=5
            )
            authors = list(set(result.stdout.strip().split('\n'))) if result.returncode == 0 else []
            
            # Get commit count
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD', '--', file_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(file_path) if file_path else '.',
                timeout=5
            )
            commit_count = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip().isdigit() else 0
            
            # Get last modified date
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%aI', '--', file_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(file_path) if file_path else '.',
                timeout=5
            )
            last_modified = result.stdout.strip() if result.returncode == 0 else datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.warning(f"Could not extract git metadata for {file_path}: {e}")
            # Fallback to file system metadata
            try:
                stat = os.stat(file_path)
                last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                last_commit = 'unknown'
                authors = []
                commit_count = 0
            except:
                last_modified = datetime.utcnow().isoformat()
                last_commit = 'unknown'
                authors = []
                commit_count = 0
        
        return {
            'lastCommit': last_commit,
            'authors': authors[:10],  # Limit to 10 authors
            'commitCount': commit_count,
            'lastModified': last_modified
        }


class ContextAwareChunkingSkill(CustomSkillBase):
    """
    Custom skill for intelligent code chunking
    Chunks based on code structure rather than arbitrary size
    """
    
    def __init__(self, max_chunk_size: int = 2000, overlap_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
    
    async def process_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chunk code intelligently based on structure
        
        Expected input:
        - code: The code content
        - language: Programming language
        
        Returns:
        - chunks: List of code chunks with metadata
        """
        code = data.get('code', '')
        language = data.get('language', 'unknown')
        
        # Simple line-based chunking with function awareness
        chunks = []
        lines = code.split('\n')
        
        current_chunk = []
        current_size = 0
        chunk_start_line = 0
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            # Check if adding this line would exceed chunk size
            if current_size + line_size > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'content': '\n'.join(current_chunk),
                    'start_line': chunk_start_line,
                    'end_line': i - 1,
                    'chunk_type': self._detect_chunk_type(current_chunk, language)
                })
                
                # Start new chunk with overlap
                overlap_lines = max(0, len(current_chunk) - 5)  # Last 5 lines
                current_chunk = current_chunk[-overlap_lines:] if overlap_lines > 0 else []
                current_size = sum(len(l) + 1 for l in current_chunk)
                chunk_start_line = i - overlap_lines if overlap_lines > 0 else i
            
            current_chunk.append(line)
            current_size += line_size
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'content': '\n'.join(current_chunk),
                'start_line': chunk_start_line,
                'end_line': len(lines) - 1,
                'chunk_type': self._detect_chunk_type(current_chunk, language)
            })
        
        return {
            'chunks': chunks
        }
    
    def _detect_chunk_type(self, lines: List[str], language: str) -> str:
        """Detect the type of code in a chunk"""
        content = '\n'.join(lines).lower()
        
        if any(keyword in content for keyword in ['function', 'def', 'func']):
            return 'function'
        elif 'class' in content:
            return 'class'
        elif any(keyword in content for keyword in ['import', 'require', 'use']):
            return 'imports'
        else:
            return 'code'


async def create_code_analysis_endpoint(host: str = "0.0.0.0", port: int = 8080):
    """
    Create a web endpoint for the code analyzer skill
    This can be deployed as an Azure Function or container
    """
    from aiohttp import web
    
    analyzer = CodeAnalyzerSkill()
    
    async def handle_request(request: web.Request) -> web.Response:
        try:
            data = await request.json()
            result = await analyzer.process_batch(data['values'])
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )
    
    app = web.Application()
    app.router.add_post('/', handle_request)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Code analysis endpoint running on http://{host}:{port}")
    
    return runner