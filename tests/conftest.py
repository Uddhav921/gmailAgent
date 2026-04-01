import sys
from pathlib import Path

# Add project root to Python path so pytest can find 'app' module
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
