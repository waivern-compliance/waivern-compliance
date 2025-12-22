"""Tests for ServiceContainer - DI container core functionality.

These tests verify the service container's ability to:
- Register services with different lifetimes (singleton, transient)
- Lazy-load services on first access
- Cache singleton instances
- Create new transient instances per request
- Handle errors gracefully (missing services, creation failures)
- Support type safety
"""

from waivern_core.services import ServiceContainer, ServiceDescriptor

from .conftest import TestService, TestServiceFactory

# =============================================================================
# Service Registration & Retrieval
# =============================================================================


class TestServiceContainer:
    """Test suite for ServiceContainer."""

    def test_register_and_retrieve_singleton_service(self):
        """Verify registering a service with singleton lifetime returns same instance on multiple calls."""
        # Arrange
        container = ServiceContainer()
        factory = TestServiceFactory()

        # Act
        container.register(ServiceDescriptor(TestService, factory, "singleton"))
        service1 = container.get_service(TestService)
        service2 = container.get_service(TestService)

        # Assert
        assert service1 is service2, "Singleton service should return same instance"

    def test_register_and_retrieve_transient_service(self):
        """Verify registering a service with transient lifetime returns new instance each time."""
        # Arrange
        container = ServiceContainer()
        factory = TestServiceFactory()

        # Act
        container.register(ServiceDescriptor(TestService, factory, "transient"))
        service1 = container.get_service(TestService)
        service2 = container.get_service(TestService)

        # Assert
        assert service1 is not service2, (
            "Transient service should return different instances"
        )

    def test_raise_error_when_retrieving_unregistered_service(self):
        """Verify that attempting to get unregistered service raises clear error."""
        # Arrange
        container = ServiceContainer()

        # Act & Assert
        try:
            container.get_service(TestService)
            assert False, "Should have raised an error for unregistered service"
        except KeyError:
            # Expected - service not registered
            pass

    def test_service_factory_create_called_lazily_on_first_access(self):
        """Verify factory create() only called when get_service() invoked, not during registration."""
        # Arrange
        container = ServiceContainer()

        # Track if create() was called
        create_called = False

        class LazyTestFactory:
            def create(self) -> TestService:
                nonlocal create_called
                create_called = True
                return TestService()

            def can_create(self) -> bool:
                return True

        factory = LazyTestFactory()

        # Act - register service
        container.register(ServiceDescriptor(TestService, factory, "singleton"))

        # Assert - create() should NOT have been called yet
        assert not create_called, (
            "Factory create() should not be called during registration"
        )

        # Act - get service
        container.get_service(TestService)

        # Assert - create() should have been called now
        assert create_called, (
            "Factory create() should be called when get_service() is invoked"
        )

    def test_singleton_service_factory_create_called_only_once(self):
        """Verify singleton service factory create() called exactly once despite multiple get_service() calls."""
        # Arrange
        container = ServiceContainer()

        # Track how many times create() was called
        create_count = 0

        class SingletonTestFactory:
            def create(self) -> TestService:
                nonlocal create_count
                create_count += 1
                return TestService()

            def can_create(self) -> bool:
                return True

        factory = SingletonTestFactory()

        # Act
        container.register(ServiceDescriptor(TestService, factory, "singleton"))
        container.get_service(TestService)
        container.get_service(TestService)
        container.get_service(TestService)

        # Assert
        assert create_count == 1, (
            f"Factory create() should be called exactly once for singleton, but was called {create_count} times"
        )

    def test_transient_service_factory_create_called_every_time(self):
        """Verify transient service factory create() called on every get_service() invocation."""
        # Arrange
        container = ServiceContainer()

        # Track how many times create() was called
        create_count = 0

        class TransientTestFactory:
            def create(self) -> TestService:
                nonlocal create_count
                create_count += 1
                return TestService()

            def can_create(self) -> bool:
                return True

        factory = TransientTestFactory()

        # Act
        container.register(ServiceDescriptor(TestService, factory, "transient"))
        container.get_service(TestService)
        container.get_service(TestService)
        container.get_service(TestService)

        # Assert
        assert create_count == 3, (
            f"Factory create() should be called every time for transient, but was called {create_count} times"
        )

    def test_support_multiple_different_service_types_in_same_container(self):
        """Verify container can manage multiple unrelated service types simultaneously."""
        # Arrange
        container = ServiceContainer()

        # Create a second service type
        class AnotherService:
            pass

        class AnotherServiceFactory:
            def create(self) -> AnotherService:
                return AnotherService()

            def can_create(self) -> bool:
                return True

        test_factory = TestServiceFactory()
        another_factory = AnotherServiceFactory()

        # Act
        container.register(ServiceDescriptor(TestService, test_factory, "singleton"))
        container.register(
            ServiceDescriptor(AnotherService, another_factory, "transient")
        )

        service1 = container.get_service(TestService)
        service2 = container.get_service(AnotherService)

        # Assert
        assert isinstance(service1, TestService), "Should retrieve TestService instance"
        assert isinstance(service2, AnotherService), (
            "Should retrieve AnotherService instance"
        )
        assert service1 is container.get_service(TestService), (
            "TestService should be singleton"
        )
        assert service2 is not container.get_service(AnotherService), (
            "AnotherService should be transient"
        )

    def test_type_safety_get_service_returns_correct_type(self):
        """Verify get_service(ServiceType) returns instance of ServiceType (type system compliance)."""
        # Arrange
        container = ServiceContainer()
        factory = TestServiceFactory()

        # Act
        container.register(ServiceDescriptor(TestService, factory))
        service = container.get_service(TestService)

        # Assert
        assert isinstance(service, TestService), (
            "get_service(TestService) should return TestService instance"
        )
        assert type(service) is TestService, "Service should be exact type TestService"

    def test_handle_factory_that_returns_none_gracefully(self):
        """Verify graceful handling when factory create() returns None (service unavailable)."""
        # Arrange
        container = ServiceContainer()

        class NoneReturningFactory:
            def create(self) -> TestService | None:
                return None

            def can_create(self) -> bool:
                return False

        factory = NoneReturningFactory()

        # Act
        container.register(ServiceDescriptor(TestService, factory))

        # Assert - should raise clear error when service creation returns None
        try:
            container.get_service(TestService)
            assert False, "Should raise an error when factory returns None"
        except (ValueError, RuntimeError) as e:
            # Expected - clear error about service unavailable
            assert (
                "None" in str(e)
                or "unavailable" in str(e).lower()
                or "failed" in str(e).lower()
            )

    def test_handle_factory_creation_failure_exception_gracefully(self):
        """Verify exceptions raised during factory create() are handled appropriately."""
        # Arrange
        container = ServiceContainer()

        class FailingFactory:
            def create(self) -> TestService:
                raise RuntimeError("Service creation failed due to missing dependency")

            def can_create(self) -> bool:
                return True  # Claims it can create, but fails during creation

        factory = FailingFactory()

        # Act
        container.register(ServiceDescriptor(TestService, factory))

        # Assert - exception should bubble up from factory.create()
        try:
            container.get_service(TestService)
            assert False, "Should raise an error when factory.create() raises exception"
        except RuntimeError as e:
            # Expected - exception from factory should bubble up
            assert "Service creation failed" in str(e)
