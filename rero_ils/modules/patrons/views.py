# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Blueprint used for loading templates."""

from __future__ import absolute_import, print_function

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_babelex import gettext as _
from flask_login import current_user, login_required
from flask_menu import register_menu
from invenio_i18n.ext import current_i18n
from werkzeug.exceptions import NotFound

from .api import Patron
from .utils import user_has_patron
from ..documents.api import Document
from ..items.api import Item
from ..libraries.api import Library
from ..loans.api import get_loans_by_patron_pid
from ..locations.api import Location

api_blueprint = Blueprint(
    'api_patrons',
    __name__,
    url_prefix='/patrons',
    template_folder='templates',
    static_folder='static',
)


blueprint = Blueprint(
    'patrons',
    __name__,
    template_folder='templates',
    static_folder='static',
)


@blueprint.route('/patrons/logged_user', methods=['GET'])
# @check_permission
def logged_user():
    """Current logged user informations in JSON."""
    patron = Patron.get_patron_by_user(current_user)
    if patron and 'resolve' in request.args:
        patron = patron.replace_refs()
        patron = patron.dumps()
        if patron.get('library'):
            library = Library.get_record_by_pid(
                patron['library']['pid']
            ).replace_refs()
            patron['library']['organisation'] = {
                'pid': library['organisation']['pid']
            }
    personsLabelOrder = current_app.config.get(
        'RERO_ILS_PERSONS_LABEL_ORDER', {}
    )
    data = {
        'settings': {
            'language': current_i18n.locale.language,
            'global_view': current_app.config.get(
                'RERO_ILS_SEARCH_GLOBAL_VIEW_CODE'),
            'baseUrl': current_app.config.get(
                'RERO_ILS_APP_BASE_URL',
                ''
            ),
            'personsLabelOrder': personsLabelOrder.get(
                current_i18n.locale.language,
                personsLabelOrder.get(personsLabelOrder.get('fallback')))
        }
    }
    if patron:
        data['metadata'] = patron
    return jsonify(data)


@blueprint.route('/global/patrons/profile', defaults={'viewcode': 'global'})
@blueprint.route('/<string:viewcode>/patrons/profile')
@login_required
@register_menu(
    blueprint,
    'main.profile.profile',
    _('%(icon)s Profile', icon='<i class="fa fa-user fa-fw"></i>'),
    visible_when=user_has_patron
)
def profile(viewcode):
    """Patron Profile Page."""
    patron = Patron.get_patron_by_user(current_user)
    if patron is None:
        raise NotFound()
    loans = get_loans_by_patron_pid(patron.pid)
    checkouts = []
    requests = []
    if loans:
        for loan in loans:
            item_pid = loan.get('item_pid')
            item = Item.get_record_by_pid(item_pid).replace_refs()
            document = Document.get_record_by_pid(item['document']['pid'])
            loan['document_title'] = document['title']
            loan['item_call_number'] = item['call_number']
            if loan['state'] == 'ITEM_ON_LOAN':
                checkouts.append(loan)
            elif loan['state'] in (
                    'PENDING',
                    'ITEM_AT_DESK',
                    'ITEM_IN_TRANSIT_FOR_PICKUP'
            ):
                pickup_loc = Location.get_record_by_pid(
                    loan['pickup_location_pid'])
                loan['pickup_library_name'] = \
                    pickup_loc.get_library().get('name')
                requests.append(loan)
    return render_template(
        'rero_ils/patron_profile.html',
        record=patron,
        checkouts=checkouts,
        pendings=requests,
        viewcode=viewcode
    )


@blueprint.app_template_filter('get_patron_from_barcode')
def get_patron_from_barcode(value):
    """Get patron from barcode."""
    return Patron.get_patron_by_barcode(value)


@blueprint.app_template_filter('get_patron_from_checkout_item_pid')
def get_patron_from_checkout_item_pid(item_pid):
    """Get patron from a checked out item pid."""
    from invenio_circulation.api import get_loan_for_item
    patron_pid = get_loan_for_item(item_pid)['patron_pid']
    return Patron.get_record_by_pid(patron_pid)


@blueprint.app_template_filter('get_checkout_loan_for_item')
def get_checkout_loan_for_item(item_pid):
    """Get patron from a checkout item pid."""
    from invenio_circulation.api import get_loan_for_item
    return get_loan_for_item(item_pid)


@blueprint.app_template_filter('get_patron_from_pid')
def get_patron_from_pid(patron_pid):
    """Get patron from pid."""
    return Patron.get_record_by_pid(patron_pid)


@blueprint.app_template_filter('get_location_name_from_pid')
def get_location_name_from_pid(location_pid):
    """Get location from pid."""
    from ..locations.api import Location
    return Location.get_record_by_pid(location_pid)['name']
