"""
Unit tests for FileArchiver (no network or .env required).
"""
import os
import tempfile
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archiver import FileArchiver


def test_archiver():
    with tempfile.TemporaryDirectory() as base:
        archiver = FileArchiver(base)
        archive_root = os.path.join(base, "Archive")
        assert archiver.archive_root == archive_root
        
        # Create a dummy file
        test_file = os.path.join(base, "receipt.jpg")
        with open(test_file, "w") as f:
            f.write("dummy")
        
        assert archiver.is_in_archive(test_file) is False
        
        # Archive with receipt_date
        dest = archiver.archive_file(test_file, receipt_date="2025-01-15")
        assert dest is not None
        assert os.path.exists(dest)
        assert not os.path.exists(test_file)
        assert "2025" in dest and "01" in dest
        assert archiver.is_in_archive(dest) is True
        assert archiver.is_in_archive(test_file) is False  # original gone
        
        # Archive without receipt_date (uses current date)
        test_file2 = os.path.join(base, "receipt2.jpg")
        with open(test_file2, "w") as f:
            f.write("dummy2")
        dest2 = archiver.archive_file(test_file2)
        assert dest2 is not None
        assert os.path.exists(dest2)
        assert not os.path.exists(test_file2)
        
        # Non-existent file
        result = archiver.archive_file(os.path.join(base, "nonexistent.jpg"))
        assert result is None
    print("[OK] FileArchiver tests passed.")


if __name__ == "__main__":
    test_archiver()
