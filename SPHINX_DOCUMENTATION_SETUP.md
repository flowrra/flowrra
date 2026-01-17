# Flowrra Sphinx Documentation Setup

This document explains how the Sphinx documentation is set up for Flowrra and how to publish it to Read the Docs.

## Directory Structure

```
flowrra/
├── .readthedocs.yml              # Read the Docs configuration
├── sphinx-docs/                   # Sphinx documentation root
│   ├── Makefile                   # Build commands
│   ├── requirements.txt           # Sphinx dependencies
│   ├── source/                    # Documentation source files
│   │   ├── conf.py                # Sphinx configuration
│   │   ├── index.rst              # Main documentation page
│   │   ├── installation.rst       # Installation guide
│   │   ├── quickstart.rst         # Quick start guide
│   │   ├── concepts.rst           # Core concepts
│   │   ├── guides/                # User guides
│   │   │   ├── tasks.rst
│   │   │   ├── scheduling.rst
│   │   │   ├── web-ui.rst
│   │   │   ├── backends.rst
│   │   │   └── executors.rst
│   │   ├── api/                   # Auto-generated API docs
│   │   │   ├── modules.rst
│   │   │   └── flowrra.*.rst      # Module documentation
│   │   ├── changelog.rst
│   │   ├── contributing.rst
│   │   └── license.rst
│   └── build/                     # Built HTML documentation
│       └── html/
│           └── index.html         # Entry point
└── src/flowrra/                   # Source code with docstrings
```

## Local Development

### Building Documentation Locally

1. Install Sphinx and dependencies:
```bash
pip install sphinx sphinx-autodoc-typehints sphinx-rtd-theme
```

2. Navigate to sphinx-docs directory:
```bash
cd sphinx-docs
```

3. Build HTML documentation:
```bash
make html
```

4. Open in browser:
```bash
open build/html/index.html
```

### Regenerating API Documentation

If you add new modules or change the structure:

```bash
sphinx-apidoc -f -o source/api ../src/flowrra
make clean
make html
```

### Clean Build

```bash
make clean
make html
```

## Publishing to Read the Docs

### Step 1: Sign up on Read the Docs

1. Go to https://readthedocs.org/
2. Sign up or log in with your GitHub account
3. Click "Import a Project"

### Step 2: Import Your Repository

1. Select your GitHub repository (flowrra)
2. Read the Docs will automatically detect the `.readthedocs.yml` configuration
3. Click "Build Version"

### Step 3: Configuration

The `.readthedocs.yml` file is already configured with:

- **Python Version**: 3.11
- **Build OS**: Ubuntu 22.04
- **Sphinx Configuration**: `sphinx-docs/source/conf.py`
- **Requirements**: `sphinx-docs/requirements.txt`

### Step 4: Verify Build

1. Wait for the build to complete (usually 2-5 minutes)
2. Click "View Docs" to see your published documentation
3. Your docs will be available at: `https://flowrra.readthedocs.io/`

### Step 5: Enable Webhooks (Optional)

Read the Docs automatically sets up webhooks, but you can verify:

1. Go to GitHub repository settings
2. Click "Webhooks"
3. Verify Read the Docs webhook is present
4. Every push to main/master will trigger a new build

## Customization

### Changing Theme

Edit `sphinx-docs/source/conf.py`:

```python
html_theme = 'sphinx_rtd_theme'  # Or 'alabaster', 'sphinx_book_theme', etc.
```

### Adding New Pages

1. Create new `.rst` file in `sphinx-docs/source/`
2. Add it to the `toctree` in `index.rst`
3. Rebuild docs: `make html`

### Updating Project Information

Edit `sphinx-docs/source/conf.py`:

```python
project = 'Flowrra'
copyright = '2026, Flowrra Contributors'
author = 'Flowrra Contributors'
release = '0.1.0'  # Update version here
```

## Documentation Structure

- **Getting Started**: Installation, quickstart, core concepts
- **User Guide**: Detailed guides for tasks, scheduling, UI, backends, executors
- **API Reference**: Auto-generated from docstrings
- **Additional Resources**: Changelog, contributing guidelines, license

## Writing Documentation

### reStructuredText Basics

```rst
Section Header
==============

Subsection
----------

**Bold text**
*Italic text*
``code``

Code block:

.. code-block:: python

   def hello():
       print("Hello")

Links:
`External Link <https://example.com>`_
:doc:`internal-page`
:ref:`section-reference`
```

### Documenting Code

Use Google-style docstrings in your Python code:

```python
async def my_function(arg1: str, arg2: int) -> dict:
    """Short description.

    Longer description with more details about what
    this function does.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Dictionary with results

    Raises:
        ValueError: If arg2 is negative

    Example:
        >>> result = await my_function("test", 42)
        >>> print(result)
        {'status': 'success'}
    """
    return {"status": "success"}
```

## Troubleshooting

### Build Warnings

Some warnings are normal (e.g., cross-reference warnings). To see full warnings:

```bash
make html
```

### Import Errors

If Sphinx can't find your modules, check `conf.py`:

```python
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))  # Should point to project root
```

### Missing Dependencies

Install all documentation dependencies:

```bash
pip install -r sphinx-docs/requirements.txt
```

## Next Steps

1. ✅ Documentation is set up and builds locally
2. ✅ `.readthedocs.yml` configuration is ready
3. ✅ Requirements file is created
4. 🔲 Push to GitHub
5. 🔲 Import project on Read the Docs
6. 🔲 Verify build succeeds
7. 🔲 Share documentation URL

## Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Read the Docs Guide](https://docs.readthedocs.io/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Napoleon Extension](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) (for Google-style docstrings)
