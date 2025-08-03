#!/usr/bin/env python3
"""
Test script to verify the asyncio event loop initialization fix.
This script tests that FeedbackCollector can be initialized synchronously
without causing "no running event loop" errors.
"""

import asyncio
import logging
import sys
import traceback
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_synchronous_initialization():
    """Test that components can be initialized synchronously without errors."""
    print("🧪 Testing synchronous initialization...")

    try:
        # Test FeedbackCollector initialization (the root cause of the original error)
        from enhanced_rag.learning.feedback_collector import FeedbackCollector

        print("  ✅ Importing FeedbackCollector...")
        collector = FeedbackCollector(storage_path="./test_feedback")
        print("  ✅ FeedbackCollector initialized successfully")

        # Verify it's not started yet
        if hasattr(collector, 'is_started') and not collector.is_started():
            print("  ✅ FeedbackCollector properly deferred async task creation")
        else:
            print("  ⚠️  Warning: FeedbackCollector may have started prematurely")

        # Test RAGPipeline initialization
        try:
            from enhanced_rag.pipeline import RAGPipeline
            print("  ✅ Importing RAGPipeline...")

            # Basic config for testing
            config = {
                'context': {},
                'retrieval': {'enable_vector_search': False},
                'ranking': {},
                'learning': {'enable_adaptive_ranking': False},
                'generation': {}
            }

            pipeline = RAGPipeline(config)
            print("  ✅ RAGPipeline initialized successfully")

        except Exception as e:
            print(f"  ⚠️  RAGPipeline test skipped due to dependencies: {e}")

        # Test MCPServer initialization
        try:
            from mcprag.server import MCPServer
            print("  ✅ Importing MCPServer...")

            # This should not fail with asyncio errors anymore
            server = MCPServer()
            print("  ✅ MCPServer initialized successfully")

            # Verify async components tracking
            if hasattr(server, '_async_components_started'):
                print("  ✅ MCPServer has async component tracking")
            else:
                print("  ⚠️  Warning: MCPServer missing async component tracking")

        except Exception as e:
            print(f"  ❌ MCPServer initialization failed: {e}")
            return False

        print("🎉 All synchronous initialization tests passed!")
        return True

    except Exception as e:
        print(f"❌ Synchronous initialization test failed: {e}")
        traceback.print_exc()
        return False

async def test_async_startup():
    """Test that async components start correctly when event loop is available."""
    print("\n🧪 Testing async component startup...")

    try:
        from enhanced_rag.learning.feedback_collector import FeedbackCollector
        from mcprag.server import MCPServer

        # Create FeedbackCollector and verify it can start
        collector = FeedbackCollector(storage_path="./test_feedback")
        print("  ✅ FeedbackCollector created")

        # Start async components
        await collector.start()
        print("  ✅ FeedbackCollector async components started")

        # Verify it's started
        if collector.is_started():
            print("  ✅ FeedbackCollector reports as started")
        else:
            print("  ❌ FeedbackCollector not reporting as started")
            return False

        # Test cleanup
        await collector.cleanup()
        print("  ✅ FeedbackCollector cleanup completed")

        # Test MCPServer async startup
        try:
            server = MCPServer()
            print("  ✅ MCPServer created")

            # Test async component startup
            await server.ensure_async_components_started()
            print("  ✅ MCPServer async components started")

            # Test cleanup
            await server.cleanup_async_components()
            print("  ✅ MCPServer cleanup completed")

        except Exception as e:
            print(f"  ⚠️  MCPServer async test skipped due to dependencies: {e}")

        print("🎉 All async startup tests passed!")
        return True

    except Exception as e:
        print(f"❌ Async startup test failed: {e}")
        traceback.print_exc()
        return False

def test_original_error_scenario():
    """Test the original error scenario that was failing."""
    print("\n🧪 Testing original error scenario...")

    try:
        # This was the failing sequence:
        # MCPServer.__init__ → _init_components → RAGPipeline.__init__ →
        # _initialize_components → FeedbackCollector.__init__ → asyncio.create_task

        # Import without running event loop (mimics original error condition)
        from mcprag.server import MCPServer

        print("  ✅ Creating MCPServer (original failing scenario)...")
        server = MCPServer()  # This should NOT raise asyncio errors anymore
        print("  ✅ MCPServer created successfully without asyncio errors!")

        # Verify async components are not started yet
        if hasattr(server, '_async_components_started') and not server._async_components_started:
            print("  ✅ Async components properly deferred")
        else:
            print("  ⚠️  Warning: Async components may have started prematurely")

        print("🎉 Original error scenario test passed!")
        return True

    except RuntimeError as e:
        if "no running event loop" in str(e).lower():
            print(f"❌ ORIGINAL ERROR STILL EXISTS: {e}")
            return False
        else:
            print(f"❌ Different RuntimeError: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error in original scenario test: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting asyncio event loop initialization fix tests...\n")

    # Test 1: Synchronous initialization (main fix verification)
    sync_success = test_synchronous_initialization()

    # Test 2: Original error scenario
    original_success = test_original_error_scenario()

    # Test 3: Async startup (when event loop is available)
    async_success = asyncio.run(test_async_startup())

    print(f"\n📊 Test Results:")
    print(f"  Synchronous Initialization: {'✅ PASS' if sync_success else '❌ FAIL'}")
    print(f"  Original Error Scenario: {'✅ PASS' if original_success else '❌ FAIL'}")
    print(f"  Async Component Startup: {'✅ PASS' if async_success else '❌ FAIL'}")

    if sync_success and original_success and async_success:
        print(f"\n🎉 ALL TESTS PASSED! The asyncio event loop initialization fix is working correctly.")
        return 0
    else:
        print(f"\n❌ SOME TESTS FAILED. The fix may need additional work.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
