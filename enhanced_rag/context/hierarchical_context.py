"""
Hierarchical Context Analyzer
Implements multi-level context awareness for code understanding
"""

import ast
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import subprocess
import re
from collections import defaultdict

from ..core.interfaces import ContextProvider
from ..core.models import CodeContext, EnhancedContext, ContextLevel
from ..core.config import get_config

logger = logging.getLogger(__name__)


class HierarchicalContextAnalyzer(ContextProvider):
    """
    Analyzes code context at multiple hierarchical levels:
    1. File level - Current file imports, functions, classes
    2. Module level - Related files in same package/directory
    3. Project level - Project-wide patterns and conventions
    4. Cross-project level - Similar patterns across repositories
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config().context.model_dump()
        self.cache: Dict[str, Tuple[EnhancedContext, datetime]] = {}
        self._initialize_analyzers()
    
    def _initialize_analyzers(self):
        """Initialize language-specific analyzers"""
        self.analyzers = {
            'python': self._analyze_python_file,
            'javascript': self._analyze_javascript_file,
            'typescript': self._analyze_javascript_file,
            'java': self._analyze_java_file,
            'go': self._analyze_go_file,
            'rust': self._analyze_rust_file,
        }
    
    async def get_context(
        self,
        file_path: str,
        open_files: Optional[List[str]] = None,
        recent_edits: Optional[List[Tuple[str, datetime]]] = None
    ) -> CodeContext:
        """Extract basic context from current file"""
        try:
            # Check cache first
            if self._is_cached(file_path):
                cached_context = self.cache[file_path][0]
                return CodeContext(
                    current_file=cached_context.current_file,
                    file_content=cached_context.file_content,
                    imports=cached_context.imports,
                    functions=cached_context.functions,
                    classes=cached_context.classes,
                    recent_changes=cached_context.recent_changes,
                    git_branch=cached_context.git_branch,
                    language=cached_context.language,
                    framework=cached_context.framework,
                    project_root=cached_context.project_root,
                    open_files=open_files or [],
                )
            
            # Extract fresh context
            language = self._detect_language(file_path)
            file_content = self._read_file(file_path)
            
            # Get language-specific analysis
            analysis = await self._analyze_file(file_path, file_content, language)
            
            # Get git information
            git_info = await self._get_git_info(file_path)
            
            # Detect framework
            framework = await self._detect_framework(file_path, language, analysis['imports'])
            
            context = CodeContext(
                current_file=file_path,
                file_content=file_content,
                imports=analysis.get('imports', []),
                functions=analysis.get('functions', []),
                classes=analysis.get('classes', []),
                recent_changes=git_info.get('recent_changes', []),
                git_branch=git_info.get('branch'),
                language=language,
                framework=framework,
                project_root=self._find_project_root(file_path),
                open_files=open_files or [],
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Error extracting context from {file_path}: {e}")
            # Return minimal context on error
            return CodeContext(
                current_file=file_path,
                language=self._detect_language(file_path),
                open_files=open_files or [],
            )
    
    async def get_hierarchical_context(
        self,
        file_path: str,
        depth: int = 3
    ) -> EnhancedContext:
        """Get multi-level hierarchical context"""
        try:
            # Check cache
            if self._is_cached(file_path):
                return self.cache[file_path][0]
            
            # Get basic context first
            base_context = await self.get_context(file_path)
            
            # Build hierarchical context
            module_context = await self._analyze_module_context(file_path, base_context)
            project_context = await self._analyze_project_context(file_path, base_context)
            cross_project_patterns = await self._analyze_cross_project_patterns(base_context)
            
            # Build dependency graph
            dependency_graph = await self._build_dependency_graph(
                file_path, 
                base_context,
                depth
            )
            
            # Detect architectural patterns
            architectural_patterns = await self._detect_architectural_patterns(
                base_context,
                module_context,
                project_context
            )
            
            # Calculate context weights based on relevance
            context_weights = self._calculate_context_weights(
                base_context,
                module_context,
                project_context
            )
            
            enhanced_context = EnhancedContext(
                **base_context.model_dump(),
                module_context=module_context,
                project_context=project_context,
                cross_project_patterns=cross_project_patterns,
                dependency_graph=dependency_graph,
                architectural_patterns=architectural_patterns,
                context_weights=context_weights
            )
            
            # Cache the result
            if self.config.get('cache_enabled', True):
                self.cache[file_path] = (enhanced_context, datetime.utcnow())
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Error building hierarchical context for {file_path}: {e}")
            # Return basic context on error
            base_context = await self.get_context(file_path)
            return EnhancedContext(**base_context.model_dump())
    
    async def _analyze_file(
        self, 
        file_path: str, 
        content: str, 
        language: str
    ) -> Dict[str, Any]:
        """Analyze file content based on language"""
        analyzer = self.analyzers.get(language, self._analyze_generic_file)
        return await analyzer(file_path, content)
    
    async def _analyze_python_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze Python file using AST"""
        try:
            tree = ast.parse(content, filename=file_path)
            
            imports = []
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                        'docstring': ast.get_docstring(node)
                    }
                    functions.append(func_info)
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'bases': [self._get_base_name(base) for base in node.bases],
                        'methods': [],
                        'docstring': ast.get_docstring(node)
                    }
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info['methods'].append(item.name)
                    classes.append(class_info)
            
            # Extract additional patterns
            patterns = self._extract_python_patterns(tree)
            
            return {
                'imports': imports,
                'functions': functions,
                'classes': classes,
                'patterns': patterns
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Python file {file_path}: {e}")
            return self._fallback_analysis(content)
    
    async def _analyze_javascript_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript file"""
        try:
            # Use Node.js parser if available
            result = subprocess.run(
                ['node', 'parse_js.mjs', file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return self._fallback_js_analysis(content)
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_js_analysis(content)
    
    def _fallback_js_analysis(self, content: str) -> Dict[str, Any]:
        """Fallback JavaScript analysis using regex"""
        imports = re.findall(r'import\s+(?:{[^}]+}|[\w\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        requires = re.findall(r'require\s*\([\'"]([^\'"]+)[\'"]\)', content)
        functions = re.findall(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[\w]+)\s*=>)', content)
        classes = re.findall(r'class\s+(\w+)', content)
        
        return {
            'imports': imports + requires,
            'functions': [f for f in sum(functions, ()) if f],
            'classes': classes,
            'patterns': []
        }
    
    async def _analyze_module_context(
        self, 
        file_path: str, 
        base_context: CodeContext
    ) -> Dict[str, Any]:
        """Analyze module-level context"""
        module_dir = Path(file_path).parent
        module_files = []
        shared_imports = defaultdict(int)
        shared_patterns = []
        
        # Analyze sibling files
        for file in module_dir.glob(f"*.{base_context.language[:2]}*"):
            if file.is_file() and str(file) != file_path:
                module_files.append(str(file))
                
                # Quick analysis of sibling files
                try:
                    content = self._read_file(str(file))
                    analysis = await self._analyze_file(str(file), content, base_context.language)
                    
                    # Track shared imports
                    for imp in analysis.get('imports', []):
                        shared_imports[imp] += 1
                    
                except Exception as e:
                    logger.debug(f"Error analyzing sibling file {file}: {e}")
        
        # Find most common imports in module
        common_imports = [
            imp for imp, count in shared_imports.items() 
            if count >= len(module_files) * 0.3  # Used in 30%+ of files
        ]
        
        return {
            'module_files': module_files,
            'common_imports': common_imports,
            'module_size': len(module_files),
            'module_path': str(module_dir),
            'is_test_module': 'test' in module_dir.name.lower(),
            'module_type': self._detect_module_type(module_dir.name)
        }
    
    async def _analyze_project_context(
        self, 
        file_path: str, 
        base_context: CodeContext
    ) -> Dict[str, Any]:
        """Analyze project-level context"""
        project_root = Path(base_context.project_root) if base_context.project_root else self._find_project_root(file_path)
        
        project_info = {
            'project_root': str(project_root),
            'project_type': await self._detect_project_type(project_root),
            'dependencies': await self._get_project_dependencies(project_root, base_context.language),
            'coding_standards': await self._detect_coding_standards(project_root),
            'test_framework': await self._detect_test_framework(project_root, base_context.language),
            'build_system': await self._detect_build_system(project_root),
            'common_patterns': []
        }
        
        return project_info
    
    async def _analyze_cross_project_patterns(
        self, 
        context: CodeContext
    ) -> List[str]:
        """Identify patterns used across multiple projects"""
        # This would integrate with a pattern database
        # For now, return common patterns based on framework
        patterns = []
        
        if context.framework:
            framework_patterns = {
                'django': ['MVT', 'middleware', 'orm', 'signals'],
                'fastapi': ['dependency-injection', 'async', 'pydantic-models'],
                'react': ['component-based', 'hooks', 'state-management'],
                'angular': ['dependency-injection', 'services', 'observables'],
                'spring': ['dependency-injection', 'aop', 'mvc'],
            }
            patterns.extend(framework_patterns.get(context.framework.lower(), []))
        
        # Add language-specific patterns
        language_patterns = {
            'python': ['decorator', 'context-manager', 'generator'],
            'javascript': ['promise', 'async-await', 'closure'],
            'java': ['factory', 'singleton', 'observer'],
            'go': ['goroutine', 'channel', 'interface'],
        }
        patterns.extend(language_patterns.get(context.language.lower(), []))
        
        return patterns
    
    async def _build_dependency_graph(
        self, 
        file_path: str, 
        context: CodeContext,
        depth: int
    ) -> Dict[str, List[str]]:
        """Build dependency graph starting from current file"""
        graph = defaultdict(list)
        visited = set()
        
        async def analyze_dependencies(path: str, current_depth: int):
            if current_depth >= depth or path in visited:
                return
            
            visited.add(path)
            
            try:
                content = self._read_file(path)
                analysis = await self._analyze_file(path, content, context.language)
                
                # Extract file dependencies from imports
                for imp in analysis.get('imports', []):
                    dep_path = self._resolve_import_path(imp, path, context.project_root)
                    if dep_path and os.path.exists(dep_path):
                        graph[path].append(dep_path)
                        await analyze_dependencies(dep_path, current_depth + 1)
                        
            except Exception as e:
                logger.debug(f"Error analyzing dependencies for {path}: {e}")
        
        await analyze_dependencies(file_path, 0)
        return dict(graph)
    
    async def _detect_architectural_patterns(
        self,
        base_context: CodeContext,
        module_context: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> List[str]:
        """Detect architectural patterns in use"""
        patterns = []
        
        # Check for MVC/MVP/MVVM patterns
        if any(name in base_context.current_file.lower() for name in ['controller', 'view', 'model']):
            patterns.append('MVC')
        
        # Check for microservices
        if project_context.get('project_type') == 'microservice':
            patterns.append('microservices')
        
        # Check for layered architecture
        if any(layer in base_context.current_file for layer in ['service', 'repository', 'dto', 'dao']):
            patterns.append('layered-architecture')
        
        # Check for event-driven
        if any(term in str(base_context.imports) for term in ['event', 'message', 'queue', 'pubsub']):
            patterns.append('event-driven')
        
        return list(set(patterns))
    
    def _calculate_context_weights(
        self,
        base_context: CodeContext,
        module_context: Dict[str, Any],
        project_context: Dict[str, Any]
    ) -> Dict[ContextLevel, float]:
        """Calculate relevance weights for each context level"""
        weights = {
            ContextLevel.FILE: self.config.get('file_weight', 1.0),
            ContextLevel.MODULE: self.config.get('module_weight', 0.7),
            ContextLevel.PROJECT: self.config.get('project_weight', 0.5),
            ContextLevel.CROSS_PROJECT: self.config.get('cross_project_weight', 0.3)
        }
        
        # Adjust weights based on context
        # Boost module weight if many shared imports
        if module_context.get('common_imports', []):
            weights[ContextLevel.MODULE] *= 1.2
        
        # Boost project weight if in core module
        if 'core' in base_context.current_file.lower() or 'common' in base_context.current_file.lower():
            weights[ContextLevel.PROJECT] *= 1.3
        
        # Normalize weights
        total = sum(weights.values())
        return {k: v/total for k, v in weights.items()}
    
    # Helper methods
    
    def _is_cached(self, file_path: str) -> bool:
        """Check if context is cached and still valid"""
        if not self.config.get('cache_enabled', True):
            return False
            
        if file_path not in self.cache:
            return False
            
        _, cached_time = self.cache[file_path]
        ttl = timedelta(seconds=self.config.get('cache_ttl_seconds', 300))
        
        return datetime.utcnow() - cached_time < ttl
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'objc',
            '.mm': 'objcpp',
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'unknown')
    
    def _read_file(self, file_path: str) -> str:
        """Read file content with encoding detection"""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
                
        # If all fail, read as binary and decode with errors ignored
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')
    
    async def _get_git_info(self, file_path: str) -> Dict[str, Any]:
        """Get git information for file"""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=os.path.dirname(file_path),
                capture_output=True,
                text=True
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
            
            # Get recent changes
            recent_changes = []
            if self.config.get('include_git_history', True):
                days = self.config.get('git_history_days', 7)
                log_result = subprocess.run(
                    ['git', 'log', f'--since={days} days ago', '--pretty=format:%H|%an|%ae|%ad|%s', '--', file_path],
                    cwd=os.path.dirname(file_path),
                    capture_output=True,
                    text=True
                )
                
                if log_result.returncode == 0:
                    for line in log_result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split('|')
                            if len(parts) >= 5:
                                recent_changes.append({
                                    'commit': parts[0],
                                    'author': parts[1],
                                    'email': parts[2],
                                    'date': parts[3],
                                    'message': parts[4]
                                })
            
            return {
                'branch': branch,
                'recent_changes': recent_changes
            }
            
        except Exception as e:
            logger.debug(f"Error getting git info for {file_path}: {e}")
            return {}
    
    async def _detect_framework(
        self, 
        file_path: str, 
        language: str, 
        imports: List[str]
    ) -> Optional[str]:
        """Detect framework from imports and project structure"""
        framework_indicators = {
            'python': {
                'django': ['django', 'rest_framework'],
                'flask': ['flask'],
                'fastapi': ['fastapi', 'pydantic'],
                'pytest': ['pytest'],
                'tensorflow': ['tensorflow', 'keras'],
                'pytorch': ['torch', 'torchvision'],
            },
            'javascript': {
                'react': ['react', 'react-dom'],
                'angular': ['@angular/core'],
                'vue': ['vue'],
                'express': ['express'],
                'nestjs': ['@nestjs/core'],
                'nextjs': ['next'],
            },
            'typescript': {
                'react': ['react', 'react-dom'],
                'angular': ['@angular/core'],
                'vue': ['vue'],
                'express': ['express'],
                'nestjs': ['@nestjs/core'],
                'nextjs': ['next'],
            },
            'java': {
                'spring': ['springframework'],
                'hibernate': ['hibernate'],
                'junit': ['junit', 'jupiter'],
            },
        }
        
        indicators = framework_indicators.get(language, {})
        imports_str = ' '.join(imports).lower()
        
        for framework, keywords in indicators.items():
            if any(keyword in imports_str for keyword in keywords):
                return framework
                
        return None
    
    def _find_project_root(self, file_path: str) -> str:
        """Find project root directory"""
        markers = [
            '.git', 'package.json', 'requirements.txt', 'setup.py',
            'pom.xml', 'build.gradle', 'go.mod', 'Cargo.toml',
            'CMakeLists.txt', 'Makefile', '.project'
        ]
        
        current = Path(file_path).parent
        
        while current != current.parent:
            for marker in markers:
                if (current / marker).exists():
                    return str(current)
            current = current.parent
            
        return str(Path(file_path).parent)
    
    def _get_decorator_name(self, node) -> str:
        """Extract decorator name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{node.value.id if isinstance(node.value, ast.Name) else '?'}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return "unknown"
    
    def _get_base_name(self, node) -> str:
        """Extract base class name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{node.value.id if isinstance(node.value, ast.Name) else '?'}.{node.attr}"
        return "unknown"
    
    def _extract_python_patterns(self, tree: ast.AST) -> List[str]:
        """Extract common Python patterns from AST"""
        patterns = []
        
        for node in ast.walk(tree):
            # Decorator pattern
            if isinstance(node, ast.FunctionDef) and node.decorator_list:
                patterns.append('decorator')
            
            # Context manager pattern
            if isinstance(node, ast.With):
                patterns.append('context-manager')
            
            # Generator pattern
            if isinstance(node, ast.FunctionDef):
                for n in ast.walk(node):
                    if isinstance(n, ast.Yield):
                        patterns.append('generator')
                        break
            
            # Async pattern
            if isinstance(node, (ast.AsyncFunctionDef, ast.AsyncWith, ast.AsyncFor)):
                patterns.append('async')
        
        return list(set(patterns))
    
    def _resolve_import_path(
        self, 
        import_name: str, 
        current_file: str, 
        project_root: Optional[str]
    ) -> Optional[str]:
        """Resolve import to actual file path"""
        # This is simplified - real implementation would handle various import styles
        if import_name.startswith('.'):
            # Relative import
            base_dir = Path(current_file).parent
            parts = import_name.split('.')
            level = len([p for p in parts if not p]) - 1
            
            for _ in range(level):
                base_dir = base_dir.parent
                
            module_parts = [p for p in parts if p]
            potential_path = base_dir / '/'.join(module_parts)
            
            for ext in ['.py', '.js', '.ts', '']:
                full_path = f"{potential_path}{ext}"
                if os.path.exists(full_path):
                    return full_path
        else:
            # Absolute import - check in project
            if project_root:
                parts = import_name.split('.')
                potential_path = Path(project_root) / '/'.join(parts)
                
                for ext in ['.py', '.js', '.ts', '']:
                    full_path = f"{potential_path}{ext}"
                    if os.path.exists(full_path):
                        return full_path
        
        return None
    
    async def _detect_project_type(self, project_root: Path) -> str:
        """Detect project type from structure and files"""
        # Check for microservice indicators
        if (project_root / 'Dockerfile').exists() or (project_root / 'docker-compose.yml').exists():
            if any((project_root / name).exists() for name in ['api', 'service', 'services']):
                return 'microservice'
        
        # Check for monolith indicators
        if (project_root / 'manage.py').exists():  # Django
            return 'monolith'
        
        # Check for library/package
        if (project_root / 'setup.py').exists() or (project_root / 'pyproject.toml').exists():
            return 'library'
        
        # Check for CLI tool
        if any((project_root / name).exists() for name in ['cli.py', 'main.py', '__main__.py']):
            return 'cli'
        
        return 'application'
    
    async def _get_project_dependencies(self, project_root: Path, language: str) -> List[str]:
        """Get project dependencies based on language"""
        dependencies = []
        
        dependency_files = {
            'python': ['requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py'],
            'javascript': ['package.json'],
            'typescript': ['package.json'],
            'java': ['pom.xml', 'build.gradle'],
            'go': ['go.mod'],
            'rust': ['Cargo.toml'],
        }
        
        for dep_file in dependency_files.get(language, []):
            dep_path = project_root / dep_file
            if dep_path.exists():
                try:
                    content = dep_path.read_text()
                    # Simple extraction - real implementation would parse properly
                    if dep_file == 'requirements.txt':
                        dependencies = [line.split('==')[0].strip() 
                                      for line in content.splitlines() 
                                      if line.strip() and not line.startswith('#')]
                    elif dep_file == 'package.json':
                        import json
                        data = json.loads(content)
                        dependencies = list(data.get('dependencies', {}).keys())
                        dependencies.extend(list(data.get('devDependencies', {}).keys()))
                    # Add more parsers as needed
                except Exception as e:
                    logger.debug(f"Error parsing {dep_file}: {e}")
                break
        
        return dependencies
    
    async def _detect_coding_standards(self, project_root: Path) -> Dict[str, Any]:
        """Detect coding standards and linting configuration"""
        standards = {}
        
        # Python
        for config_file in ['.flake8', 'setup.cfg', 'pyproject.toml', '.pylintrc']:
            if (project_root / config_file).exists():
                standards['python_linter'] = config_file
                break
        
        # JavaScript/TypeScript
        for config_file in ['.eslintrc', '.eslintrc.json', '.eslintrc.js', 'eslint.config.js']:
            if (project_root / config_file).exists():
                standards['js_linter'] = config_file
                break
        
        # Prettier
        if (project_root / '.prettierrc').exists():
            standards['formatter'] = 'prettier'
        
        # EditorConfig
        if (project_root / '.editorconfig').exists():
            standards['editor_config'] = True
        
        return standards
    
    async def _detect_test_framework(self, project_root: Path, language: str) -> Optional[str]:
        """Detect testing framework in use"""
        test_indicators = {
            'python': {
                'pytest': ['pytest.ini', 'conftest.py', 'pytest.config'],
                'unittest': ['test_*.py'],
                'nose': ['nose.cfg'],
            },
            'javascript': {
                'jest': ['jest.config.js', 'jest.config.json'],
                'mocha': ['mocha.opts', '.mocharc.json'],
                'jasmine': ['jasmine.json'],
                'vitest': ['vitest.config.js', 'vitest.config.ts'],
            },
            'java': {
                'junit': ['*Test.java', '*Tests.java'],
                'testng': ['testng.xml'],
            },
        }
        
        indicators = test_indicators.get(language, {})
        
        for framework, files in indicators.items():
            for file_pattern in files:
                if '*' in file_pattern:
                    if list(project_root.rglob(file_pattern)):
                        return framework
                elif (project_root / file_pattern).exists():
                    return framework
        
        return None
    
    async def _detect_build_system(self, project_root: Path) -> Optional[str]:
        """Detect build system in use"""
        build_files = {
            'npm': 'package.json',
            'yarn': 'yarn.lock',
            'pnpm': 'pnpm-lock.yaml',
            'pip': 'requirements.txt',
            'poetry': 'poetry.lock',
            'maven': 'pom.xml',
            'gradle': 'build.gradle',
            'make': 'Makefile',
            'cmake': 'CMakeLists.txt',
            'cargo': 'Cargo.toml',
            'go': 'go.mod',
        }
        
        for system, file in build_files.items():
            if (project_root / file).exists():
                return system
        
        return None
    
    def _detect_module_type(self, module_name: str) -> str:
        """Detect module type from naming conventions"""
        module_lower = module_name.lower()
        
        if 'test' in module_lower:
            return 'test'
        elif any(name in module_lower for name in ['model', 'schema', 'entity']):
            return 'model'
        elif any(name in module_lower for name in ['view', 'ui', 'component']):
            return 'view'
        elif any(name in module_lower for name in ['controller', 'handler', 'route']):
            return 'controller'
        elif any(name in module_lower for name in ['service', 'business', 'logic']):
            return 'service'
        elif any(name in module_lower for name in ['util', 'helper', 'common']):
            return 'utility'
        elif any(name in module_lower for name in ['config', 'settings']):
            return 'configuration'
        else:
            return 'general'
    
    def _fallback_analysis(self, content: str) -> Dict[str, Any]:
        """Generic fallback analysis for any language"""
        # Simple regex-based extraction
        imports = []
        functions = []
        classes = []
        
        # Common import patterns
        import_patterns = [
            r'import\s+([^\s;]+)',
            r'from\s+([^\s]+)\s+import',
            r'#include\s+[<"]([^>"]+)[>"]',
            r'using\s+([^\s;]+);',
        ]
        
        for pattern in import_patterns:
            imports.extend(re.findall(pattern, content))
        
        # Function patterns
        function_patterns = [
            r'def\s+(\w+)\s*\(',
            r'function\s+(\w+)\s*\(',
            r'func\s+(\w+)\s*\(',
            r'(?:public|private|protected)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*{',
        ]
        
        for pattern in function_patterns:
            functions.extend(re.findall(pattern, content))
        
        # Class patterns
        class_patterns = [
            r'class\s+(\w+)',
            r'struct\s+(\w+)',
            r'interface\s+(\w+)',
        ]
        
        for pattern in class_patterns:
            classes.extend(re.findall(pattern, content))
        
        return {
            'imports': list(set(imports)),
            'functions': list(set(functions)),
            'classes': list(set(classes)),
            'patterns': []
        }
    
    async def _analyze_java_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze Java file"""
        # For now, use fallback - could integrate with Java parser
        return self._fallback_analysis(content)
    
    async def _analyze_go_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze Go file"""
        # For now, use fallback - could integrate with Go parser
        return self._fallback_analysis(content)
    
    async def _analyze_rust_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze Rust file"""
        # For now, use fallback - could integrate with Rust parser
        return self._fallback_analysis(content)
    
    async def _analyze_generic_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Generic file analysis"""
        return self._fallback_analysis(content)