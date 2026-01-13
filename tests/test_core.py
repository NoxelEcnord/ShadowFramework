import unittest
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.module_loader import ModuleLoader
from utils.db_manager import DBManager

class TestCore(unittest.TestCase):
    def setUp(self):
        self.modules_dir = Path("./modules")
        self.db_file = Path("./db/test_shadow.db")
        self.loader = ModuleLoader(self.modules_dir)

    def test_module_loading(self):
        """Verify that modules are correctly identified and loaded."""
        modules = self.loader.load_modules()
        self.assertIn('auxiliary/scanner', modules)
        self.assertIn('auxiliary/test', modules)
        self.assertIn('exploit/smb_exploit', modules)

    def test_db_initialization(self):
        """Verify database manager initialization."""
        db = DBManager(self.db_file)
        self.assertTrue(self.db_file.exists() or self.db_file.parent.exists())

    def tearDown(self):
        if self.db_file.exists():
            os.remove(self.db_file)

if __name__ == '__main__':
    unittest.main()
