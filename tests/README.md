# Flowrra Test Suite

Comprehensive test suite for the Flowrra async task queue library.

## Test Coverage

### `test_task.py` - Task Models (36 tests)
- **TaskStatus**: Enum values and behavior
- **TaskResult**: Creation, properties (is_complete, is_success), serialization (to_dict, from_dict)
- **Task**: Creation, priority comparison, default values

### `test_exceptions.py` - Exception Hierarchy (6 tests)
- **FlowrraError**: Base exception class
- **TaskNotFoundError**: Task registration errors
- **TaskTimeoutError**: Timeout handling
- **ExecutorNotRunningError**: Lifecycle errors
- **BackendError**: Backend operation errors

### `test_registry.py` - Task Registry (19 tests)
- Task registration (async and sync/CPU-bound)
- Custom task names
- Task metadata (max_retries, retry_delay, cpu_bound)
- Validation (rejecting async CPU tasks, sync I/O tasks)
- Task retrieval (get, get_or_raise)
- Task unregistration
- Task execution

### `test_backends.py` - Result Backends (13 tests)
- **InMemoryBackend**:
  - Store and retrieve results
  - Update existing results
  - Wait for task completion
  - Timeout handling
  - Delete operations
  - Clear all results
  - Multiple concurrent waiters

### `test_executor.py` - Task Executor (30+ tests)
- **Initialization**: Configuration, backends, worker counts
- **Lifecycle**: Start, stop, context manager
- **Task Submission**: Args/kwargs, priority, validation
- **Task Execution**: Simple tasks, concurrent tasks, async operations
- **Retry Logic**: Success after retry, exhausted retries
- **CPU-Bound Tasks**: ProcessPoolExecutor integration
- **Result Retrieval**: get_result, wait_for_result, timeouts
- **Edge Cases**: Exceptions, graceful shutdown, empty queue

### `test_integration.py` - End-to-End Tests (10 tests)
- Complete workflows (I/O + CPU tasks)
- Mixed success/failure scenarios
- High load testing (50+ concurrent tasks)
- Priority ordering verification
- Hybrid execution (CPU + I/O together)
- Task result lifecycle tracking
- Multiple executor instances

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_executor.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_executor.py::TestTaskExecution -v
```

### Run Specific Test
```bash
pytest tests/test_executor.py::TestTaskExecution::test_simple_task_execution -v
```

### Run with Coverage
```bash
pytest tests/ --cov=flowrra --cov-report=html
```

### Run Only Fast Tests (exclude integration)
```bash
pytest tests/ -v -m "not integration"
```

## Test Structure

```
tests/
├── __init__.py              # Package marker
├── conftest.py              # Pytest fixtures and configuration
├── test_task.py             # Task model tests
├── test_exceptions.py       # Exception tests
├── test_registry.py         # Registry tests
├── test_backends.py         # Backend tests
├── test_executor.py         # Executor tests
└── test_integration.py      # Integration tests
```

## Fixtures

### Defined in `conftest.py`:

- **`executor`**: Basic executor with 2 workers
- **`backend`**: Fresh InMemoryBackend instance
- **`running_executor`**: Started executor (auto-cleanup)
- **`event_loop`**: Async event loop

## Test Conventions

1. **Naming**: Tests use descriptive names prefixed with `test_`
2. **Organization**: Tests grouped into classes by functionality
3. **Async Tests**: Marked with `@pytest.mark.asyncio`
4. **Timeouts**: All wait operations include explicit timeouts
5. **Cleanup**: Context managers ensure proper resource cleanup
6. **Assertions**: Clear, specific assertions with helpful messages

## Adding New Tests

1. Create test file: `test_<feature>.py`
2. Import required modules
3. Create test class: `TestFeatureName`
4. Write test methods: `def test_specific_behavior(self):`
5. Use fixtures from `conftest.py` as needed
6. Mark async tests with `@pytest.mark.asyncio`

Example:
```python
import pytest
from flowrra import AsyncTaskExecutor

class TestNewFeature:
    @pytest.mark.asyncio
    async def test_feature_works(self):
        executor = AsyncTaskExecutor(num_workers=2)

        @executor.task()
        async def my_task():
            return "success"

        async with executor:
            task_id = await executor.submit(my_task)
            result = await executor.wait_for_result(task_id, timeout=2.0)

            assert result.result == "success"
```

## Coverage Goals

- **Target**: 90%+ code coverage
- **Critical paths**: 100% coverage for executor, registry, backends
- **Edge cases**: All error conditions tested
- **Integration**: Real-world usage patterns validated

## Continuous Integration

Tests are designed to run in CI environments:
- Fast execution (< 30 seconds for full suite)
- No external dependencies (Redis, etc.)
- Deterministic results
- Proper timeout handling
