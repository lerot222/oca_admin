import subprocess
import logging
import os
import stat
import ast

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ADDONS_PATH = '/var/lib/odoo/.local/share/Odoo/addons/18.0'


class OcaModule(models.Model):
    _name = 'oca.admin.module'
    _description = 'OCA Module'
    _order = 'technical_name asc'

    name = fields.Char(string='Module Name', required=True)
    technical_name = fields.Char(string='Technical Name', required=True, index=True)
    repository_id = fields.Many2one(
        'oca.admin.repository', string='Repository', required=True, ondelete='cascade'
    )
    summary = fields.Char(string='Summary')
    version = fields.Char(string='Version')
    author = fields.Char(string='Author')
    category = fields.Char(string='Category')
    is_application = fields.Boolean(string='Has WUI', default=False,
        help='True if the module has its own menu and web interface.')
    wui_icon = fields.Html(
        string='WUI',
        compute='_compute_wui_icon',
        sanitize=False,
    )

    @api.depends('is_application')
    def _compute_wui_icon(self):
        for rec in self:
            if rec.is_application:
                rec.wui_icon = (
                    '<span title="WUI + CLI" style="white-space:nowrap">'
                    '<i class="fa fa-desktop" style="color:#28a745;font-size:16px;" title="Interface WUI"></i> '
                    '<i class="fa fa-terminal" style="color:#6c757d;font-size:16px;" title="Interface CLI"></i>'
                    '</span>'
                )
            else:
                rec.wui_icon = (
                    '<span title="CLI seulement">'
                    '<i class="fa fa-terminal" style="color:#6c757d;font-size:16px;" title="Interface CLI"></i>'
                    '</span>'
                )
    install_state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('installing', 'Installing...'),
            ('installed', 'Installed'),
            ('error', 'Error'),
        ],
        string='Status', default='available', readonly=True,
    )
    install_log = fields.Text(string='Installation Log', readonly=True)
    odoo_deps = fields.Char(string='Odoo Dependencies', readonly=True,
        help='Comma-separated list of required Odoo modules (from manifest depends)')
    deps_missing = fields.Char(string='Missing Dependencies',
        compute='_compute_deps_missing', store=False)
    deps_ok = fields.Boolean(string='Dependencies OK',
        compute='_compute_deps_missing', store=False)
    deps_html = fields.Html(string='Dependencies',
        compute='_compute_deps_missing', sanitize=False)
    deps_form_html = fields.Html(string='Required Dependencies',
        compute='_compute_deps_missing', sanitize=False)
    python_deps = fields.Char(string='Python Dependencies', readonly=True)
    local_path = fields.Char(string='Local Path', compute='_compute_local_path')
    is_local = fields.Boolean(string='Downloaded', compute='_compute_local_path')
    odoo_module_id = fields.Many2one(
        'ir.module.module',
        string='Odoo Module',
        compute='_compute_odoo_module',
    )
    main_menu_action_id = fields.Integer(
        string='Main Menu Action',
        compute='_compute_odoo_module',
    )

    @api.depends('technical_name')
    def _compute_local_path(self):
        for rec in self:
            path = os.path.join(ADDONS_PATH, rec.technical_name or '')
            rec.local_path = path
            rec.is_local = os.path.isdir(path)

    @api.depends('odoo_deps', 'install_state')
    def _compute_deps_missing(self):
        installed = set(self.env['ir.module.module'].search(
            [('state', '=', 'installed')]
        ).mapped('name'))
        for rec in self:
            deps = [d.strip() for d in (rec.odoo_deps or '').split(',') if d.strip()]
            missing = [d for d in deps if d not in installed]
            rec.deps_missing = ','.join(missing) if missing else ''
            rec.deps_ok = not missing
            if not deps:
                rec.deps_html = '<span style="color:#aaa;font-size:11px">—</span>'
                rec.deps_form_html = '<p style="color:#aaa">Aucune dépendance externe.</p>'
            else:
                pills = []
                rows = []
                for d in deps:
                    mod = self.env['ir.module.module'].search([('name','=',d)], limit=1)
                    label = mod.shortdesc if mod else d
                    state = mod.state if mod else 'uninstalled'
                    ok = state == 'installed'
                    # pill for the list
                    bg, fg, icon = ('#d4edda','#155724','✓') if ok else ('#f8d7da','#721c24','✗')
                    pills.append(
                        f'<span style="display:inline-block;margin:1px 2px;padding:1px 6px;'
                        f'border-radius:10px;font-size:10px;background:{bg};color:{fg}">'
                        f'{icon} {d}</span>'
                    )
                    # row for the form
                    status_color = '#28a745' if ok else '#dc3545'
                    status_txt = 'Installed' if ok else 'Not installed'
                    status_icon = '✓' if ok else '✗'
                    rows.append(
                        f'<tr>'
                        f'<td style="padding:4px 8px;font-weight:500">{d}</td>'
                        f'<td style="padding:4px 8px;color:#666">{label}</td>'
                        f'<td style="padding:4px 8px;color:{status_color};font-weight:500">'
                        f'{status_icon} {status_txt}</td>'
                        f'</tr>'
                    )
                rec.deps_html = ''.join(pills)
                rec.deps_form_html = (
                    '<table style="width:100%;border-collapse:collapse;font-size:13px">'
                    '<thead><tr style="border-bottom:1px solid #eee">'
                    '<th style="padding:4px 8px;text-align:left;color:#666">Module</th>'
                    '<th style="padding:4px 8px;text-align:left;color:#666">Name</th>'
                    '<th style="padding:4px 8px;text-align:left;color:#666">Status</th>'
                    '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
                )

    @api.depends('technical_name', 'install_state')
    def _compute_odoo_module(self):
        for rec in self:
            module = self.env['ir.module.module'].search(
                [('name', '=', rec.technical_name)], limit=1
            )
            rec.odoo_module_id = module.id if module else False
            # Chercher le menu racine lié à ce module
            action_id = False
            if module and module.state == 'installed':
                menu = self.env['ir.ui.menu'].search(
                    [('parent_id', '=', False), ('action', '!=', False)],
                    limit=1
                )
                # Chercher via les menus dont l'action appartient au module
                menus = self.env['ir.ui.menu'].search([
                    ('parent_id', '=', False),
                ])
                for m in menus:
                    if m.action and hasattr(m.action, 'id'):
                        action_id = m.action.id
                        break
            rec.main_menu_action_id = action_id or 0

    def _run(self, cmd):
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    def action_install(self):
        self.ensure_one()
        repo = self.repository_id
        logs = []
        self.install_state = 'installing'
        self.env.cr.commit()

        try:
            logs.append('=== Downloading from GitHub ===')
            tmp_dir = f'/tmp/oca_{repo.repo_name}'
            if not os.path.isdir(tmp_dir):
                r = self._run([
                    'git', 'clone',
                    '--depth', '1',
                    '--branch', repo.branch,
                    '--filter=blob:none',
                    '--sparse',
                    f'https://github.com/{repo.organization}/{repo.repo_name}.git',
                    tmp_dir,
                ])
                logs.append(r.stdout or r.stderr or 'Clone OK')
                if r.returncode != 0:
                    raise UserError(_('Git clone failed:\n%s') % r.stderr)
            else:
                logs.append(f'Using existing clone at {tmp_dir}')

            r = self._run(['git', '-C', tmp_dir, 'sparse-checkout', 'set', self.technical_name])
            logs.append(r.stdout or r.stderr or 'Sparse-checkout OK')

            src = os.path.join(tmp_dir, self.technical_name)
            dst = os.path.join(ADDONS_PATH, self.technical_name)
            if not os.path.isdir(src):
                raise UserError(_('Module folder not found: %s') % src)

            logs.append(f'=== Copying to {dst} ===')
            # Save original permissions of the addons directory
            original_mode = os.stat(ADDONS_PATH).st_mode
            os.chmod(ADDONS_PATH, original_mode | stat.S_IWUSR)
            try:
                r = self._run(['cp', '-r', src, dst])
                logs.append(r.stdout or r.stderr or 'Copy OK')
                if r.returncode != 0:
                    raise UserError(_('Copy failed:\n%s') % r.stderr)
            finally:
                os.chmod(ADDONS_PATH, original_mode)
                logs.append(f'Permissions restored on {ADDONS_PATH}')

            python_deps = []
            manifest_path = os.path.join(dst, '__manifest__.py')
            if os.path.isfile(manifest_path):
                with open(manifest_path) as f:
                    try:
                        manifest = ast.literal_eval(f.read())
                        python_deps = manifest.get('external_dependencies', {}).get('python', [])
                    except Exception:
                        pass

            if python_deps:
                logs.append(f'=== Installing Python deps: {python_deps} ===')
                r = self._run(['pip3', 'install', '--user'] + python_deps)
                logs.append(r.stdout or r.stderr or 'pip OK')

            logs.append(f'=== Installing Odoo module: {self.technical_name} ===')
            self.env['ir.module.module'].update_list()
            module = self.env['ir.module.module'].search(
                [('name', '=', self.technical_name)], limit=1
            )
            if not module:
                raise UserError(_('Module %s not found after copy.') % self.technical_name)
            module.button_immediate_install()
            logs.append('Installation complete!')

            self.write({
                'install_state': 'installed',
                'install_log': '\n'.join(logs),
            })

        except Exception as e:
            logs.append(f'ERROR: {e}')
            self.write({'install_state': 'error', 'install_log': '\n'.join(logs)})
            self.env.cr.commit()  # commit before raise so Odoo does not rollback the error state
            raise

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Module installed'),
                'message': _('%s has been installed.') % self.technical_name,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_github(self):
        self.ensure_one()
        repo = self.repository_id
        url = (
            f'https://github.com/{repo.organization}/'
            f'{repo.repo_name}/tree/{repo.branch}/{self.technical_name}'
        )
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}


    def action_open_installed_module(self):
        """Open the installed module's main menu in Odoo."""
        self.ensure_one()
        module = self.env['ir.module.module'].search(
            [('name', '=', self.technical_name)], limit=1
        )
        if not module or module.state != 'installed':
            raise UserError(_('Module %s is not installed.') % self.technical_name)

        # All menus created by this module
        menu_data = self.env['ir.model.data'].search([
            ('module', '=', self.technical_name),
            ('model', '=', 'ir.ui.menu'),
        ])
        all_menus = self.env['ir.ui.menu'].browse(menu_data.mapped('res_id'))

        # 1. Menu racine avec action directe
        root_with_action = all_menus.filtered(lambda m: not m.parent_id and m.action)
        if root_with_action:
            action = root_with_action[0].action
            action_dict = action.sudo().read()[0]
            action_dict['type'] = action._name
            return action_dict

        # 2. Menu racine sans action → prendre le premier enfant avec action
        root_menus = all_menus.filtered(lambda m: not m.parent_id)
        if root_menus:
            children = all_menus.filtered(
                lambda m: m.parent_id.id == root_menus[0].id and m.action
            ).sorted('sequence')
            if children:
                action = children[0].action
                action_dict = action.sudo().read()[0]
                action_dict['type'] = action._name
                return action_dict

        # 3. Fallback : première act_window créée par le module
        action_data = self.env['ir.model.data'].search([
            ('module', '=', self.technical_name),
            ('model', '=', 'ir.actions.act_window'),
        ], limit=1)
        if action_data:
            action = self.env['ir.actions.act_window'].browse(action_data.res_id)
            action_dict = action.sudo().read()[0]
            action_dict['type'] = 'ir.actions.act_window'
            return action_dict

        raise UserError(
            _('No menu found for module %s. Try navigating manually.') % self.technical_name
        )

