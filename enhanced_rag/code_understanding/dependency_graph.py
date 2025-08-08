"""
Dependency Graph Builder for code understanding
Builds and analyzes dependency graphs for code files and projects
"""

import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import networkx as nx
from dataclasses import dataclass

from .ast_analyzer import ASTAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class DependencyNode:
    """Represents a node in the dependency graph"""
    name: str
    type: str  # 'function', 'class', 'module', 'file'
    file_path: str
    metadata: Dict[str, Any]


@dataclass
class DependencyEdge:
    """Represents an edge (dependency) in the graph"""
    source: str
    target: str
    type: str  # 'calls', 'imports', 'inherits', 'uses'
    metadata: Dict[str, Any]


class DependencyGraphBuilder:
    """
    Builds dependency graphs for code analysis

    This class creates graphs showing relationships between:
    - Functions (call graph)
    - Classes (inheritance and usage)
    - Modules (import dependencies)
    - Files (cross-file dependencies)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ast_analyzer = ASTAnalyzer(config)

        # Initialize graph
        self.graph = nx.DiGraph()

        # Cache for analyzed files
        self._file_cache: Dict[str, Dict[str, Any]] = {}

        # Node ID mappings
        self._node_ids: Dict[str, str] = {}

    async def build_file_graph(self, file_path: str) -> nx.DiGraph:
        """
        Build dependency graph for a single file

        Args:
            file_path: Path to the file to analyze

        Returns:
            NetworkX directed graph with dependencies
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.warning(f"File not found: {file_path}")
            return nx.DiGraph()

        # Clear existing graph
        self.graph.clear()

        # Analyze file
        analysis = await self.ast_analyzer.analyze_file(file_path)
        if not analysis or analysis['language'] == 'unknown':
            return self.graph

        # Add file node
        file_node_id = self._get_node_id('file', file_path, '')
        self.graph.add_node(
            file_node_id,
            name=file_path_obj.name,
            type='file',
            file_path=file_path,
            language=analysis['language']
        )

        # Add function nodes and internal dependencies
        await self._add_function_nodes(analysis, file_path)

        # Add class nodes and relationships
        await self._add_class_nodes(analysis, file_path)

        # Add import dependencies
        await self._add_import_dependencies(analysis, file_path)

        return self.graph

    async def build_project_graph(
        self,
        project_root: str,
        file_patterns: Optional[List[str]] = None
    ) -> nx.DiGraph:
        """
        Build dependency graph for an entire project

        Args:
            project_root: Root directory of the project
            file_patterns: List of file patterns to include (e.g., ['*.py', '*.js'])

        Returns:
            NetworkX directed graph with project-wide dependencies
        """
        project_root_path = Path(project_root)
        if not project_root_path.exists():
            logger.warning(f"Project root not found: {project_root}")
            return nx.DiGraph()

        # Clear existing graph
        self.graph.clear()

        # Default file patterns
        if not file_patterns:
            file_patterns = ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx']

        # Find all matching files
        files_to_analyze = []
        for pattern in file_patterns:
            files_to_analyze.extend(project_root_path.rglob(pattern))

        logger.info(f"Analyzing {len(files_to_analyze)} files in {project_root}")

        # First pass: analyze all files and add nodes
        file_analyses = {}
        for file_path in files_to_analyze:
            try:
                analysis = await self.ast_analyzer.analyze_file(str(file_path))
                if analysis and analysis['language'] != 'unknown':
                    file_analyses[str(file_path)] = analysis

                    # Add file node
                    file_node_id = self._get_node_id('file', str(file_path), '')
                    self.graph.add_node(
                        file_node_id,
                        name=file_path.name,
                        type='file',
                        file_path=str(file_path),
                        language=analysis['language']
                    )

                    # Add function and class nodes
                    await self._add_function_nodes(analysis, str(file_path))
                    await self._add_class_nodes(analysis, str(file_path))

            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")

        # Second pass: add cross-file dependencies
        for file_path, analysis in file_analyses.items():
            await self._add_cross_file_dependencies(analysis, file_path, file_analyses)

        return self.graph

    async def _add_function_nodes(self, analysis: Dict[str, Any], file_path: str):
        """Add function nodes and their internal dependencies"""
        for func in analysis.get('functions', []):
            func_node_id = self._get_node_id('function', file_path, func['name'])

            self.graph.add_node(
                func_node_id,
                name=func['name'],
                type='function',
                file_path=file_path,
                signature=func.get('signature', ''),
                start_line=func.get('start_line'),
                end_line=func.get('end_line'),
                is_async=func.get('is_async', False),
                docstring=func.get('docstring', '')
            )

            # Link function to its file
            file_node_id = self._get_node_id('file', file_path, '')
            self.graph.add_edge(
                file_node_id,
                func_node_id,
                type='contains'
            )

            # Add dependencies (simplified - would need more sophisticated analysis)
            for dep in analysis.get('dependencies', []):
                # Check if dependency is another function in the same file
                dep_name = dep.split('.')[-1]
                for other_func in analysis.get('functions', []):
                    if other_func['name'] == dep_name and other_func['name'] != func['name']:
                        dep_node_id = self._get_node_id('function', file_path, dep_name)
                        self.graph.add_edge(
                            func_node_id,
                            dep_node_id,
                            type='calls'
                        )

    async def _add_class_nodes(self, analysis: Dict[str, Any], file_path: str):
        """Add class nodes and their relationships"""
        for cls in analysis.get('classes', []):
            class_node_id = self._get_node_id('class', file_path, cls['name'])

            self.graph.add_node(
                class_node_id,
                name=cls['name'],
                type='class',
                file_path=file_path,
                start_line=cls.get('start_line'),
                end_line=cls.get('end_line'),
                methods=[m['name'] for m in cls.get('methods', [])],
                bases=cls.get('bases', [])
            )

            # Link class to its file
            file_node_id = self._get_node_id('file', file_path, '')
            self.graph.add_edge(
                file_node_id,
                class_node_id,
                type='contains'
            )

            # Add method nodes
            for method in cls.get('methods', []):
                method_node_id = self._get_node_id('method', file_path, f"{cls['name']}.{method['name']}")

                self.graph.add_node(
                    method_node_id,
                    name=method['name'],
                    type='method',
                    class_name=cls['name'],
                    file_path=file_path,
                    is_async=method.get('is_async', False)
                )

                # Link method to its class
                self.graph.add_edge(
                    class_node_id,
                    method_node_id,
                    type='contains'
                )

    async def _add_import_dependencies(self, analysis: Dict[str, Any], file_path: str):
        """Add import dependencies for a file"""
        file_node_id = self._get_node_id('file', file_path, '')

        for imp in analysis.get('imports', []):
            # Create module node for import
            module_node_id = self._get_node_id('module', '', imp)

            if module_node_id not in self.graph:
                self.graph.add_node(
                    module_node_id,
                    name=imp,
                    type='module',
                    external=True  # Assume external unless found in project
                )

            # Add import edge
            self.graph.add_edge(
                file_node_id,
                module_node_id,
                type='imports'
            )

    async def _add_cross_file_dependencies(
        self,
        analysis: Dict[str, Any],
        file_path: str,
        all_analyses: Dict[str, Dict[str, Any]]
    ):
        """Add dependencies across files in the project"""
        # Look for imports that match other files in the project
        for imp in analysis.get('imports', []):
            # Try to resolve import to a file in the project
            resolved_file = self._resolve_import_to_file(imp, file_path, all_analyses)

            if resolved_file:
                source_file_id = self._get_node_id('file', file_path, '')
                target_file_id = self._get_node_id('file', resolved_file, '')

                if target_file_id in self.graph:
                    self.graph.add_edge(
                        source_file_id,
                        target_file_id,
                        type='imports'
                    )

                    # Update module node to be internal
                    module_node_id = self._get_node_id('module', '', imp)
                    if module_node_id in self.graph:
                        self.graph.nodes[module_node_id]['external'] = False
                        self.graph.nodes[module_node_id]['resolved_to'] = resolved_file

    def _resolve_import_to_file(
        self,
        import_str: str,
        importing_file: str,
        all_analyses: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """Try to resolve an import string to a file in the project"""
        # Simplified import resolution
        # In a real implementation, this would handle relative imports,
        # package structures, etc.

        importing_path = Path(importing_file)
        project_root = importing_path.parent

        # Try common Python import patterns
        if import_str.startswith('.'):
            # Relative import
            parts = import_str.strip('.').split('.')
            potential_path = project_root / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
            if str(potential_path) in all_analyses:
                return str(potential_path)
        else:
            # Absolute import - check if it matches any analyzed file
            parts = import_str.split('.')
            for file_path in all_analyses:
                file_name = Path(file_path).stem
                if file_name == parts[-1] or file_name == parts[0]:
                    return file_path

        return None

    def _get_node_id(self, node_type: str, file_path: str, name: str) -> str:
        """Generate unique node ID"""
        if node_type == 'file':
            return f"file:{file_path}"
        elif node_type == 'module':
            return f"module:{name}"
        else:
            return f"{node_type}:{file_path}:{name}"

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get all dependencies of a node"""
        if node_id not in self.graph:
            return []

        return list(self.graph.successors(node_id))

    def get_dependents(self, node_id: str) -> List[str]:
        """Get all nodes that depend on this node"""
        if node_id not in self.graph:
            return []

        return list(self.graph.predecessors(node_id))

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find all circular dependencies in the graph"""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except:
            return []

    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific node"""
        if node_id not in self.graph:
            return None

        return dict(self.graph.nodes[node_id])

    def export_graph(self, format: str = 'json') -> Any:
        """Export the dependency graph in various formats"""
        if format == 'json':
            # Convert to JSON-serializable format
            nodes = []
            for node_id, data in self.graph.nodes(data=True):
                node_data = {'id': node_id}
                node_data.update(data)
                nodes.append(node_data)

            edges = []
            for source, target, data in self.graph.edges(data=True):
                edge_data = {'source': source, 'target': target}
                edge_data.update(data)
                edges.append(edge_data)

            return {
                'nodes': nodes,
                'edges': edges
            }
        elif format == 'dot':
            # Export as Graphviz DOT format
            try:
                from networkx.drawing.nx_agraph import to_agraph
                return to_agraph(self.graph).to_string()
            except ImportError:
                logger.warning("Graphviz export requires pygraphviz")
                return None
        else:
            return None

    def get_call_chain(self, start_node: str, end_node: str) -> Optional[List[str]]:
        """Find call chain between two nodes"""
        try:
            path = nx.shortest_path(self.graph, start_node, end_node)
            return path
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None
