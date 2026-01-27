Contributing to Flowrra
=======================

We welcome contributions to Flowrra! This guide will help you get started with contributing to the project.

.. contents:: Table of Contents
   :local:
   :depth: 2

Getting Started
---------------

Prerequisites
~~~~~~~~~~~~~

Before contributing, ensure you have:

* Python 3.11 or higher
* git (for version control)
* pip (Python package installer)
* A GitHub account

Fork and Clone
~~~~~~~~~~~~~~

1. Fork the repository on GitHub: https://github.com/flowrra/flowrra

2. Clone your fork locally:

.. code-block:: bash

   git clone https://github.com/YOUR_USERNAME/flowrra.git
   cd flowrra

3. Add the upstream repository:

.. code-block:: bash

   git remote add upstream https://github.com/flowrra/flowrra.git

Development Setup
-----------------

Create Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create virtual environment
   python3 -m venv .venv

   # Activate it
   source .venv/bin/activate  # macOS/Linux
   # or
   .venv\Scripts\activate     # Windows

Install Dependencies
~~~~~~~~~~~~~~~~~~~~

Install Flowrra in editable mode with development dependencies:

.. code-block:: bash

   # Basic installation with dev dependencies
   pip install -e ".[dev]"

   # With all optional dependencies
   pip install -e ".[dev,redis,postgresql,mysql,ui]"

   # Or install from requirements files
   pip install -r requirements-dev.txt
   pip install -e .

Verify Installation
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run tests to verify setup
   pytest tests/ -v

   # Check code quality tools
   ruff --version
   mypy --version

Making Changes
--------------

1. Create a Feature Branch
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Always create a new branch for your changes:

.. code-block:: bash

   git checkout -b feature/my-new-feature
   # or
   git checkout -b fix/issue-123

Branch naming conventions:

* ``feature/description`` - New features
* ``fix/description`` - Bug fixes
* ``docs/description`` - Documentation improvements
* ``refactor/description`` - Code refactoring
* ``test/description`` - Test improvements

2. Make Your Changes
~~~~~~~~~~~~~~~~~~~~

Edit the relevant files. Common areas:

* **Core code**: ``src/flowrra/``
* **Tests**: ``tests/``
* **Documentation**: ``sphinx-docs/source/``
* **Examples**: ``examples/``

3. Write Tests
~~~~~~~~~~~~~~

All new features and bug fixes must include tests:

.. code-block:: python

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

4. Update Documentation
~~~~~~~~~~~~~~~~~~~~~~~

If your change affects user-facing functionality:

* Update relevant ``.rst`` files in ``sphinx-docs/source/``
* Add code examples if applicable
* Update API documentation if needed

5. Run Quality Checks
~~~~~~~~~~~~~~~~~~~~~~

Before committing, run all quality checks:

.. code-block:: bash

   # Run all tests
   pytest tests/ -v

   # Check code style
   ruff check src/ tests/

   # Auto-fix style issues
   ruff check --fix src/ tests/

   # Format code
   ruff format src/ tests/

   # Type checking
   mypy src/flowrra/

   # Run everything at once
   pytest tests/ -v && ruff check src/ tests/ && mypy src/flowrra/

6. Commit Your Changes
~~~~~~~~~~~~~~~~~~~~~~~

Write clear, descriptive commit messages:

.. code-block:: bash

   git add .
   git commit -m "Add feature X for Y

   - Implement core functionality
   - Add comprehensive tests
   - Update documentation
   - Add examples

   Fixes #123"

Commit message guidelines:

* First line: concise summary (50 chars or less)
* Blank line
* Detailed description of changes
* Reference related issues

7. Push and Create Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git push origin feature/my-new-feature

Then create a Pull Request on GitHub:

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select your feature branch
4. Fill in the PR template
5. Submit for review

Code Style Guidelines
---------------------

We follow strict code quality standards to maintain consistency and reliability.

General Principles
~~~~~~~~~~~~~~~~~~

1. **Type Hints**: All functions must have type hints

   .. code-block:: python

      async def process_task(task_id: str, timeout: float = 5.0) -> TaskResult:
          pass

2. **Docstrings**: All public APIs must have docstrings

   .. code-block:: python

      def create_scheduler(self, backend: str | None = None) -> Scheduler:
          """Create a task scheduler integrated with this Flowrra instance.

          Args:
              backend: Optional database URL for persistent storage.
                  Defaults to SQLite if not specified.

          Returns:
              Scheduler instance configured with this app's executors.
          """
          pass

3. **Async/Await**: Use async/await for I/O operations

   .. code-block:: python

      # Good
      async def fetch_data(url: str) -> dict:
          async with httpx.AsyncClient() as client:
              response = await client.get(url)
              return response.json()

4. **Line Length**: Maximum 100 characters per line

5. **Imports**: Organized by standard library, third-party, local

   .. code-block:: python

      # Standard library
      import asyncio
      from typing import Dict, List

      # Third-party
      import redis.asyncio as redis

      # Local
      from flowrra.task import Task
      from flowrra.exceptions import FlowrraError

Testing Guidelines
------------------

Test Requirements
~~~~~~~~~~~~~~~~~

* Every new feature must have tests
* Every bug fix must have a regression test
* Aim for >90% code coverage
* All tests must pass before merging

Writing Tests
~~~~~~~~~~~~~

Use pytest with async support:

