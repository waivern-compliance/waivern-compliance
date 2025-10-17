"""Global test configuration for WCT tests."""

from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from WCT application .env file for testing
# This ensures VS Code and other test runners have access to the same environment
# Note: We use the WCT app's .env since that's where API keys and credentials live
env_file = Path(__file__).parent.parent / "apps" / "wct" / ".env"
if env_file.exists():
    load_dotenv(env_file)
