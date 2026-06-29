import ast
import requests
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RAW_URL = 'https://raw.githubusercontent.com/{org}/{repo}/{branch}/{module}/__manifest__.py'


class OcaRepository(models.Model):
    _name = 'oca.admin.repository'
    _description = 'OCA GitHub Repository'
    _order = 'name asc'

    name = fields.Char(string='Name', required=True)
    organization = fields.Char(string='Organization', default='OCA', required=True)
    repo_name = fields.Char(string='Repository', required=True)
    branch = fields.Char(string='Branch', default='18.0', required=True)
    github_url = fields.Char(string='GitHub URL', compute='_compute_github_url', store=True)
    state = fields.Selection(
        selection=[('not_fetched', 'Not Fetched'), ('fetched', 'Fetched'), ('error', 'Error')],
        string='Status', default='not_fetched', readonly=True,
    )
    last_fetch_date = fields.Datetime(string='Last Fetch', readonly=True)
    module_ids = fields.One2many('oca.admin.module', 'repository_id', string='Modules')
    module_count = fields.Integer(string='Module Count', compute='_compute_module_count')
    installed_count = fields.Integer(string='Installed', compute='_compute_module_count')
    module_ratio = fields.Char(string='Installed / Total', compute='_compute_module_count')
    notes = fields.Text(string='Notes')

    @api.depends('organization', 'repo_name')
    def _compute_github_url(self):
        for rec in self:
            if rec.organization and rec.repo_name:
                rec.github_url = f'https://github.com/{rec.organization}/{rec.repo_name}'
            else:
                rec.github_url = False

    @api.depends('module_ids', 'module_ids.install_state')
    def _compute_module_count(self):
        for rec in self:
            rec.module_count = len(rec.module_ids)
            rec.installed_count = len(rec.module_ids.filtered(lambda m: m.install_state == 'installed'))
            rec.module_ratio = f'{rec.installed_count} / {rec.module_count}' if rec.module_count else '— / —'

    def _fetch_manifest(self, tech_name):
        """Fetch and parse __manifest__.py from GitHub raw content."""
        url = RAW_URL.format(
            org=self.organization,
            repo=self.repo_name,
            branch=self.branch,
            module=tech_name,
        )
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                return {}
            return ast.literal_eval(r.text)
        except Exception:
            return {}

    def action_fetch_modules(self):
        """Fetch module list + manifest details from GitHub."""
        self.ensure_one()
        api_url = (
            f'https://api.github.com/repos/'
            f'{self.organization}/{self.repo_name}/'
            f'contents?ref={self.branch}'
        )
        try:
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.state = 'error'
            raise UserError(_('Cannot reach GitHub API: %s') % str(e))

        contents = response.json()
        if not isinstance(contents, list):
            self.state = 'error'
            raise UserError(_('Unexpected response from GitHub API.'))

        existing = {m.technical_name: m for m in self.module_ids}
        created = updated = 0

        dirs = [
            item['name'] for item in contents
            if item.get('type') == 'dir'
            and not item['name'].startswith('.')
            and not item['name'].startswith('_')
        ]

        for tech_name in dirs:
            manifest = self._fetch_manifest(tech_name)
            vals = {
                'technical_name': tech_name,
                'name': manifest.get('name') or tech_name.replace('_', ' ').title(),
                'summary': (manifest.get('summary') or '')[:120],
                'version': manifest.get('version', ''),
                'author': (manifest.get('author') or '')[:100],
                'category': manifest.get('category', ''),
                'is_application': bool(manifest.get('application', False)),
                'odoo_deps': ','.join(
                    [d for d in manifest.get('depends', []) if d not in ('base', 'web')]
                ),
                'python_deps': ', '.join(
                    manifest.get('external_dependencies', {}).get('python', [])
                ),
                'repository_id': self.id,
            }
            if tech_name in existing:
                existing[tech_name].write(vals)
                updated += 1
            else:
                self.env['oca.admin.module'].create(vals)
                created += 1

        self.write({'state': 'fetched', 'last_fetch_date': fields.Datetime.now()})
        _logger.info('Fetched %s new + %s updated modules from %s/%s', created, updated, self.organization, self.repo_name)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fetch complete'),
                'message': _('%d new modules, %d updated in %s.') % (created, updated, self.repo_name),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_modules(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Modules — %s') % self.name,
            'res_model': 'oca.admin.module',
            'view_mode': 'list,form',
            'domain': [('repository_id', '=', self.id)],
            'context': {'default_repository_id': self.id},
        }

    def action_refetch_all(self):
        """Re-fetch modules for all selected repositories (or all if none selected)."""
        repos = self if self else self.search([])
        total_new = total_updated = 0
        errors = []
        for repo in repos:
            try:
                repo.action_fetch_modules()
                total_new += 0
                total_updated += 0
            except Exception as e:
                errors.append(f'{repo.repo_name}: {e}')

        msg = _('Re-fetch complete for %d repositories.') % len(repos)
        if errors:
            msg += ' Errors: ' + '; '.join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Re-fetch done'),
                'message': msg,
                'type': 'warning' if errors else 'success',
                'sticky': True,
            },
        }
