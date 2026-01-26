# Flowrra Development Guide

Complete guide for setting up and contributing to Flowrra development.

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- git (for version control)

## Installation

### Option 1: Using pip with pyproject.toml (Recommended)

```bash
# Clone the repository
git clone https://github.com/flowrra/flowrra.git
cd flowrra

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or with Redis backend support
pip install -e ".[dev,redis]"
```

### Option 2: Using requirements files

```bash
# Clone the repository
git clone https://github.com/flowrra/flowrra.git
cd flowrra

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install production dependencies (none currently)
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install the package in editable mode
pip install -e .
```

### Option 3: Using setup.py

```bash
# Clone and setup
git clone https://github.com/flowrra/flowrra.git
cd flowrra
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Project Structure

```
flowrra/
├── src/
│   └── flowrra/
│       ├── __init__.py          # Public API
│       ├── task.py              # Task models
│       ├── registry.py          # Task registration
│       ├── exceptions.py        # Custom exceptions
│       ├── executors/
│       │   ├── __init__.py
│       │   ├── base.py          # Base executor
│       │   ├── io_executor.py   # I/O-bound executor
│       │   └── cpu_executor.py  # CPU-bound executor
│       └── backends/
│           ├── __init__.py
│           ├── base.py          # Backend interface
│           ├── memory.py        # In-memory backend
│           ├── redis.py         # Redis backend
│           └── factory.py       # Backend factory
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_task.py             # Task model tests
│   ├── test_exceptions.py       # Exception tests
│   ├── test_registry.py         # Registry tests
│   ├── test_backends.py         # Backend tests
│   ├── test_redis_backend.py    # Redis backend tests
│   ├── test_backend_factory.py  # Factory tests
│   ├── test_io_executor.py      # IOExecutor tests
│   ├── test_cpu_executor.py     # CPUExecutor tests
│   ├── test_integration.py      # Integration tests
│   └── README.md                # Test documentation
├── examples/
│   └── basic_usage.py           # Usage examples
├── pyproject.toml               # Project metadata (primary)
├── setup.py                     # Alternative setup
├── requirements.txt             # Production deps
├── requirements-dev.txt         # Development deps
├── README.md                    # Project README
├── QUICKSTART.md                # Quick start guide
├── DEVELOPMENT.md               # This file
└── LICENSE                      # Apache 2.0 License
```

## Development Workflow

### 1. Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_executor.py -v

# Run specific test class
pytest tests/test_executor.py::TestTaskExecution -v

# Run specific test
pytest tests/test_executor.py::TestTaskExecution::test_simple_task_execution -v

# Run with coverage
pytest tests/ --cov=flowrra --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Run tests with timeout protection
pytest tests/ -v --timeout=30

# Run only fast tests (exclude slow integration tests)
pytest tests/ -v -m "not slow"

# Run tests with Redis backend (requires Redis server running)
pytest tests/test_redis_backend.py -v

# Skip Redis tests if Redis not available
pytest tests/ -v --ignore=tests/test_redis_backend.py
```

### 2. Code Quality

#### Linting with Ruff

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

#### Type Checking with mypy

```bash
# Check types
mypy src/flowrra/

# Strict mode (as configured in pyproject.toml)
mypy --strict src/flowrra/
```

#### Code Formatting with Black (optional)

```bash
# Format code
black src/ tests/

# Check formatting without changes
black --check src/ tests/
```

### 3. Running Examples

```bash
# Run the basic example
python examples/basic_usage.py

# Create your own example
cat > examples/my_example.py << 'EOF'
import asyncio
from flowrra import Flowrra

async def main():
    app = Flowrra.from_urls()

    @app.task()
    async def my_task(x: int):
        return x * 2

    async with app:
        task_id = await app.submit(my_task, 21)
        result = await app.wait_for_result(task_id, timeout=5.0)
        print(f"Result: {result.result}")

if __name__ == "__main__":
    asyncio.run(main())
EOF

python examples/my_example.py
```

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-new-feature
```

### 2. Make Your Changes

Edit the relevant files in `src/flowrra/`.

### 3. Add Tests

Add tests in `tests/` for any new functionality:

```python
# tests/test_my_feature.py
import pytest
from flowrra import Flowrra

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_my_feature(self):
        app = Flowrra.from_urls()

        @app.task()
        async def my_new_task():
            return "feature works!"

        async with app:
            task_id = await app.submit(my_new_task)
            result = await app.wait_for_result(task_id, timeout=2.0)

            assert result.result == "feature works!"
