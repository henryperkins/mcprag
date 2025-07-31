"""
Context-aware MCP tool for intelligent assistance
"""

import logging
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

from ..context.hierarchical_context import HierarchicalContextAnalyzer
from ..context.session_tracker import SessionTracker
from ..code_understanding.ast_analyzer import ASTAnalyzer
from ..code_understanding.dependency_graph import DependencyGraphBuilder
from ..core.models import FileContext, ModuleContext, ProjectContext

logger = logging.getLogger(__name__)


class ContextAwareTool:
    """
    MCP tool providing context-aware operations
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context_analyzer = HierarchicalContextAnalyzer(config)
        self.session_tracker = SessionTracker(config)
        self.ast_analyzer = ASTAnalyzer(config)
        self.dep_builder = DependencyGraphBuilder(config)
        
    async def analyze_context(
        self,
        file_path: str,
        include_dependencies: bool = True,
        depth: int = 2,
        include_imports: bool = True,
        include_git_history: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze hierarchical context for a file
        
        Args:
            file_path: Path to analyze
            include_dependencies: Include dependency analysis
            depth: Depth of context analysis (1-3)
            include_imports: Include import analysis
            include_git_history: Include recent git changes
            
        Returns:
            Comprehensive context analysis
        """
        try:
            # Get hierarchical context
            context = await self.context_analyzer.analyze(
                file_path=file_path,
                depth=depth
            )
            
            # Build response
            result = {
                'file': file_path,
                'language': context.file_context.language,
                'module': context.module_context.module_path,
                'project': {
                    'name': context.project_context.name,
                    'root': context.project_context.root_path,
                    'type': context.project_context.project_type
                },
                'context_depth': depth,
                'timestamp': context.timestamp.isoformat()
            }
            
            # Add imports if requested
            if include_imports:
                result['imports'] = {
                    'direct': context.file_context.imports,
                    'indirect': await self._get_indirect_imports(context)
                }
            
            # Add dependencies if requested
            if include_dependencies:
                dep_graph = await self.dep_builder.build_graph(file_path)
                result['dependencies'] = {
                    'internal': dep_graph.get_internal_dependencies(file_path),
                    'external': dep_graph.get_external_dependencies(file_path),
                    'graph_size': len(dep_graph.nodes)
                }
            
            # Add git history if requested
            if include_git_history:
                result['git_history'] = await self._get_git_history(file_path)
            
            # Add related files
            result['related_files'] = await self._find_related_files(context)
            
            # Add context summary
            result['summary'] = self._generate_context_summary(context, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Context analysis error: {e}")
            return {
                'error': str(e),
                'file': file_path
            }
    
    async def suggest_improvements(
        self,
        file_path: str,
        focus: Optional[str] = None,
        include_examples: bool = True
    ) -> Dict[str, Any]:
        """
        Suggest improvements based on context analysis
        
        Args:
            file_path: File to analyze
            focus: Specific area to focus on (e.g., 'performance', 'readability', 'testing')
            include_examples: Include code examples
            
        Returns:
            Categorized improvement suggestions
        """
        try:
            # Analyze file
            context = await self.context_analyzer.analyze(file_path)
            ast_info = await self.ast_analyzer.analyze_file(file_path)
            
            suggestions = []
            
            # Check for missing imports
            if missing := await self._find_missing_imports(context, ast_info):
                suggestions.append({
                    'type': 'missing_imports',
                    'items': missing,
                    'priority': 'high',
                    'description': 'Add missing imports for undefined references'
                })
            
            # Check for unused imports
            if unused := await self._find_unused_imports(context, ast_info):
                suggestions.append({
                    'type': 'unused_imports',
                    'items': unused,
                    'priority': 'medium',
                    'description': 'Remove unused imports to clean up code'
                })
            
            # Pattern suggestions
            if patterns := await self._suggest_patterns(context, ast_info, focus):
                suggestions.append({
                    'type': 'design_patterns',
                    'items': patterns,
                    'priority': 'low',
                    'description': 'Consider using these design patterns'
                })
            
            # Code quality issues
            if quality_issues := await self._check_code_quality(ast_info, focus):
                suggestions.append({
                    'type': 'code_quality',
                    'items': quality_issues,
                    'priority': 'medium',
                    'description': 'Address code quality issues'
                })
            
            # Testing suggestions
            if test_suggestions := await self._suggest_tests(context, ast_info):
                suggestions.append({
                    'type': 'testing',
                    'items': test_suggestions,
                    'priority': 'medium',
                    'description': 'Add or improve test coverage'
                })
            
            # Add examples if requested
            if include_examples:
                for suggestion in suggestions:
                    suggestion['examples'] = await self._get_examples_for_suggestion(
                        suggestion,
                        context
                    )
            
            return {
                'file': file_path,
                'total_suggestions': len(suggestions),
                'suggestions': suggestions,
                'focus_area': focus,
                'context_summary': {
                    'functions': len(ast_info.get('functions', [])),
                    'classes': len(ast_info.get('classes', [])),
                    'complexity': ast_info.get('complexity', 'unknown')
                }
            }
            
        except Exception as e:
            logger.error(f"Improvement suggestion error: {e}")
            return {
                'error': str(e),
                'file': file_path
            }
    
    async def find_similar_code(
        self,
        file_path: str,
        scope: str = "project",
        threshold: float = 0.7,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Find similar code patterns in the codebase
        
        Args:
            file_path: Reference file
            scope: Search scope ('project', 'module', 'all')
            threshold: Similarity threshold (0-1)
            max_results: Maximum results to return
            
        Returns:
            Similar code patterns with locations
        """
        try:
            # Analyze reference file
            context = await self.context_analyzer.analyze(file_path)
            ast_info = await self.ast_analyzer.analyze_file(file_path)
            
            # Extract patterns
            patterns = await self._extract_code_patterns(ast_info)
            
            # Search for similar patterns
            similar_files = []
            search_paths = self._get_search_paths(context, scope)
            
            for search_path in search_paths:
                if search_path == file_path:
                    continue
                
                try:
                    other_ast = await self.ast_analyzer.analyze_file(search_path)
                    similarity = await self._calculate_similarity(ast_info, other_ast)
                    
                    if similarity >= threshold:
                        similar_files.append({
                            'file': search_path,
                            'similarity': similarity,
                            'patterns': await self._find_matching_patterns(patterns, other_ast),
                            'potential_refactor': similarity > 0.9
                        })
                except Exception as e:
                    logger.debug(f"Error analyzing {search_path}: {e}")
            
            # Sort by similarity
            similar_files.sort(key=lambda x: x['similarity'], reverse=True)
            
            return {
                'reference_file': file_path,
                'scope': scope,
                'threshold': threshold,
                'total_found': len(similar_files),
                'similar_code': similar_files[:max_results],
                'refactoring_opportunities': [
                    f for f in similar_files if f['potential_refactor']
                ][:5]
            }
            
        except Exception as e:
            logger.error(f"Similar code search error: {e}")
            return {
                'error': str(e),
                'file': file_path
            }
    
    async def track_changes(
        self,
        file_path: str,
        event_type: str = "edit",
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track file changes for context awareness
        
        Args:
            file_path: File that changed
            event_type: Type of change ('edit', 'create', 'delete', 'rename')
            content: New content (for edit/create)
            
        Returns:
            Tracking confirmation with impact analysis
        """
        try:
            # Track the change
            await self.session_tracker.track_file_change(
                file_path=file_path,
                event_type=event_type,
                content=content
            )
            
            # Analyze impact
            impact = await self._analyze_change_impact(file_path, event_type)
            
            return {
                'tracked': True,
                'file': file_path,
                'event': event_type,
                'timestamp': impact['timestamp'],
                'impact': {
                    'affected_files': impact['affected_files'],
                    'rebuild_required': impact['rebuild_required'],
                    'test_files': impact['test_files']
                },
                'session_stats': await self.session_tracker.get_session_stats()
            }
            
        except Exception as e:
            logger.error(f"Change tracking error: {e}")
            return {
                'tracked': False,
                'error': str(e),
                'file': file_path
            }
    
    async def _get_indirect_imports(self, context: Any) -> List[str]:
        """Get indirect imports through dependencies"""
        indirect = set()
        for imp in context.file_context.imports:
            dep_context = await self.context_analyzer.analyze(imp, depth=1)
            indirect.update(dep_context.file_context.imports)
        return list(indirect - set(context.file_context.imports))
    
    async def _get_git_history(self, file_path: str) -> Dict[str, Any]:
        """Get recent git history for file"""
        # Simplified - would integrate with git
        return {
            'recent_commits': [],
            'last_modified': None,
            'authors': []
        }
    
    async def _find_related_files(self, context: Any) -> List[Dict[str, str]]:
        """Find files related to the current context"""
        related = []
        
        # Test files
        if test_file := self._find_test_file(context.file_context.file_path):
            related.append({
                'type': 'test',
                'path': test_file,
                'relationship': 'tests'
            })
        
        # Import relationships
        for imp in context.file_context.imports[:5]:
            related.append({
                'type': 'import',
                'path': imp,
                'relationship': 'imports'
            })
        
        # Same module files
        module_files = await self._find_module_files(context.module_context)
        for mf in module_files[:3]:
            if mf != context.file_context.file_path:
                related.append({
                    'type': 'module',
                    'path': mf,
                    'relationship': 'same_module'
                })
        
        return related
    
    def _generate_context_summary(self, context: Any, analysis: Dict) -> str:
        """Generate human-readable context summary"""
        summary_parts = []
        
        # File info
        summary_parts.append(
            f"File '{Path(context.file_context.file_path).name}' "
            f"in module '{context.module_context.module_name}'"
        )
        
        # Dependencies
        if 'dependencies' in analysis:
            dep_count = len(analysis['dependencies']['internal']) + \
                       len(analysis['dependencies']['external'])
            summary_parts.append(f"has {dep_count} dependencies")
        
        # Imports
        if 'imports' in analysis:
            import_count = len(analysis['imports']['direct'])
            summary_parts.append(f"imports {import_count} modules")
        
        # Related files
        if 'related_files' in analysis:
            summary_parts.append(f"relates to {len(analysis['related_files'])} files")
        
        return ". ".join(summary_parts) + "."
    
    async def _find_missing_imports(self, context: Any, ast_info: Dict) -> List[Dict]:
        """Find potentially missing imports"""
        # Simplified implementation
        return []
    
    async def _find_unused_imports(self, context: Any, ast_info: Dict) -> List[str]:
        """Find unused imports"""
        # Simplified implementation
        return []
    
    async def _suggest_patterns(self, context: Any, ast_info: Dict, focus: str) -> List[Dict]:
        """Suggest design patterns"""
        patterns = []
        
        # Example pattern suggestions based on code structure
        if len(ast_info.get('classes', [])) > 5:
            patterns.append({
                'pattern': 'Factory Pattern',
                'reason': 'Multiple related classes could benefit from factory'
            })
        
        return patterns
    
    async def _check_code_quality(self, ast_info: Dict, focus: str) -> List[Dict]:
        """Check code quality issues"""
        issues = []
        
        # Example checks
        for func in ast_info.get('functions', []):
            if func.get('complexity', 0) > 10:
                issues.append({
                    'type': 'high_complexity',
                    'location': func['name'],
                    'severity': 'medium',
                    'suggestion': 'Consider breaking down this function'
                })
        
        return issues
    
    async def _suggest_tests(self, context: Any, ast_info: Dict) -> List[Dict]:
        """Suggest testing improvements"""
        suggestions = []
        
        # Check for untested functions
        for func in ast_info.get('functions', []):
            if not func.get('has_test', False):
                suggestions.append({
                    'function': func['name'],
                    'test_type': 'unit',
                    'priority': 'high' if func.get('is_public', True) else 'medium'
                })
        
        return suggestions
    
    async def _get_examples_for_suggestion(
        self, 
        suggestion: Dict, 
        context: Any
    ) -> List[Dict]:
        """Get code examples for suggestions"""
        # Simplified - would search for examples
        return []
    
    async def _extract_code_patterns(self, ast_info: Dict) -> List[Dict]:
        """Extract code patterns from AST"""
        patterns = []
        
        # Extract function patterns
        for func in ast_info.get('functions', []):
            patterns.append({
                'type': 'function',
                'signature': func.get('signature', ''),
                'complexity': func.get('complexity', 0)
            })
        
        return patterns
    
    def _get_search_paths(self, context: Any, scope: str) -> List[str]:
        """Get paths to search based on scope"""
        if scope == 'module':
            return context.module_context.files
        elif scope == 'project':
            return []  # Would enumerate project files
        else:
            return []  # Would enumerate all indexed files
    
    async def _calculate_similarity(self, ast1: Dict, ast2: Dict) -> float:
        """Calculate similarity between two AST structures"""
        # Simplified similarity calculation
        return 0.0
    
    async def _find_matching_patterns(self, patterns: List[Dict], ast_info: Dict) -> List[Dict]:
        """Find patterns matching in AST"""
        return []
    
    async def _analyze_change_impact(self, file_path: str, event_type: str) -> Dict:
        """Analyze impact of file change"""
        return {
            'timestamp': 'now',
            'affected_files': [],
            'rebuild_required': False,
            'test_files': []
        }
    
    def _find_test_file(self, file_path: str) -> Optional[str]:
        """Find test file for given file"""
        path = Path(file_path)
        test_name = f"test_{path.name}"
        test_path = path.parent / test_name
        return str(test_path) if test_path.exists() else None
    
    async def _find_module_files(self, module_context: Any) -> List[str]:
        """Find all files in module"""
        return module_context.files if hasattr(module_context, 'files') else []