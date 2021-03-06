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

"""Click command-line utilities."""

from __future__ import absolute_import, print_function

import json
import os
import sys
from collections import OrderedDict
from glob import glob

import click
from flask import current_app
from flask.cli import with_appcontext
from flask_security.confirmable import confirm_user
from invenio_accounts.cli import commit, users
from invenio_pidstore.models import PersistentIdentifier
from invenio_records.api import Record
from invenio_records_rest.utils import obj_or_import_string
from invenio_search.cli import es_version_check
from invenio_search.proxies import current_search
from werkzeug.local import LocalProxy

from .items.cli import create_items, reindex_items
from .loans.cli import create_loans
from .patrons.cli import import_users

_datastore = LocalProxy(lambda: current_app.extensions['security'].datastore)


@click.group()
def fixtures():
    """Fixtures management commands."""


fixtures.add_command(import_users)
fixtures.add_command(create_items)
fixtures.add_command(reindex_items)
fixtures.add_command(create_loans)


@users.command('confirm')
@click.argument('user')
@with_appcontext
@commit
def manual_confirm_user(user):
    """Confirm a user."""
    user_obj = _datastore.get_user(user)
    if user_obj is None:
        raise click.UsageError('ERROR: User not found.')
    if confirm_user(user_obj):
        click.secho('User "%s" has been confirmed.' % user, fg='green')
    else:
        click.secho('User "%s" was already confirmed.' % user, fg='yellow')


@click.group()
def utils():
    """Misc management commands."""


@utils.command('show')
@click.argument('pid_value', nargs=1)
@click.option('-t', '--pid-type', 'pid-type, default(document_id)',
              default='document_id')
@with_appcontext
def show(pid_value, pid_type):
    """Show records."""
    record = PersistentIdentifier.query.filter_by(pid_type=pid_type,
                                                  pid_value=pid_value).first()
    recitem = Record.get_record(record.object_uuid)
    click.echo(json.dumps(recitem.dumps(), indent=2))


@utils.command('check_json')
@click.argument('paths', nargs=-1)
@click.option(
    '-r', '--replace', 'replace', is_flag=True, default=False,
    help='change file in place default=False'
)
@click.option(
    '-s', '--sort-keys', 'sort_keys', is_flag=True, default=False,
    help='order keys during replacement default=False'
)
@click.option(
    '-i', '--indent', 'indent', type=click.INT, default=2,
    help='intent default=2'
)
def check_json(paths, replace, indent, sort_keys):
    """Check json files."""
    files_list = []
    for path in paths:
        if os.path.isfile(path):
            files_list.append(path)
        elif os.path.isdir(path):
            files_list = files_list + glob(os.path.join(path, '**/*.json'),
                                           recursive=True)
    if not paths:
        files_list = glob('**/*.json', recursive=True)
    tot_error_cnt = 0
    for path_file in files_list:
        error_cnt = 0
        try:
            fname = path_file
            with open(fname, 'r') as opened_file:
                json_orig = opened_file.read().rstrip()
                opened_file.seek(0)
                json_file = json.load(opened_file,
                                      object_pairs_hook=OrderedDict)
            json_dump = json.dumps(json_file, indent=indent).rstrip()
            if json_dump != json_orig:
                error_cnt = 1
            click.echo(fname + ': ', nl=False)
            if replace:
                with open(fname, 'w') as opened_file:
                    opened_file.write(json.dumps(json_file,
                                                 indent=indent,
                                                 sort_keys=sort_keys))
                click.secho('File replaced', fg='yellow')
            else:
                if error_cnt == 0:
                    click.secho('Well indented', fg='green')
                else:
                    click.secho('Bad indentation', fg='red')
        except ValueError as e:
            click.echo(fname + ': ', nl=False)
            click.secho('Invalid JSON', fg='red', nl=False)
            click.echo(' -- ' + e.msg)
            error_cnt = 1

        tot_error_cnt += error_cnt
    return tot_error_cnt


@utils.command('schedules')
@with_appcontext
def schedules():
    """List harvesting schedules."""
    celery_ext = current_app.extensions.get('invenio-celery')
    for key, value in celery_ext.celery.conf.beat_schedule.items():
        click.echo(key + '\t', nl=False)
        click.echo(value)


@utils.command()
@click.option('--force', is_flag=True, default=False)
@with_appcontext
@es_version_check
def init(force):
    """Initialize registered templates, aliases and mappings."""
    # TODO: to remove once it is fixed in invenio-search module
    click.secho('Putting templates...', fg='green', bold=True, file=sys.stderr)
    with click.progressbar(
            current_search.put_templates(ignore=[400] if force else None),
            length=len(current_search.templates.keys())) as bar:
        for response in bar:
            bar.label = response
    click.secho('Creating indexes...', fg='green', bold=True, file=sys.stderr)
    with click.progressbar(
            current_search.create(ignore=[400] if force else None),
            length=current_search.number_of_indexes) as bar:
        for name, response in bar:
            bar.label = name


@click.command('create')
@click.option('-v', '--verbose', 'verbose', is_flag=True, default=True)
@click.option('-c', '--dbcommit', 'dbcommit', is_flag=True, default=True)
@click.option('-r', '--reindex', 'reindex', is_flag=True, default=False)
@click.option('-s', '--schema', 'schema', default=None)
@click.option('-p', '--pid_type', 'pid_type', default=None)
@click.argument('infile', type=click.File('r'), default=sys.stdin)
@with_appcontext
def create(infile, pid_type, schema, verbose, dbcommit, reindex):
    """Load REROILS record.

    infile: Json file
    reindex: reindex record by record
    dbcommit: commit record to database
    pid_type: record type
    schema: recoord schema
    """
    click.secho(
        'Loading {pid_type} records from {file_name}.'.format(
            pid_type=pid_type,
            file_name=infile.name
        ),
        fg='green'
    )
    record_class = obj_or_import_string(
        current_app.config
        .get('RECORDS_REST_ENDPOINTS')
        .get(pid_type).get('record_class', Record))
    data = json.load(infile)
    count = 0
    for record in data:
        count += 1
        if schema:
            record['$schema'] = schema
        rec = record_class.create(record, dbcommit=dbcommit, reindex=reindex)
        if verbose:
            click.echo(
                '{count: <8} {pid_type} created {id}'.format(
                    count=count,
                    pid_type=pid_type,
                    id=rec.id
                )
            )


fixtures.add_command(create)
