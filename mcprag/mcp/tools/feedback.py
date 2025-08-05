"""Feedback and tracking MCP tools."""
from typing import Optional, Dict, Any, TYPE_CHECKING
from ...utils.response_helpers import ok, err
from .base import check_component

# Helper functions that were referenced but not found in original
def validate_rating(rating: int) -> bool:
    """Validate rating is between 1 and 5."""
    return isinstance(rating, int) and 1 <= rating <= 5

def validate_feedback_kind(kind: str) -> bool:
    """Validate feedback kind."""
    valid_kinds = {"positive", "negative", "neutral", "bug", "feature", "other"}
    return kind.lower() in valid_kinds

async def track_interaction(
    server: "MCPServer",
    interaction_type: str,
    query_id: str,
    doc_id: Optional[str] = None,
    rank: Optional[int] = None,
    outcome: Optional[str] = None,
    score: Optional[float] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Common tracking implementation for clicks and outcomes."""
    # Try enhanced_search first
    if server.enhanced_search and hasattr(server.enhanced_search, "track_interaction"):
        try:
            await server.enhanced_search.track_interaction(
                interaction_type=interaction_type,
                query_id=query_id,
                doc_id=doc_id,
                rank=rank,
                outcome=outcome,
                score=score,
                context=context,
            )
            return ok({"tracked": True, "backend": "enhanced"})
        except Exception:
            pass

    # Try feedback_collector
    if server.feedback_collector and hasattr(server.feedback_collector, "record_interaction"):
        try:
            await server.feedback_collector.record_interaction(
                interaction_type=interaction_type,
                query_id=query_id,
                doc_id=doc_id,
                rank=rank,
                outcome=outcome,
                score=score,
                context=context,
            )
            return ok({"tracked": True, "backend": "feedback_collector"})
        except Exception:
            pass

    return err("No tracking backend available")

if TYPE_CHECKING:
    from ...server import MCPServer


def register_feedback_tools(mcp, server: "MCPServer") -> None:
    """Register feedback and tracking MCP tools."""

    @mcp.tool()
    async def submit_feedback(
        target_id: str,
        kind: str,
        rating: int,
        notes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit user feedback."""
        # Validation
        if not validate_rating(rating):
            return err("Rating must be an integer between 1 and 5")

        if not validate_feedback_kind(kind):
            return err(f"Invalid feedback kind: {kind}")

        if not check_component(server.feedback_collector, "Feedback collection"):
            return err("Feedback collection not available")

        # Explicit null check for type checker
        if server.feedback_collector is None:
            return err("Feedback collector component is not initialized")

        try:
            await server.feedback_collector.record_explicit_feedback(
                interaction_id=target_id, satisfaction=rating, comment=notes
            )
            return ok({"stored": True})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def track_search_click(
        query_id: str, doc_id: str, rank: int, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track user click on search result."""
        return await track_interaction(
            server=server,
            interaction_type="click",
            query_id=query_id,
            doc_id=doc_id,
            rank=rank,
            context=context,
        )

    @mcp.tool()
    async def track_search_outcome(
        query_id: str,
        outcome: str,
        score: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Track search outcome (success/failure)."""
        return await track_interaction(
            server=server,
            interaction_type="outcome",
            query_id=query_id,
            outcome=outcome,
            score=score,
            context=context,
        )