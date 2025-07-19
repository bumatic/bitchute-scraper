Installation
============

System Requirements
-------------------

* Python 3.7 or higher
* Google Chrome or Chromium browser
* ChromeDriver (automatically managed)

Basic Installation
------------------

Install from PyPI using pip:

.. code-block:: bash

   pip install bitchute-scraper

This installs the core package with basic functionality.

Full Installation
-----------------

For all features including progress bars and fast data formats:

.. code-block:: bash

   pip install bitchute-scraper[full]

Optional Dependencies
---------------------

Install specific optional features:

Progress Bars
~~~~~~~~~~~~~

.. code-block:: bash

   pip install bitchute-scraper[progress]

Fast Data Formats
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install bitchute-scraper[fast]

System Monitoring
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install bitchute-scraper[monitoring]

Development Installation
------------------------

For development and testing:

.. code-block:: bash

   git clone https://github.com/bumatic/bitchute-scraper.git
   cd bitchute-scraper
   pip install -e .[dev]

This installs the package in editable mode with development dependencies.

Docker Installation
-------------------

Using Docker for isolated environments:

.. code-block:: bash

   docker run -it python:3.9
   pip install bitchute-scraper[full]

Verification
------------

Verify your installation:

.. code-block:: python

   import bitchute
   print(bitchute.get_version())
   
   # Test basic functionality
   api = bitchute.BitChuteAPI()
   print("Installation successful!")

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**ChromeDriver Issues**

If you encounter ChromeDriver errors:

.. code-block:: bash

   # On macOS
   brew install --cask google-chrome
   brew install chromedriver
   
   # On Ubuntu
   sudo apt-get update
   sudo apt-get install google-chrome-stable

**Permission Errors**

For permission issues during installation:

.. code-block:: bash

   pip install --user bitchute-scraper

**Import Errors**

If you get import errors, ensure all dependencies are installed:

.. code-block:: bash

   pip install bitchute-scraper[full] --upgrade

Upgrade
-------

To upgrade to the latest version:

.. code-block:: bash

   pip install bitchute-scraper --upgrade

Uninstall
---------

To remove the package:

.. code-block:: bash

   pip uninstall bitchute-scraper,