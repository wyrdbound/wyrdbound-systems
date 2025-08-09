"""Tests for the factory pattern implementation in executor creation."""

import pytest
from unittest.mock import Mock, MagicMock

from grimoire_runner.executors.executor_factories import (
    ExecutorRegistry,
    ActionExecutorFactory,
    TableExecutorFactory,
    DefaultActionExecutorFactory,
    DefaultTableExecutorFactory,
)
from grimoire_runner.executors.action_executor import ActionExecutor
from grimoire_runner.executors.table_executor import TableExecutor
from grimoire_runner.core.engine import GrimoireEngine


class TestFactoryPattern:
    """Test cases for the factory pattern implementation."""

    def test_executor_registry_creates_default_factories(self):
        """Test that ExecutorRegistry creates default factories when none provided."""
        registry = ExecutorRegistry()
        
        # Test that it creates default factories
        assert registry.action_executor_factory is not None
        assert registry.table_executor_factory is not None
        assert registry.step_executor_factory is not None
        
        # Test that they create the expected executor types
        action_executor = registry.create_action_executor()
        table_executor = registry.create_table_executor()
        
        assert isinstance(action_executor, ActionExecutor)
        assert isinstance(table_executor, TableExecutor)

    def test_custom_action_executor_factory_injection(self):
        """Test that custom action executor factory can be injected."""
        # Create a mock factory
        mock_factory = Mock(spec=ActionExecutorFactory)
        mock_executor = Mock(spec=ActionExecutor)
        mock_factory.create_action_executor.return_value = mock_executor
        
        # Create registry with custom factory
        registry = ExecutorRegistry(action_executor_factory=mock_factory)
        
        # Test that custom factory is used
        result = registry.create_action_executor()
        assert result is mock_executor
        mock_factory.create_action_executor.assert_called_once()

    def test_custom_table_executor_factory_injection(self):
        """Test that custom table executor factory can be injected."""
        # Create a mock factory
        mock_factory = Mock(spec=TableExecutorFactory)
        mock_executor = Mock(spec=TableExecutor)
        mock_factory.create_table_executor.return_value = mock_executor
        
        # Create registry with custom factory
        registry = ExecutorRegistry(table_executor_factory=mock_factory)
        
        # Test that custom factory is used
        result = registry.create_table_executor()
        assert result is mock_executor
        mock_factory.create_table_executor.assert_called_once()

    def test_engine_uses_executor_registry(self):
        """Test that GrimoireEngine uses ExecutorRegistry correctly."""
        # Create a custom registry
        registry = ExecutorRegistry()
        
        # Create engine with custom registry
        engine = GrimoireEngine(executor_registry=registry)
        
        # Verify registry is set
        assert engine.executor_registry is registry
        
        # Verify action executor was created through registry
        assert engine.action_executor is not None
        assert isinstance(engine.action_executor, ActionExecutor)

    def test_dependency_injection_in_action_executor(self):
        """Test that ActionExecutor receives table executor factory properly."""
        # Create a mock table executor factory
        mock_table_factory = Mock(spec=TableExecutorFactory)
        mock_table_executor = Mock(spec=TableExecutor)
        mock_table_factory.create_table_executor.return_value = mock_table_executor
        
        # Create action executor factory with table factory
        action_factory = DefaultActionExecutorFactory(table_executor_factory=mock_table_factory)
        
        # Create action executor through factory
        action_executor = action_factory.create_action_executor()
        
        # Verify action executor was created
        assert isinstance(action_executor, ActionExecutor)
        
        # The table factory should be available in the action strategies
        # (This verifies the dependency injection chain is working)
        flow_strategy = None
        for strategy in action_executor.strategy_registry._strategies.values():
            if strategy.get_action_type() == "flow_call":
                flow_strategy = strategy
                break
        
        assert flow_strategy is not None
        assert flow_strategy.table_executor_factory is mock_table_factory

    def test_factory_pattern_allows_extension(self):
        """Test that factory pattern allows easy extension with custom executors."""
        # Create a custom action executor
        class CustomActionExecutor(ActionExecutor):
            def __init__(self):
                super().__init__()
                self.custom_property = "custom"
        
        # Create a custom factory
        class CustomActionExecutorFactory(ActionExecutorFactory):
            def create_action_executor(self):
                return CustomActionExecutor()
        
        # Use custom factory in registry
        registry = ExecutorRegistry(action_executor_factory=CustomActionExecutorFactory())
        
        # Create action executor
        executor = registry.create_action_executor()
        
        # Verify it's the custom executor
        assert isinstance(executor, CustomActionExecutor)
        assert hasattr(executor, 'custom_property')
        assert executor.custom_property == "custom"

    def test_step_executor_factory_dependency_injection(self):
        """Test that step executor factory receives registry for dependency injection."""
        registry = ExecutorRegistry()
        
        # Create a flow executor (which needs action executor dependency)
        flow_executor = registry.create_step_executor("completion", Mock())
        
        # Verify it's created and has action executor
        assert flow_executor is not None
        assert hasattr(flow_executor, 'action_executor')
        assert flow_executor.action_executor is not None

    def test_registry_factory_methods_work(self):
        """Test that all registry factory methods work correctly."""
        registry = ExecutorRegistry()
        
        # Test action executor creation
        action_executor = registry.create_action_executor()
        assert isinstance(action_executor, ActionExecutor)
        
        # Test table executor creation
        table_executor = registry.create_table_executor()
        assert isinstance(table_executor, TableExecutor)
        
        # Test step executor creation for different types
        dice_executor = registry.create_step_executor("dice_roll", Mock())
        assert dice_executor is not None
        
        choice_executor = registry.create_step_executor("player_choice", Mock())
        assert choice_executor is not None
        
        # Test supported step types
        supported_types = registry.get_supported_step_types()
        expected_types = [
            "dice_roll", "dice_sequence", "player_choice", "player_input",
            "table_roll", "llm_generation", "completion", "flow_call"
        ]
        for expected_type in expected_types:
            assert expected_type in supported_types
