"""Shared test fixtures for services tests."""


class TestService:
    """Simple test service for testing container behaviour."""

    pass


class TestServiceFactory:
    """Factory that creates TestService instances.

    This factory is compliant with the ServiceFactory protocol.
    """

    def create(self) -> TestService:
        """Create a new TestService instance."""
        return TestService()

    def can_create(self) -> bool:
        """Check if factory can create service."""
        return True
