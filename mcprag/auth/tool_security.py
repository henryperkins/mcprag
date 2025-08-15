"""
Tool security classification for mcprag.

Maps MCP tools to security tiers for access control.
"""

from enum import Enum
from typing import Set, Dict

class SecurityTier(Enum):
    """Security access tiers for tools."""
    PUBLIC = "public"      # Read-only, no sensitive data
    DEVELOPER = "developer" # Read/write non-destructive
    ADMIN = "admin"        # Destructive operations
    SERVICE = "service"    # M2M automation

# Map existing mcprag tools to security tiers based on CLAUDE.md
TOOL_SECURITY_MAP: Dict[str, SecurityTier] = {
    # Search Tools (PUBLIC) - Read-only operations
    "search_code": SecurityTier.PUBLIC,
    "search_code_raw": SecurityTier.PUBLIC,
    "search_microsoft_docs": SecurityTier.PUBLIC,
    
    # Analysis Tools (PUBLIC) - Read-only analysis
    "explain_ranking": SecurityTier.PUBLIC,
    "preview_query_processing": SecurityTier.PUBLIC,
    "health_check": SecurityTier.PUBLIC,
    "index_status": SecurityTier.PUBLIC,
    "cache_stats": SecurityTier.PUBLIC,
    
    # Generation Tools (DEVELOPER) - Create content but non-destructive
    "generate_code": SecurityTier.DEVELOPER,
    "analyze_context": SecurityTier.DEVELOPER,
    
    # Feedback Tools (DEVELOPER) - Submit usage data
    "submit_feedback": SecurityTier.DEVELOPER,
    "track_search_click": SecurityTier.DEVELOPER,
    "track_search_outcome": SecurityTier.DEVELOPER,
    
    # Admin Tools (ADMIN) - Require MCP_ADMIN_MODE=true
    "index_rebuild": SecurityTier.ADMIN,
    "github_index_repo": SecurityTier.ADMIN,
    "manage_index": SecurityTier.ADMIN,
    "manage_documents": SecurityTier.ADMIN,
    "manage_indexer": SecurityTier.ADMIN,
    "create_datasource": SecurityTier.ADMIN,
    "create_skillset": SecurityTier.ADMIN,
    "rebuild_index": SecurityTier.ADMIN,
    "configure_semantic_search": SecurityTier.ADMIN,
    "cache_clear": SecurityTier.ADMIN,
    "index_repository": SecurityTier.ADMIN,
    "index_changed_files": SecurityTier.ADMIN,
    "backup_index_schema": SecurityTier.ADMIN,
    "clear_repository_documents": SecurityTier.ADMIN,
    "get_service_info": SecurityTier.ADMIN,
    "backfill_embeddings": SecurityTier.ADMIN,
    "validate_embeddings": SecurityTier.PUBLIC,
    
    # Additional tools default to ADMIN for safety
    "validate_index_schema": SecurityTier.ADMIN,
}

# Tier-based permissions
TIER_PERMISSIONS: Dict[SecurityTier, Set[str]] = {
    SecurityTier.PUBLIC: {
        tool for tool, tier in TOOL_SECURITY_MAP.items() 
        if tier == SecurityTier.PUBLIC
    },
    SecurityTier.DEVELOPER: {
        tool for tool, tier in TOOL_SECURITY_MAP.items() 
        if tier in (SecurityTier.PUBLIC, SecurityTier.DEVELOPER)
    },
    SecurityTier.ADMIN: set(TOOL_SECURITY_MAP.keys()),  # All tools
    SecurityTier.SERVICE: set(TOOL_SECURITY_MAP.keys()),  # All tools for M2M
}

def get_tool_tier(tool_name: str) -> SecurityTier:
    """
    Get security tier for a tool.
    
    Args:
        tool_name: Name of the MCP tool
        
    Returns:
        Security tier for the tool, defaulting to ADMIN for unknown tools
    """
    return TOOL_SECURITY_MAP.get(tool_name, SecurityTier.ADMIN)

def user_can_access_tool(user_tier: SecurityTier, tool_name: str) -> bool:
    """
    Check if a user tier can access a specific tool.
    
    Args:
        user_tier: User's security tier
        tool_name: Name of the tool to access
        
    Returns:
        True if user can access the tool, False otherwise
    """
    allowed_tools = TIER_PERMISSIONS.get(user_tier, set())
    return tool_name in allowed_tools

def get_tier_hierarchy_level(tier: SecurityTier) -> int:
    """
    Get numeric hierarchy level for a tier.
    
    Higher numbers mean higher access.
    
    Args:
        tier: Security tier
        
    Returns:
        Numeric level (0-3)
    """
    hierarchy = {
        SecurityTier.PUBLIC: 0,
        SecurityTier.DEVELOPER: 1,
        SecurityTier.ADMIN: 2,
        SecurityTier.SERVICE: 3,
    }
    return hierarchy.get(tier, 0)

def user_meets_tier_requirement(user_tier: SecurityTier, required_tier: SecurityTier) -> bool:
    """
    Check if user's tier meets or exceeds required tier.
    
    Args:
        user_tier: User's security tier
        required_tier: Required security tier
        
    Returns:
        True if user tier is sufficient, False otherwise
    """
    return get_tier_hierarchy_level(user_tier) >= get_tier_hierarchy_level(required_tier)
