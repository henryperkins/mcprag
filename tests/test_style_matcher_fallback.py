import pytest

from enhanced_rag.generation.style_matcher import StyleMatcher
from enhanced_rag.core.models import SearchResult


@pytest.mark.asyncio
async def test_style_matcher_accepts_code_snippet_and_content_fallback():
    # Example with canonical field 'code_snippet'
    example1 = SearchResult(
        id="1",
        score=1.0,
        file_path="f.py",
        code_snippet="def foo():\n    return 1\n",
        language="python",
    )

    # Dict-shaped example using 'content' (fallback path)
    example2 = {
        "id": "2",
        "score": 0.9,
        "file_path": "g.py",
        "content": "def bar():\n  return 2\n",
        "language": "python",
    }

    matcher = StyleMatcher({})
    res = await matcher.analyze_style([example1, example2], "python")

    assert isinstance(res, dict)
    assert "profile" in res
    assert res.get("detected_from_examples") is True
    profile = res["profile"]
    assert profile.get("language") == "python"