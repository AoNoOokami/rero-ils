# -*- coding: utf-8 -*-
#
# This file is part of RERO ILS.
# Copyright (C) 2017 RERO.
#
# RERO ILS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# RERO ILS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RERO ILS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, RERO does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Invenio-admin views."""

from flask_admin import BaseView, expose
from invenio_admin.permissions import \
    admin_permission_factory as default_admin_permission_factory

from ...permissions import can_edit


class CirculationManager(BaseView):
    """Flask-Admin Circulation view."""

    @expose('/')
    @expose('/<path:path>')
    def index(self, path=None):
        """Angular Circulation view."""
        return self.render('rero_ils/circulation_ui.html')

    def is_accessible(self):
        """Access control."""
        return (can_edit() or default_admin_permission_factory(self).can())


circulation_adminview = {
    'view_class': CirculationManager,
    'kwargs': dict(name='Circulation', endpoint='circulation',
                   menu_icon_type='fa', menu_icon_value='fa-barcode'),
}