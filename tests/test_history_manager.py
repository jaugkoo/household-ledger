"""
Unit tests for HistoryManager (no network or .env required).
"""
import os
import tempfile
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from history_manager import HistoryManager


def test_history_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_file = os.path.join(tmpdir, ".processed_history")
        hm = HistoryManager(history_file=history_file)
        
        assert hm.get_count() == 0
        assert hm.is_processed("/some/path/file.jpg") is False
        
        hm.add_to_history("/some/path/file.jpg")
        assert hm.get_count() == 1
        assert hm.is_processed("/some/path/file.jpg") is True
        assert hm.is_processed("/some/path/file.jpg") is True  # idempotent check
        
        # Same path added again should not double-count (set semantics)
        hm.add_to_history("/some/path/file.jpg")
        assert hm.get_count() == 1
        
        # Different file
        hm.add_to_history("/other/receipt.png")
        assert hm.get_count() == 2
        assert hm.is_processed("/other/receipt.png") is True
        
        # Reload from disk
        hm2 = HistoryManager(history_file=history_file)
        assert hm2.get_count() == 2
        assert hm2.is_processed("/some/path/file.jpg") is True
        assert hm2.is_processed("/other/receipt.png") is True
    print("[OK] HistoryManager tests passed.")


if __name__ == "__main__":
    test_history_manager()
