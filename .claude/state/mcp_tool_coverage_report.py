#!/usr/bin/env python3
"""
MCP Tool Coverage Report Generator

Generates a comprehensive coverage report for all MCP tools in the MCPRAG ecosystem.
Identifies which tools have tests and which need test coverage.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class ToolInfo:
    """Information about an MCP tool"""
    name: str
    category: str
    file_path: str
    has_tests: bool = False
    test_coverage: float = 0.0
    requires_admin: bool = False
    requires_confirmation: bool = False
    parameters: List[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class MCPToolCoverageAnalyzer:
    """Analyzes MCP tool coverage across the codebase"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.tools: Dict[str, ToolInfo] = {}
        self.test_files: List[Path] = []
        
    def discover_mcp_tools(self) -> Dict[str, ToolInfo]:
        """Discover all MCP tools in the codebase"""
        tools_dir = self.project_root / "mcprag" / "mcp" / "tools"
        
        # Categories based on file names
        category_map = {
            "search.py": "search",
            "generation.py": "generation",
            "analysis.py": "analysis",
            "admin.py": "admin",
            "cache.py": "cache",
            "feedback.py": "feedback",
            "azure_management.py": "azure_management",
            "service_management.py": "service_management",
        }
        
        for py_file in tools_dir.glob("*.py"):
            if py_file.name in ["__init__.py", "base.py", "auth_proxy.py"]:
                continue
                
            category = category_map.get(py_file.name, "other")
            tools_in_file = self._extract_tools_from_file(py_file, category)
            self.tools.update(tools_in_file)
        
        return self.tools
    
    def _extract_tools_from_file(self, file_path: Path, category: str) -> Dict[str, ToolInfo]:
        """Extract tool definitions from a Python file"""
        tools = {}
        
        with open(file_path, "r") as f:
            content = f.read()
        
        # Pattern to match @mcp.tool() decorated functions
        tool_pattern = r'@mcp\.tool\(\)\s+async def (\w+)\((.*?)\):'
        matches = re.finditer(tool_pattern, content, re.DOTALL)
        
        for match in matches:
            tool_name = match.group(1)
            params_str = match.group(2)
            
            # Extract parameter names
            param_pattern = r'(\w+):\s*[^,=\)]+(?:[,\)]|$)'
            params = re.findall(param_pattern, params_str)
            # Filter out 'self' and common non-parameter matches
            params = [p for p in params if p not in ['self', 'cls', 'Dict', 'Any', 'List', 'Optional']]
            
            # Check for admin requirement
            requires_admin = "MCP_ADMIN_MODE" in content[max(0, match.start()-500):match.end()+500]
            
            # Check for confirmation requirement
            requires_confirm = "confirm" in params or "confirmation" in tool_name.lower()
            
            tools[tool_name] = ToolInfo(
                name=tool_name,
                category=category,
                file_path=str(file_path.relative_to(self.project_root)),
                parameters=params,
                requires_admin=requires_admin,
                requires_confirmation=requires_confirm
            )
        
        return tools
    
    def find_test_coverage(self) -> None:
        """Find test coverage for each tool"""
        # Find all test files
        test_patterns = [
            "tests/**/*test*.py",
            "test_*.py",
            "*_test.py",
            ".claude/state/*evaluation*.py",
            ".claude/state/*test*.py"
        ]
        
        for pattern in test_patterns:
            self.test_files.extend(self.project_root.glob(pattern))
        
        # Check which tools have tests
        for test_file in self.test_files:
            with open(test_file, "r") as f:
                content = f.read()
            
            for tool_name, tool_info in self.tools.items():
                if tool_name in content:
                    tool_info.has_tests = True
                    # Simple coverage estimate based on mentions
                    mentions = content.count(tool_name)
                    tool_info.test_coverage = min(100, mentions * 10)  # Rough estimate
    
    def generate_coverage_report(self) -> Dict:
        """Generate comprehensive coverage report"""
        self.discover_mcp_tools()
        self.find_test_coverage()
        
        # Calculate statistics
        total_tools = len(self.tools)
        tools_with_tests = sum(1 for t in self.tools.values() if t.has_tests)
        coverage_percentage = (tools_with_tests / total_tools * 100) if total_tools > 0 else 0
        
        # Group by category
        by_category = {}
        for tool in self.tools.values():
            if tool.category not in by_category:
                by_category[tool.category] = {
                    "tools": [],
                    "total": 0,
                    "tested": 0,
                    "coverage": 0.0
                }
            
            by_category[tool.category]["tools"].append(tool.name)
            by_category[tool.category]["total"] += 1
            if tool.has_tests:
                by_category[tool.category]["tested"] += 1
        
        # Calculate category coverage
        for category in by_category.values():
            category["coverage"] = (category["tested"] / category["total"] * 100) if category["total"] > 0 else 0
        
        # Identify untested tools
        untested_tools = [t for t in self.tools.values() if not t.has_tests]
        untested_admin_tools = [t for t in untested_tools if t.requires_admin]
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tools": total_tools,
                "tools_with_tests": tools_with_tests,
                "tools_without_tests": total_tools - tools_with_tests,
                "coverage_percentage": coverage_percentage,
                "test_files_found": len(self.test_files)
            },
            "by_category": by_category,
            "untested_tools": [t.name for t in untested_tools],
            "untested_admin_tools": [t.name for t in untested_admin_tools],
            "all_tools": {name: asdict(info) for name, info in self.tools.items()}
        }
        
        return report
    
    def print_coverage_report(self, report: Dict) -> None:
        """Print formatted coverage report"""
        print("\n" + "=" * 60)
        print("📊 MCP TOOL COVERAGE REPORT")
        print("=" * 60)
        print(f"📅 {report['timestamp']}")
        print(f"\n🎯 Overall Coverage: {report['summary']['tools_with_tests']}/{report['summary']['total_tools']} tools tested ({report['summary']['coverage_percentage']:.1f}%)")
        print(f"📄 Test Files Found: {report['summary']['test_files_found']}")
        
        print("\n📋 Coverage by Category:")
        for category_name, stats in report["by_category"].items():
            status = "✅" if stats["coverage"] > 50 else "❌"
            print(f"  {status} {category_name}: {stats['tested']}/{stats['total']} ({stats['coverage']:.1f}%)")
            if stats["tested"] < stats["total"]:
                untested = [t for t in stats["tools"] if t not in [tool.name for tool in self.tools.values() if tool.has_tests and tool.category == category_name]]
                if untested:
                    print(f"      Untested: {', '.join(untested[:3])}{' ...' if len(untested) > 3 else ''}")
        
        if report["untested_tools"]:
            print(f"\n🚨 Untested Tools ({len(report['untested_tools'])}):")
            for tool_name in report["untested_tools"][:10]:
                tool = self.tools[tool_name]
                admin_flag = " [ADMIN]" if tool.requires_admin else ""
                print(f"  • {tool_name}{admin_flag} ({tool.category})")
            if len(report["untested_tools"]) > 10:
                print(f"  ... and {len(report['untested_tools']) - 10} more")
        
        print("\n💡 Recommendations:")
        if report['summary']['coverage_percentage'] < 50:
            print("  1. 🚨 CRITICAL: Less than 50% tool coverage - prioritize test creation")
        if report['untested_admin_tools']:
            print(f"  2. ⚠️  {len(report['untested_admin_tools'])} admin tools lack tests - high risk for destructive operations")
        if report['summary']['test_files_found'] < 5:
            print("  3. 📝 Limited test files found - consider organizing tests better")
        
        # Priority recommendations
        print("\n🎯 Priority Tools to Test (based on risk and usage):")
        priority_tools = []
        for tool_name, tool in self.tools.items():
            if not tool.has_tests:
                priority_score = 0
                if tool.requires_admin:
                    priority_score += 10  # High risk
                if tool.requires_confirmation:
                    priority_score += 5   # Destructive operation
                if tool.category in ["admin", "azure_management"]:
                    priority_score += 3   # Critical infrastructure
                if len(tool.parameters) > 5:
                    priority_score += 2   # Complex tool
                
                priority_tools.append((tool_name, priority_score, tool))
        
        priority_tools.sort(key=lambda x: x[1], reverse=True)
        for tool_name, score, tool in priority_tools[:5]:
            risk = "HIGH" if score >= 10 else "MEDIUM" if score >= 5 else "LOW"
            print(f"  • {tool_name} ({tool.category}) - Risk: {risk}")
        
        print("\n" + "=" * 60)


