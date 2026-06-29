# OCA Admin

Odoo 18.0 module to browse and install OCA (Odoo Community Association) modules directly from the Odoo web interface.

## Features

- Browse popular OCA GitHub repositories
- Fetch module lists with metadata (name, summary, version, author, category)
- View interface type: WUI (web UI + menu) or CLI (technical, no menu)
- Dependency checking: see which Odoo modules are required and whether they are installed
- One-click installation via `git sparse-checkout` (no full repo clone)
- Automatic Python dependency installation via `pip`
- Link to open installed modules directly
- Link to module source on GitHub
- Re-fetch all repositories in one action
- **Admin-only access** (`base.group_system` required)

## Requirements

- Odoo 18.0 Community or Enterprise
- `git` installed on the server
- Odoo service user must have write access to the addons directory (handled automatically during install — permissions are temporarily unlocked then restored)

## Installation

Copy this module to your Odoo addons path and install it via Settings > Apps.

## Usage

1. Go to **OCA Admin > Repositories**
2. Click **Fetch modules from GitHub** on a repository
3. Browse modules in **OCA Admin > Modules**
4. Check dependency status (green = installed, red = missing)
5. Click **Install** to download and install a module

## Preconfigured Repositories

| Repository | Description |
|---|---|
| web | Web client enhancements |
| server-tools | Server administration tools |
| account-financial-tools | Accounting extensions |
| reporting-engine | Reporting tools |
| stock-logistics-warehouse | Warehouse management |
| sale-workflow | Sales workflow |
| project | Project management |

## Security

Accessible only to Odoo administrators (`Settings > Technical`).

## License

LGPL-3.0 — see [LICENSE](LICENSE)

## Author

math
