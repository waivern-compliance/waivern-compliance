"""Global test configuration for WCT tests."""

from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file for testing
# This ensures VS Code and other test runners have access to the same environment
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