def generate_test_template(tool_name: str, tool_info: ToolInfo) -> str:
    """Generate a test template for an untested tool"""
    template = f'''"""Tests for {tool_name} MCP tool"""
import pytest
import asyncio
from mcprag.server import MCPServer
from mcprag.mcp.tools._helpers import {tool_name}_impl  # Update import path

@pytest.fixture
async def server():
    """Create test server"""
    server = MCPServer()
    await server.start_async_components()
    yield server
    await server.cleanup_async_components()

@pytest.mark.asyncio
async def test_{tool_name}_basic(server):
    """Test basic {tool_name} functionality"""
    result = await {tool_name}_impl(
        server=server,
        # Add required parameters
        {chr(10).join(f'        {param}=...,' for param in tool_info.parameters[:3])}
    )
    
    assert result["status"] != "error"
    assert "data" in result
    # Add specific assertions

@pytest.mark.asyncio  
async def test_{tool_name}_error_handling(server):
    """Test {tool_name} error handling"""
    result = await {tool_name}_impl(
        server=server,
        # Invalid parameters to trigger error
    )
    
    assert result["status"] == "error"
    assert "message" in result
'''
    return template


def main():
    """Main entry point"""
    analyzer = MCPToolCoverageAnalyzer()
    report = analyzer.generate_coverage_report()
    
    # Print report
    analyzer.print_coverage_report(report)
    
    # Save detailed report
    report_file = f"mcp_tool_coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved: {report_file}")
    
    # Generate test templates for top untested tools
    print("\n📝 Generating test templates for untested tools...")
    templates_dir = Path(".claude/state/test_templates")
    templates_dir.mkdir(exist_ok=True)
    
    for tool_name in report["untested_tools"][:5]:
        tool_info = analyzer.tools[tool_name]
        template = generate_test_template(tool_name, tool_info)
        
        template_file = templates_dir / f"test_{tool_name}.py"
        with open(template_file, "w") as f:
            f.write(template)
        
        print(f"  ✅ Generated template: {template_file}")
    
    # Return exit code based on coverage
    if report['summary']['coverage_percentage'] < 30:
        return 1  # Critical - less than 30% coverage
    return 0


if __name__ == "__main__":
    exit(main())