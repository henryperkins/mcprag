"""
Custom Skill and Vectorizer Implementation
Based on customskill.md documentation for enhanced RAG
"""

import logging
import os
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiohttp
import asyncio
import base64
from abc import ABC, abstractmethod
import time
import time


from enhanced_rag.core.config import get_config
from enhanced_rag.semantic.query_enhancer import ContextualQueryEnhancer

logger = logging.getLogger(__name__)


class CustomSkillBase(ABC):
    """Base class for custom skills"""
    
    @abstractmethod
    async def process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single record"""
        pass
    
    async def process_batch(
        self, values: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
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
                logger.error(
                    f"Error processing record {record.get('recordId')}: {e}"
                )
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
        # Use existing analyzers (simplified; production should use AST)
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
    
    def _extract_functions(
        self,
        code: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Extract function definitions"""
        functions: List[Dict[str, Any]] = []

        if language.lower() == 'python':
            import re
            pattern = r'def\s+(\w+)\s*\(([^)]*)\):'
            for match in re.finditer(pattern, code):
                params_str = match.group(2)
                params = [
                    p.strip()
                    for p in params_str.split(',')
                    if p.strip()
                ]
                functions.append({
                    'name': match.group(1),
                    'parameters': params,
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
                    params_str = match.group(2)
                    params = [
                        p.strip()
                        for p in params_str.split(',')
                        if p.strip()
                    ]
                    functions.append({
                        'name': match.group(1),
                        'parameters': params,
                        'type': 'function'
                    })

        return functions
    
    def _extract_classes(
        self,
        code: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Extract class definitions"""
        classes: List[Dict[str, Any]] = []

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
        control_keywords = [
            'if', 'else', 'elif', 'for', 'while',
            'try', 'catch', 'switch'
        ]
        control_count = sum(
            1
            for line in lines
            for keyword in control_keywords
            if keyword in line
        )
        control_complexity = min(control_count / 20, 1.0)
        
        # Add complexity for nesting
        max_indent = 0
        for line in lines:
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)
        indent_complexity = min(max_indent / 40, 1.0)
        
        # Combine scores
        complexity = (
            base_complexity + control_complexity + indent_complexity
        ) / 3
        
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
        if (
            'factory' in code_lower
            and any('create' in f['name'].lower() for f in functions)
        ):
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
        self._semaphore = asyncio.Semaphore(
            self.config.get('max_concurrent_requests', 5)
        )
        
        # Initialize embedding provider based on config
        self.provider = None
        if self.config.get('provider') == 'client':
            from .embedding_provider import AzureOpenAIEmbeddingProvider
            self.provider = AzureOpenAIEmbeddingProvider()
        elif self.config.get('provider') == 'none':
            self.provider = None
        # else: provider remains None, will use azure_openai_http method
        
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
        if self.provider is not None:
            # Use client-side embedding provider
            embedding = self.provider.generate_embedding(text)
            if embedding and len(embedding) != self.config.get('dimensions', 1536):
                # Truncate or pad to match configured dimensions
                dimensions = self.config.get('dimensions', 1536)
                if len(embedding) > dimensions:
                    embedding = embedding[:dimensions]
                else:
                    embedding = embedding + [0.0] * (dimensions - len(embedding))
            return {'embedding': embedding or []}
        elif self.config.get('provider') == 'azure_openai_http':
            # Use existing Azure HTTP method
            embedding = await self._generate_azure_openai_embedding_with_retry(text)
            return {'embedding': embedding}
        else:
            # Provider is 'none' or unknown - return empty embedding
            return {'embedding': []}
    
    async def _generate_azure_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        endpoint = self.config.get('azure_endpoint')
        model = self.config.get('model')
        api_key = self.config.get('api_key')
        api_version = self.config.get('api_version')

        if not endpoint or not model or not api_key or not api_version:
            raise RuntimeError(
                "Missing required Azure OpenAI embedding configuration"
            )

        url = f"{endpoint}/openai/deployments/{model}/embeddings"
        headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            'input': text,
            'model': model
        }

        async with self._semaphore:
            async with self.session.post(
                url,
                headers=headers,
                json=payload,
                params={'api-version': api_version}
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    raise RuntimeError(
                        f"Embedding HTTP {response.status}: {body[:200]}"
                    )
                result = await response.json()
                return result['data'][0]['embedding']

    async def _generate_azure_openai_embedding_with_retry(
        self,
        text: str,
        max_retries: int = 3
    ) -> List[float]:
        """Generate embedding with retry logic and exponential backoff"""
        delay = 1.0
        for attempt in range(max_retries):
            try:
                return await self._generate_azure_openai_embedding(text)
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Embedding attempt {attempt + 1} failed, "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"All embedding attempts failed: {e}")
                    dims = int(self.config.get('dimensions', 1536))
                    return [0.0] * dims
        # Fallback in case no return occurred above
        dims = int(self.config.get('dimensions', 1536))
        return [0.0] * dims
    
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
                value = (hash_bytes[i] + hash_bytes[i + 1]) / 510.0  # Normalize [0,1]
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

        # Simple concurrency limit shared per instance
        self._semaphore = asyncio.Semaphore(
            get_config().embedding.max_concurrent_requests
        )
        # Circuit breaker state
        self._fail_count = 0
        self._open_until = 0.0
    
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

            # Circuit breaker parameters
            cfg = get_config().embedding
            threshold = getattr(cfg, "circuit_breaker_threshold", 5)
            reset_seconds = getattr(cfg, "circuit_breaker_reset_seconds", 30)

            # Short-circuit if breaker is open
            now = time.monotonic()
            if now < self._open_until:
                logger.warning("Vectorizer circuit breaker open; skipping request")
                return []

            try:
                async with self._semaphore:
                    async with session.request(
                        method=self.http_method,
                        url=self.uri,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.timeout.total_seconds())
                    ) as response:
                        if response.status != 200:
                            body = await response.text()
                            raise RuntimeError(f"Vectorizer HTTP {response.status}: {body[:200]}")

                        result = await response.json()

                        # Extract embedding from response
                        if 'values' in result and len(result['values']) > 0:
                            # Success: reset breaker
                            self._fail_count = 0
                            return result['values'][0]['data'].get('vector', [])
                        else:
                            raise RuntimeError(f"Invalid response from vectorizer: {result}")

            except Exception as e:
                logger.error(f"Error calling custom vectorizer: {e}")
                # Update circuit breaker
                self._fail_count += 1
                if self._fail_count >= threshold:
                    self._open_until = time.monotonic() + reset_seconds
                    logger.warning(
                        f"Vectorizer circuit opened for {reset_seconds}s after "
                        f"{self._fail_count} failures"
                    )
                return []


class GitMetadataExtractorSkill(CustomSkillBase):
    """
    Custom skill for extracting git metadata
    """
    
    async def process_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract git metadata for a file with input validation and safe subprocess usage.
        """
        file_path = data.get('filePath', '')

        # Validate file path to prevent command injection and path traversal
        if not file_path or '..' in file_path or os.path.isabs(file_path):
            logger.warning(f"Invalid file path: {file_path}")
            return self._empty_metadata()

        try:
            real_path = os.path.realpath(file_path)
            if not os.path.exists(real_path) or not os.path.isfile(real_path):
                return self._empty_metadata()

            repo_dir = os.path.dirname(real_path)

            def run_git(args: List[str]) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ['git'] + args + ['--', real_path],
                    capture_output=True,
                    text=True,
                    cwd=repo_dir,
                    timeout=5
                )

            # Last commit hash
            result = run_git(['log', '-1', '--format=%H'])
            last_commit = result.stdout.strip() if result.returncode == 0 else 'unknown'

            # Authors (unique, non-empty)
            result = run_git(['log', '--format=%an'])
            authors = [a for a in set(result.stdout.strip().split('\n')) if a] if result.returncode == 0 else []

            # Commit count
            result = run_git(['rev-list', '--count', 'HEAD'])
            commit_count = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip().isdigit() else 0

            # Last modified (ISO)
            result = run_git(['log', '-1', '--format=%aI'])
            last_modified = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else datetime.utcnow().isoformat()

        except Exception as e:
            logger.warning(f"Could not extract git metadata for {file_path}: {e}")
            try:
                stat = os.stat(file_path)
                last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            except Exception:
                last_modified = datetime.utcnow().isoformat()
            last_commit = 'unknown'
            authors = []
            commit_count = 0

        return {
            'lastCommit': last_commit,
            'authors': authors[:10],
            'commitCount': commit_count,
            'lastModified': last_modified
        }

    def _empty_metadata(self) -> Dict[str, Any]:
        """Return empty metadata structure"""
        return {
            'lastCommit': 'unknown',
            'authors': [],
            'commitCount': 0,
            'lastModified': datetime.utcnow().isoformat()
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