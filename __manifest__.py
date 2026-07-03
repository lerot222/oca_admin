{
    'name': 'OCA Admin',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Install and manage OCA modules from the web interface',
    'description': '''
        Allows Odoo administrators to browse OCA repositories,
        discover available modules and install them directly
        from the Odoo web interface without using the command line.
    ''',
    'author': 'math',
    'website': 'https://github.com/math/oca_admin',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/oca_repository_views.xml',
        'views/oca_module_views.xml',
        'views/menus.xml',
        'data/oca_repositories.xml',
    ],
    'installable': True,
    'application': True,
    'images': ['static/description/icon.png'],
}
