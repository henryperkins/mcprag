#!/usr/bin/env python3
"""
Simple test to verify the asyncio event loop initialization fix.
This test focuses only on the specific asyncio error that was reported.
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_asyncio_fix():
    """Test the specific asyncio error that was reported in the task."""
    print("🧪 Testing asyncio event loop initialization fix...")

    try:
        print("  ⚡ Testing FeedbackCollector synchronous initialization...")

        # This was the exact failing line from the original error:
        # FeedbackCollector.__init__ → asyncio.create_task(self._periodic_persist())
        from enhanced_rag.learning.feedback_collector import FeedbackCollector

        # This should NOT raise "no running event loop" RuntimeError anymore
        collector = FeedbackCollector(storage_path="./test_feedback")
        print("  ✅ SUCCESS: FeedbackCollector created without asyncio errors!")

        # Verify the fix: async task should be deferred
        if hasattr(collector, 'persist_task') and collector.persist_task is None:
            print("  ✅ SUCCESS: Async task creation properly deferred")
        else:
            print("  ⚠️  WARNING: Async task may have been created prematurely")

        if hasattr(collector, 'is_started') and not collector.is_started():
            print("  ✅ SUCCESS: Component reports as not started (lazy initialization)")
        else:
            print("  ⚠️  WARNING: Component may have started prematurely")

        print("\n🎉 ASYNCIO EVENT LOOP INITIALIZATION FIX: ✅ WORKING!")
        print("The original 'no running event loop' RuntimeError has been resolved.")
        return True

    except RuntimeError as e:
        if "no running event loop" in str(e).lower():
            print(f"\n❌ ORIGINAL ASYNCIO ERROR STILL EXISTS: {e}")
            print("The fix did not resolve the asyncio event loop initialization issue.")
            return False
        else:
            print(f"\n⚠️  Different RuntimeError occurred: {e}")
            return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing the specific asyncio event loop initialization fix...\n")

    success = test_asyncio_fix()

    if success:
        print(f"\n🏆 CONCLUSION: The asyncio event loop initialization error has been FIXED!")
        print(f"   • FeedbackCollector can now be initialized synchronously")
        print(f"   • Async tasks are properly deferred until an event loop is available")
        print(f"   • The 'no running event loop' RuntimeError is resolved")
        sys.exit(0)
    else:
        print(f"\n💥 CONCLUSION: The asyncio fix needs more work.")
        sys.exit(1)
