Installation
============

Flowrra requires Python 3.11 or later.

Basic Installation
------------------

Install from PyPI:

.. code-block:: bash

   pip install flowrra

This installs the core package with in-memory backend support.


Optional Dependencies
---------------------

Redis Backend
~~~~~~~~~~~~~

For distributed execution with Redis result backend:

.. code-block:: bash

   pip install flowrra[redis]


Database Support for Scheduler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PostgreSQL:

.. code-block:: bash

   pip install flowrra[postgresql]

MySQL:

.. code-block:: bash

   pip install flowrra[mysql]


Web UI Support
~~~~~~~~~~~~~~

FastAPI:

.. code-block:: bash

   pip install flowrra[ui-fastapi]

Flask/Quart:

.. code-block:: bash

   pip install flowrra[ui-flask]

Django:

.. code-block:: bash

   pip install flowrra[ui-django]

All UI adapters:

.. code-block:: bash

   pip install flowrra[ui]


All Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install flowrra[all]


Development Installation
------------------------

For development with testing and linting tools:

.. code-block:: bash

   pip install flowrra[dev]

Or install from source:

.. code-block:: bash

   git clone https://github.com/yourusername/flowrra.git
   cd flowrra
   pip install -e ".[dev]"


Verifying Installation
-----------------------

Check that Flowrra is installed correctly:

.. code-block:: python

   import flowrra
   print(flowrra.__version__)
