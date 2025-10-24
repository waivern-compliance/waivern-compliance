"""Tests for service protocols - integration with ServiceContainer."""

from waivern_core.services import ServiceContainer, ServiceFactory


class TestServiceFactoryIntegration:
    """Test suite for ServiceFactory protocol integration with ServiceContainer."""

    def test_container_works_with_protocol_compliant_factory(self):
        """Verify that ServiceContainer accepts and uses protocol-compliant factories."""

        # Arrange
        class TestService:
            pass

        class CompliantFactory:
            def create(self) -> TestService | None:
                return TestService()

            def can_create(self) -> bool:
                return True

        container = ServiceContainer()
        factory: ServiceFactory[TestService] = CompliantFactory()

        # Act
        container.register(TestService, factory)
        service = container.get_service(TestService)

        # Assert
        assert service is not None
        assert isinstance(service, TestService)

    def test_factory_can_create_indicates_service_availability(self):
        """Verify that factory can_create() correctly indicates when service is available or unavailable."""

        # Arrange
        class TestService:
            pass

        class ConditionalFactory:
            def __init__(self, available: bool):
                self._available = available

            def create(self) -> TestService | None:
                if self._available:
                    return TestService()
                return None

            def can_create(self) -> bool:
                return self._available

        # Test with available factory
        container_available = ServiceContainer()
        available_factory: ServiceFactory[TestService] = ConditionalFactory(
            available=True
        )

        # Act
        container_available.register(TestService, available_factory)
        service = container_available.get_service(TestService)

        # Assert - should succeed
        assert service is not None
        assert isinstance(service, TestService)

        # Test with unavailable factory
        container_unavailable = ServiceContainer()
        unavailable_factory: ServiceFactory[TestService] = ConditionalFactory(
            available=False
        )

        # Act
        container_unavailable.register(TestService, unavailable_factory)

        # Assert - should raise ValueError when factory returns None
        try:
            container_unavailable.get_service(TestService)
            assert False, "Should raise ValueError when factory.create() returns None"
        except ValueError as e:
            assert "None" in str(e) or "unavailable" in str(e).lower()

    def test_container_handles_factory_that_cannot_create_service(self):
        """Verify that container gracefully handles factory where can_create() returns False."""

        # Arrange
        class TestService:
            pass

        class UnavailableFactory:
            def create(self) -> TestService | None:
                # Service unavailable, return None
                return None

            def can_create(self) -> bool:
                return False

        container = ServiceContainer()
        factory: ServiceFactory[TestService] = UnavailableFactory()

        # Act
        container.register(TestService, factory)

        # Assert - container should raise ValueError when trying to get unavailable service
        try:
            container.get_service(TestService)
            assert False, "Should raise ValueError when factory cannot create service"
        except ValueError as e:
            assert "None" in str(e) or "unavailable" in str(e).lower()
