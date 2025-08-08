import asyncio
import pytest

from enhanced_rag.utils.cache_manager import CacheManager


@pytest.mark.asyncio
async def test_cache_manager_clear_scope_and_pattern():
    cm = CacheManager(ttl=60, max_size=100)

    # Seed keys across scopes
    await cm.set("search:foo", {"v": 1})
    await cm.set("search:bar", {"v": 2})
    await cm.set("embeddings:abc", {"v": 3})
    await cm.set("results:item", {"v": 4})
    await cm.set("results:other", {"v": 5})

    # Sanity: keys readable
    assert await cm.get("search:foo") == {"v": 1}
    assert await cm.get("results:item") == {"v": 4}

    # Clear 'search' scope
    removed_search = await cm.clear_scope("search")
    assert removed_search == 2
    assert await cm.get("search:foo") is None
    assert await cm.get("search:bar") is None
    # Others untouched
    assert await cm.get("embeddings:abc") == {"v": 3}
    assert await cm.get("results:item") == {"v": 4}

    # Clear by glob pattern under 'results'
    removed_results = await cm.clear_pattern("results:*")
    assert removed_results == 2
    assert await cm.get("results:item") is None
    assert await cm.get("results:other") is None

    # Remaining key should still exist
    assert await cm.get("embeddings:abc") == {"v": 3}

    # Stats return shape (not asserting exact counts due to TTL clock)
    stats = await cm.get_stats()
    assert "total_entries" in stats
    assert "ttl_seconds" in stats