"""Setup script for Flowrra."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="flowrra",
    version="0.1.0",
    description="Async task executor built on asyncio - a lightweight Celery alternative",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ahmad Ameen",
    author_email="ahmadmameen7@gmail.com",
    url="https://github.com/flowrra/flowrra",
    project_urls={
        "Homepage": "https://github.com/flowrra/flowrra",
        "Documentation": "https://github.com/flowrra/flowrra#readme",
        "Repository": "https://github.com/flowrra/flowrra",
        "Issues": "https://github.com/flowrra/flowrra/issues",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        # Zero core dependencies!
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-timeout>=2.1.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
            "black>=23.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Typing :: Typed",
    ],
    keywords=[
        "async",
        "asyncio",
        "tasks",
        "queue",
        "celery",
        "background-jobs",
        "distributed",
        "worker",
    ],
    license="Apache-2.0",
    zip_safe=False,
)
