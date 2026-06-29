# Copyright 2024 math
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from odoo.tests.common import TransactionCase


class TestOcaRepository(TransactionCase):
    """Tests for oca.admin.repository"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repo = cls.env['oca.admin.repository'].create({
            'name': 'Test Repo',
            'organization': 'OCA',
            'repo_name': 'web',
            'branch': '18.0',
        })

    def test_github_url_computed(self):
        """GitHub URL is built from organization + repo_name."""
        self.assertEqual(
            self.repo.github_url,
            'https://github.com/OCA/web',
        )

    def test_github_url_empty_when_no_repo(self):
        """GitHub URL is False when repo_name is not set."""
        repo = self.env['oca.admin.repository'].new({
            'name': 'Empty',
            'organization': 'OCA',
            'repo_name': '',
        })
        self.assertFalse(repo.github_url)

    def test_module_count_zero_on_create(self):
        """A new repository has zero modules."""
        self.assertEqual(self.repo.module_count, 0)
        self.assertEqual(self.repo.installed_count, 0)

    def test_module_count_updates(self):
        """module_count and installed_count reflect child modules."""
        mod1 = self.env['oca.admin.module'].create({
            'name': 'Web Widget Datepicker',
            'technical_name': 'web_widget_datepicker',
            'repository_id': self.repo.id,
            'install_state': 'installed',
        })
        mod2 = self.env['oca.admin.module'].create({
            'name': 'Web Responsive',
            'technical_name': 'web_responsive',
            'repository_id': self.repo.id,
            'install_state': 'available',
        })
        self.repo.invalidate_recordset()
        self.assertEqual(self.repo.module_count, 2)
        self.assertEqual(self.repo.installed_count, 1)
        # cleanup
        mod1.unlink()
        mod2.unlink()

    def test_default_state(self):
        """Default state is not_fetched."""
        self.assertEqual(self.repo.state, 'not_fetched')


class TestOcaModule(TransactionCase):
    """Tests for oca.admin.module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repo = cls.env['oca.admin.repository'].create({
            'name': 'Test Repo',
            'organization': 'OCA',
            'repo_name': 'server-tools',
            'branch': '18.0',
        })

    def _create_module(self, **kwargs):
        vals = {
            'name': 'Test Module',
            'technical_name': 'test_module',
            'repository_id': self.repo.id,
        }
        vals.update(kwargs)
        return self.env['oca.admin.module'].create(vals)

    def test_wui_icon_application(self):
        """Module with is_application=True shows desktop + terminal icons."""
        mod = self._create_module(is_application=True)
        self.assertIn('fa-desktop', mod.wui_icon)
        self.assertIn('fa-terminal', mod.wui_icon)
        self.assertIn('WUI + CLI', mod.wui_icon)

    def test_wui_icon_cli_only(self):
        """Module with is_application=False shows CLI-only icon."""
        mod = self._create_module(is_application=False)
        self.assertNotIn('fa-desktop', mod.wui_icon)
        self.assertIn('fa-terminal', mod.wui_icon)
        self.assertIn('CLI only', mod.wui_icon)

    def test_deps_ok_when_no_deps(self):
        """Module with no odoo_deps has deps_ok=True and empty deps_missing."""
        mod = self._create_module(odoo_deps='')
        self.assertTrue(mod.deps_ok)
        self.assertFalse(mod.deps_missing)

    def test_deps_ok_when_all_installed(self):
        """Module whose deps are all installed has deps_ok=True."""
        mod = self._create_module(odoo_deps='base,mail')
        # base and mail are always installed in tests
        self.assertTrue(mod.deps_ok)
        self.assertFalse(mod.deps_missing)

    def test_deps_missing_when_not_installed(self):
        """Module depending on a nonexistent module has it listed as missing."""
        mod = self._create_module(odoo_deps='base,nonexistent_module_xyz')
        self.assertFalse(mod.deps_ok)
        self.assertIn('nonexistent_module_xyz', mod.deps_missing)

    def test_deps_html_has_pills(self):
        """deps_html contains span pills for each dependency."""
        mod = self._create_module(odoo_deps='base,mail')
        self.assertIn('base', mod.deps_html)
        self.assertIn('mail', mod.deps_html)

    def test_deps_html_empty_when_no_deps(self):
        """deps_html shows em-dash placeholder when no dependencies."""
        mod = self._create_module(odoo_deps='')
        self.assertIn('—', mod.deps_html)

    def test_default_install_state(self):
        """Default install_state is 'available'."""
        mod = self._create_module()
        self.assertEqual(mod.install_state, 'available')

    def test_local_path_computed(self):
        """local_path is built from ADDONS_PATH + technical_name."""
        mod = self._create_module(technical_name='my_module')
        self.assertTrue(mod.local_path.endswith('my_module'))

    def test_is_local_false_for_nonexistent(self):
        """is_local is False for a module not on disk."""
        mod = self._create_module(technical_name='_nonexistent_oca_module_12345')
        self.assertFalse(mod.is_local)