.. code-block:: python

   import pytest
   from flowrra import Flowrra

   @pytest.mark.asyncio
   async def test_task_execution():
       """Test basic task execution."""
       app = Flowrra.from_urls()

       @app.task()
       async def add(a: int, b: int) -> int:
           return a + b

       async with app:
           task_id = await app.submit(add, 2, 3)
           result = await app.wait_for_result(task_id, timeout=5.0)

           assert result.result == 5
           assert result.status == "success"

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest tests/ -v

   # Run specific test file
   pytest tests/test_scheduler.py -v

   # Run with coverage
   pytest tests/ --cov=flowrra --cov-report=html

   # Run only fast tests
   pytest tests/ -m "not slow"

   # Run tests requiring Redis
   pytest tests/test_redis_backend.py -v

Test Organization
~~~~~~~~~~~~~~~~~

Tests are organized by component:

* ``test_task.py`` - Task model tests
* ``test_registry.py`` - Task registry tests
* ``test_executors.py`` - Executor tests
* ``test_scheduler.py`` - Scheduler tests
* ``test_backends.py`` - Backend tests
* ``test_integration.py`` - End-to-end tests

Pull Request Guidelines
-----------------------

PR Checklist
~~~~~~~~~~~~

Before submitting a PR, ensure:

- [ ] All tests pass
- [ ] Code style checks pass (ruff)
- [ ] Type checks pass (mypy)
- [ ] Documentation is updated
- [ ] Changelog is updated (for significant changes)
- [ ] Commit messages are clear and descriptive
- [ ] PR description explains the changes
- [ ] Related issues are referenced

PR Description Template
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: markdown

   ## Description
   Brief description of what this PR does.

   ## Motivation
   Why is this change needed? What problem does it solve?

   ## Changes
   - Change 1
   - Change 2
   - Change 3

   ## Testing
   How was this tested?

   ## Related Issues
   Fixes #123
   Relates to #456

Review Process
~~~~~~~~~~~~~~

1. **Automated Checks**: CI runs tests and quality checks
2. **Code Review**: Maintainers review the code
3. **Feedback**: Address any comments or suggestions
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainer merges the PR

Common Contribution Areas
-------------------------

Bug Fixes
~~~~~~~~~

1. Search for existing issues
2. Create an issue if one doesn't exist
3. Create a branch: ``fix/issue-123``
4. Write a failing test that reproduces the bug
5. Fix the bug
6. Verify the test now passes
7. Submit PR

New Features
~~~~~~~~~~~~

1. Discuss the feature in an issue first
2. Get feedback from maintainers
3. Create a branch: ``feature/my-feature``
4. Implement the feature
5. Add comprehensive tests
6. Update documentation
7. Submit PR

Documentation
~~~~~~~~~~~~~

Documentation improvements are always welcome:

* Fix typos or unclear explanations
* Add examples
* Improve API documentation
* Add tutorials or guides

.. code-block:: bash

   # Build documentation locally
   cd sphinx-docs
   make html
   open build/html/index.html  # macOS

Backend Development
~~~~~~~~~~~~~~~~~~~

Adding a new backend:

1. Create ``src/flowrra/backends/my_backend.py``
2. Inherit from ``BaseResultBackend``
3. Implement required methods
4. Add tests in ``tests/test_my_backend.py``
5. Update factory in ``backends/__init__.py``
6. Document usage

Scheduler Development
~~~~~~~~~~~~~~~~~~~~~

Working on scheduler features:

1. Understand the scheduler architecture
2. Implement changes in ``src/flowrra/scheduler/``
3. Add backend tests if needed
4. Test with SQLite, PostgreSQL, and MySQL
5. Update scheduling documentation

UI Development
~~~~~~~~~~~~~~

Improving the web UI:

1. UI code is in ``src/flowrra/ui/``
2. Templates in ``src/flowrra/ui/templates/``
3. Test with FastAPI, Flask, and Django
4. Ensure responsive design
5. Update UI documentation

Release Process
---------------

For Maintainers
~~~~~~~~~~~~~~~

1. **Version Bump**:

   .. code-block:: bash

      # Update version in:
      # - pyproject.toml
      # - src/flowrra/__init__.py

2. **Update Changelog**:

   Document all changes in ``CHANGELOG.md``

3. **Run Full Test Suite**:

   .. code-block:: bash

      pytest tests/ -v --cov=flowrra

4. **Build Package**:

   .. code-block:: bash

      python -m build

5. **Upload to PyPI**:

   .. code-block:: bash

      python -m twine upload dist/*

6. **Create Git Tag**:

   .. code-block:: bash

      git tag v0.1.8
      git push --tags

Community Guidelines
--------------------

Code of Conduct
~~~~~~~~~~~~~~~

* Be respectful and inclusive
* Welcome newcomers
* Provide constructive feedback
* Focus on what is best for the community
* Show empathy towards other community members

Communication
~~~~~~~~~~~~~

* **GitHub Issues**: Bug reports and feature requests
* **GitHub Discussions**: Questions and general discussion
* **Pull Requests**: Code contributions and reviews

Getting Help
~~~~~~~~~~~~

* Read the documentation: https://flowrra.readthedocs.io
* Check existing issues: https://github.com/flowrra/flowrra/issues
* Ask in discussions: https://github.com/flowrra/flowrra/discussions
* Review examples: ``examples/`` directory

Recognizing Contributors
~~~~~~~~~~~~~~~~~~~~~~~~

All contributors are recognized in:

* GitHub contributors page
* Release notes
* Project documentation

Thank you for contributing to Flowrra! 🎉

License
-------

By contributing to Flowrra, you agree that your contributions will be licensed under the Apache License 2.0.
