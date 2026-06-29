=========
OCA Admin
=========

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3
.. |badge2| image:: https://img.shields.io/badge/odoo-18.0-brightgreen
   :alt: Odoo 18.0

|badge1| |badge2|

Odoo 18.0 module to browse and install OCA (Odoo Community Association)
modules directly from the Odoo web interface — no command line required.

**Table of contents**

.. contents::
   :local:

Features
--------

- Browse popular OCA GitHub repositories
- Fetch module lists with metadata (name, summary, version, author, category)
- View interface type: WUI (web UI + menu) or CLI (technical, no menu)
- Dependency checking: see which Odoo modules are required and whether they are installed
- One-click installation via ``git sparse-checkout`` (no full repo clone)
- Automatic Python dependency installation via ``pip``
- Link to open installed modules directly
- Link to module source on GitHub
- Re-fetch all repositories in one action
- **Admin-only access** (``base.group_system`` required)

Requirements
------------

- Odoo 18.0 Community or Enterprise
- ``git`` installed on the server
- ``requests`` Python library (declared in ``external_dependencies``)
- Odoo service user must have write access to the addons directory
  (handled automatically during install — permissions are temporarily
  unlocked then restored)

Installation
------------

Copy this module to your Odoo addons path and install it via
**Settings > Apps**.

Usage
-----

#. Go to **OCA Admin > Repositories**
#. Click **Fetch modules from GitHub** on a repository
#. Browse modules in **OCA Admin > Modules**
#. Check dependency status (green = installed, red = missing)
#. Click **Install** to download and install a module

Preconfigured Repositories
--------------------------

+---------------------------+-------------------------------+
| Repository                | Description                   |
+===========================+===============================+
| web                       | Web client enhancements       |
+---------------------------+-------------------------------+
| server-tools              | Server administration tools   |
+---------------------------+-------------------------------+
| account-financial-tools   | Accounting extensions         |
+---------------------------+-------------------------------+
| reporting-engine          | Reporting tools               |
+---------------------------+-------------------------------+
| stock-logistics-warehouse | Warehouse management          |
+---------------------------+-------------------------------+
| sale-workflow             | Sales workflow                |
+---------------------------+-------------------------------+
| project                   | Project management            |
+---------------------------+-------------------------------+

Security
--------

Accessible only to Odoo administrators (``Settings > Technical``).
Access is controlled via the ``base.group_system`` group.

Known Limitations
-----------------

- Installation requires internet access to GitHub from the Odoo server
- The addons path is hardcoded to
  ``/var/lib/odoo/.local/share/Odoo/addons/18.0`` — adjust
  ``ADDONS_PATH`` in ``models/oca_module.py`` for other environments
- No rollback mechanism if installation partially fails

Bug Tracker
-----------

Please report issues on the project's GitHub repository.

Credits
-------

Authors
~~~~~~~

* math

Maintainers
~~~~~~~~~~~

* math

License
-------

This module is licensed under the `LGPL-3 <https://www.gnu.org/licenses/lgpl-3.0.html>`_.
