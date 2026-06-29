# pylint: disable=prefer-env-translation,translation-not-lazy,attribute-string-redundant
import ast
import logging

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RAW_URL = 'https://raw.githubusercontent.com/{org}/{repo}/{branch}/{module}/__manifest__.py'


class OcaRepository(models.Model):
    _name = 'oca.admin.repository'
    _description = 'OCA GitHub Repository'
    _order = 'name asc'

    name = fields.Char(required=True)
    organization = fields.Char(default='OCA', required=True)
    repo_name = fields.Char(string='Repository', required=True)  # noqa: W8113
    branch = fields.Char(default='18.0', required=True)
    github_url = fields.Char(string='GitHub URL', compute='_compute_github_url', store=True)
    state = fields.Selection(
        selection=[
            ('not_fetched', 'Not Fetched'),
            ('fetched', 'Fetched'),
            ('error', 'Error'),
        ],
        string='Status',
        default='not_fetched',
        readonly=True,
    )
    last_fetch_date = fields.Datetime(string='Last Fetch', readonly=True)
    module_ids = fields.One2many('oca.admin.module', 'repository_id', string='Modules')
    module_count = fields.Integer(string='Module Count', compute='_compute_module_count')
    installed_count = fields.Integer(string='Installed', compute='_compute_module_count')
    module_ratio = fields.Char(string='Installed / Total', compute='_compute_module_count')
    notes = fields.Text()

    @api.depends('organization', 'repo_name')
    def _compute_github_url(self):
        for rec in self:
            if rec.organization and rec.repo_name:
                rec.github_url = 'https://github.com/%(org)s/%(repo)s' % {
                    'org': rec.organization, 'repo': rec.repo_name
                }
            else:
                rec.github_url = False

    @api.depends('module_ids', 'module_ids.install_state')
    def _compute_module_count(self):
        for rec in self:
            rec.module_count = len(rec.module_ids)
            rec.installed_count = len(
                rec.module_ids.filtered(lambda m: m.install_state == 'installed')
            )
            rec.module_ratio = (
                '%(installed)s / %(total)s' % {
                    'installed': rec.installed_count, 'total': rec.module_count
                }
                if rec.module_count else '— / —'
            )

    def _fetch_manifest(self, tech_name):
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
            _logger.debug('Could not fetch manifest for %s/%s', self.repo_name, tech_name, exc_info=True)
            return {}

    def action_fetch_modules(self):
        self.ensure_one()
        api_url = (
            'https://api.github.com/repos/%(org)s/%(repo)s/contents?ref=%(branch)s' % {
                'org': self.organization,
                'repo': self.repo_name,
                'branch': self.branch,
            }
        )
        try:
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.state = 'error'
            raise UserError(_('Cannot reach GitHub API: %(error)s') % {'error': str(e)}) from e

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
        _logger.info(
            'Fetched %s new + %s updated modules from %s/%s',
            created, updated, self.organization, self.repo_name,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fetch complete'),
                'message': _(
                    '%(new)d new modules, %(updated)d updated in %(repo)s.'
                ) % {'new': created, 'updated': updated, 'repo': self.repo_name},
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_modules(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Modules — %(name)s') % {'name': self.name},
            'res_model': 'oca.admin.module',
            'view_mode': 'list,form',
            'domain': [('repository_id', '=', self.id)],
            'context': {'default_repository_id': self.id},
        }

    def action_refetch_all(self):
        # search([]) without limit intentional: re-fetch ALL repos
        repos = self if self else self.search([])  # pylint: disable=no-search-all
        errors = []
        for repo in repos:
            try:
                repo.action_fetch_modules()
            except Exception as e:
                _logger.warning('Re-fetch failed for %s: %s', repo.repo_name, e)
                errors.append('%(repo)s: %(error)s' % {'repo': repo.repo_name, 'error': e})

        msg = _('Re-fetch complete for %(count)d repositories.') % {'count': len(repos)}
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