```

### 4. Run Quality Checks

```bash
# Run tests
pytest tests/ -v

# Check linting
ruff check src/ tests/

# Check types
mypy src/flowrra/

# Run all checks
pytest tests/ -v && ruff check src/ tests/ && mypy src/flowrra/
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "Add my new feature

- Implement feature X
- Add tests for feature X
- Update documentation"
```

### 6. Push and Create PR

```bash
git push origin feature/my-new-feature
# Then create a Pull Request on GitHub
```

## Common Development Tasks

### Adding a New Backend

1. Create backend file: `src/flowrra/backends/my_backend.py`
2. Implement `BaseResultBackend` interface
3. Add tests: `tests/test_my_backend.py`
4. Export in `src/flowrra/backends/__init__.py`
5. Update documentation

See [BACKENDS.md](BACKENDS.md) for detailed backend implementation guide.

Example:

```python
# src/flowrra/backends/my_backend.py
from flowrra.backends.base import BaseResultBackend
from flowrra.task import TaskResult

class MyBackend(BaseResultBackend):
    async def store(self, task_id: str, result: TaskResult) -> None:
        # Implementation
        pass

    async def get(self, task_id: str) -> TaskResult | None:
        # Implementation
        pass

    async def wait_for(self, task_id: str, timeout: float | None) -> TaskResult:
        # Implementation
        pass
```

### Testing Redis Backend

If you're working on Redis backend features, you'll need Redis server running:

```bash
# Start Redis with Docker
docker run -d -p 6379:6379 redis:latest

# Or install locally
brew install redis  # macOS
brew services start redis

# Run Redis tests
pytest tests/test_redis_backend.py -v

# Run all tests including Redis
pytest tests/ -v
```

### Adding a New Exception

1. Add to `src/flowrra/exceptions.py`
2. Inherit from `FlowrraError`
3. Add tests in `tests/test_exceptions.py`
4. Export in `src/flowrra/__init__.py`

### Debugging Tips

```python
# Use ipdb for debugging
import ipdb; ipdb.set_trace()

# Or use built-in breakpoint()
breakpoint()

# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Testing

```python
# tests/test_performance.py
import asyncio
import pytest
import time
from flowrra import IOExecutor

@pytest.mark.asyncio
async def test_throughput():
    """Test task throughput under load."""
    executor = IOExecutor(io_workers=10)

    @executor.task()
    async def fast_task(n: int):
        return n

    async with executor:
        start = time.time()

        # Submit 1000 tasks
        task_ids = []
        for i in range(1000):
            task_id = await executor.submit(fast_task, i)
            task_ids.append(task_id)

        # Wait for all
        for task_id in task_ids:
            await executor.wait_for_result(task_id, timeout=30.0)

        elapsed = time.time() - start
        throughput = 1000 / elapsed

        print(f"Throughput: {throughput:.2f} tasks/sec")
        assert throughput > 100  # At least 100 tasks/sec
```

## Release Process

1. Update version in `pyproject.toml` and `setup.py`
2. Update `CHANGELOG.md`
3. Run full test suite: `pytest tests/ -v --cov=flowrra`
4. Build package: `python -m build`
5. Upload to PyPI: `twine upload dist/*`
6. Tag release: `git tag v0.1.0 && git push --tags`

## Getting Help

- **Documentation**: Read the test suite and examples
- **Issues**: Check [GitHub Issues](https://github.com/flowrra/flowrra/issues)
- **Discussions**: Start a discussion on GitHub

## Code Style Guidelines

1. **Type hints**: All functions should have type hints
2. **Docstrings**: Public APIs must have docstrings
3. **Async**: Use `async`/`await` for I/O operations
4. **Sync**: Use sync functions for CPU-bound work
5. **Testing**: Every feature needs tests
6. **Line length**: Max 100 characters (configured in ruff)
7. **Imports**: Organized by standard library, third-party, local

## Performance Considerations

- **I/O tasks**: Use async/await for network, file I/O
- **CPU tasks**: Use `cpu_bound=True` for compute-heavy work
- **Worker count**: Tune based on workload (I/O vs CPU)
- **Queue size**: Consider memory vs backpressure tradeoffs

## License

Flowrra is licensed under the Apache License 2.0. See LICENSE file for details.
