import os
import yaml

from click.testing import CliRunner
from datetime import date, datetime, timezone
from onegov.ballot import Ballot, BallotResult, Vote
from onegov.election_day.cli import cli
from onegov.election_day.models import ArchivedResult
from unittest.mock import patch


def test_add_instance(postgres_dsn, temporary_directory):

    cfg = {
        'applications': [
            {
                'path': '/onegov_election_day/*',
                'application': 'onegov.election_day.ElectionDayApp',
                'namespace': 'onegov_election_day',
                'configuration': {
                    'dsn': postgres_dsn,
                    'depot_backend': 'depot.io.memory.MemoryFileStorage',
                    'filestorage': 'fs.osfs.OSFS',
                    'filestorage_options': {
                        'root_path': '{}/file-storage'.format(
                            temporary_directory
                        ),
                        'create': 'true'
                    }
                },
            }
        ]
    }
    cfg_path = os.path.join(temporary_directory, 'onegov.yml')
    with open(cfg_path, 'w') as f:
        f.write(yaml.dump(cfg))

    principal = {
        'name': 'Govikon',
        'canton': 'be',
        'color': '#fff',
        'logo': 'canton-be.svg',
    }
    principal_path = os.path.join(
        temporary_directory, 'file-storage/onegov_election_day-govikon'
    )
    os.makedirs(principal_path)
    with open(os.path.join(principal_path, 'principal.yml'), 'w') as f:
        f.write(yaml.dump(principal, default_flow_style=False))

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/govikon',
        'add',
    ])
    assert result.exit_code == 0
    assert "Instance was created successfully" in result.output

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/govikon',
        'add',
    ])
    assert result.exit_code == 1
    assert "This selector may not reference an existing path" in result.output


def test_add_instance_missing_config(postgres_dsn, temporary_directory):

    cfg = {
        'applications': [
            {
                'path': '/onegov_election_day/*',
                'application': 'onegov.election_day.ElectionDayApp',
                'namespace': 'onegov_election_day',
                'configuration': {
                    'dsn': postgres_dsn,
                    'depot_backend': 'depot.io.memory.MemoryFileStorage',
                    'filestorage': 'fs.osfs.OSFS',
                    'filestorage_options': {
                        'root_path': '{}/file-storage'.format(
                            temporary_directory
                        ),
                        'create': 'true'
                    }
                },
            }
        ]
    }

    cfg_path = os.path.join(temporary_directory, 'onegov.yml')
    with open(cfg_path, 'w') as f:
        f.write(yaml.dump(cfg))

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/govikon',
        'add',
    ])
    assert result.exit_code == 0
    assert "principal.yml not found" in result.output
    assert "Instance was created successfully" in result.output


def test_fetch(postgres_dsn, temporary_directory, session_manager):

    runner = CliRunner()

    cfg = {
        'applications': [
            {
                'path': '/onegov_election_day/*',
                'application': 'onegov.election_day.ElectionDayApp',
                'namespace': 'onegov_election_day',
                'configuration': {
                    'dsn': postgres_dsn,
                    'depot_backend': 'depot.io.memory.MemoryFileStorage',
                    'filestorage': 'fs.osfs.OSFS',
                    'filestorage_options': {
                        'root_path': '{}/file-storage'.format(
                            temporary_directory
                        ),
                        'create': 'true'
                    }
                },
            }
        ]
    }
    cfg_path = os.path.join(temporary_directory, 'onegov.yml')
    with open(cfg_path, 'w') as f:
        f.write(yaml.dump(cfg))

    assert 'onegov_election_day-thun' not in session_manager.list_schemas()
    assert 'onegov_election_day-bern' not in session_manager.list_schemas()
    assert 'onegov_election_day-be' not in session_manager.list_schemas()

    principals = {
        'be': {
            'name': 'Kanton Bern',
            'canton': 'be',
            'color': '#fff',
            'logo': 'canton-be.svg',
            'fetch': {
                'bern': ['municipality'],
                'thun': ['municipality']
            }
        },
        'bern': {
            'name': 'Stadt Bern',
            'municipality': '351',
            'color': '#fff',
            'logo': 'municipality-351.svg',
            'fetch': {
                'be': ['federation', 'canton'],
            }
        },
        'thun': {
            'name': 'Stadt Thun',
            'municipality': '942',
            'color': '#fff',
            'logo': 'municipality-942.svg',
            'fetch': {}
        }
    }
    for principal in principals:
        principal_path = os.path.join(
            temporary_directory,
            'file-storage/onegov_election_day-{}'.format(principal)
        )
        os.makedirs(principal_path)
        with open(os.path.join(principal_path, 'principal.yml'), 'w') as f:
            f.write(yaml.dump(principals[principal], default_flow_style=False))

        result = runner.invoke(cli, [
            '--config', cfg_path,
            '--select', '/onegov_election_day/{}'.format(principal),
            'add',
        ])
        assert result.exit_code == 0
        assert "Instance was created successfully" in result.output

    assert 'onegov_election_day-thun' in session_manager.list_schemas()
    assert 'onegov_election_day-bern' in session_manager.list_schemas()
    assert 'onegov_election_day-be' in session_manager.list_schemas()

    last_result_change = datetime(2010, 1, 1, 0, 0, tzinfo=timezone.utc)

    results = (
        ('be', 'canton', 'vote-1'),
        ('be', 'canton', 'vote-2'),
        ('be', 'federation', 'vote'),
        ('bern', 'federation', 'vote'),
        ('bern', 'canton', 'vote-1'),
        ('bern', 'canton', 'vote-2'),
        ('bern', 'municipality', 'vote-1'),
        ('bern', 'municipality', 'vote-2'),
        ('thun', 'canton', 'vote-1'),
        ('thun', 'canton', 'vote-2'),
        ('thun', 'municipality', 'vote-1'),
        ('thun', 'municipality', 'vote-2'),
    )

    def get_schema(entity):
        return 'onegov_election_day-{}'.format(entity)

    def get_session(entity):
        session_manager.set_current_schema(get_schema(entity))
        return session_manager.session()

    for entity, domain, title in results:
        get_session(entity).add(
            ArchivedResult(
                date=date(2010, 1, 1),
                last_result_change=last_result_change,
                schema=get_schema(entity),
                url='{}/{}/{}'.format(entity, domain, title),
                title=title,
                domain=domain,
                name=entity,
                type='vote',
            )
        )
        get_session(entity).flush()
        transaction.commit()

    results = (
        ('be', 'canton', 'vote-3', 0, False, False),
        ('be', 'canton', 'vote-4', 0, False, False),
        ('be', 'canton', 'vote-5', 0, True, False),
        ('be', 'canton', 'vote-6', 1, False, False),
        ('be', 'canton', 'vote-7', 1, True, False),
        ('be', 'canton', 'vote-8', 1, True, True),
        ('be', 'canton', 'vote-9', 2, False, False),
        ('be', 'canton', 'vote-10', 2, True, False),
        ('be', 'canton', 'vote-11', 2, True, True),
    )
    for entity, domain, title, vote_type, with_id, with_result in results:
        id = '{}-{}-{}'.format(entity, domain, title)
        then = date(2010, 1, 1)

        vote = None
        if vote_type:
            vote = Vote(id=id, title=title, domain=domain, date=then)
            vote.ballots.append(Ballot(type='proposal'))

            if with_result:
                vote.proposal.results.append(
                    BallotResult(
                        group='Bern', entity_id=351,
                        counted=True, yeas=30, nays=10, empty=0, invalid=0
                    )
                )

            if vote_type > 1:
                vote.ballots.append(Ballot(type='counter-proposal'))
                vote.ballots.append(Ballot(type='tie-breaker'))

                if with_result:
                    vote.counter_proposal.results.append(
                        BallotResult(
                            group='Bern', entity_id=351,
                            counted=True, yeas=35, nays=5, empty=0, invalid=0
                        )
                    )
                    vote.tie_breaker.results.append(
                        BallotResult(
                            group='Bern', entity_id=351,
                            counted=True, yeas=0, nays=40, empty=0, invalid=0
                        )
                    )

            get_session(entity).add(vote)
            get_session(entity).flush()
            transaction.commit()

        get_session(entity).add(
            ArchivedResult(
                date=then,
                last_result_change=last_result_change,
                schema=get_schema(entity),
                url='{}/{}/{}'.format(entity, domain, title),
                title=title,
                domain=domain,
                name=entity,
                type='vote',
                meta={'id': id} if with_id else None
            )
        )
        get_session(entity).flush()
        transaction.commit()

    assert get_session('be').query(ArchivedResult).count() == 12
    assert get_session('bern').query(ArchivedResult).count() == 5
    assert get_session('thun').query(ArchivedResult).count() == 4

    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/be',
        'fetch',
    ])
    assert result.exit_code == 0

    assert get_session('be').query(ArchivedResult).count() == 12 + 4
    assert get_session('bern').query(ArchivedResult).count() == 5
    assert get_session('thun').query(ArchivedResult).count() == 4

    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/bern',
        'fetch',
    ])
    assert result.exit_code == 0

    assert get_session('be').query(ArchivedResult).count() == 12 + 4
    assert get_session('bern').query(ArchivedResult).count() == 5 + 12
    assert get_session('thun').query(ArchivedResult).count() == 4

    meta = {
        r.meta['id']: r.meta
        for r in get_session('bern').query(ArchivedResult)
        if r.meta and 'id' in r.meta
    }
    assert sorted(meta.keys()) == [
        'be-canton-vote-{}'.format(i) for i in (10, 11, 5, 7, 8)
    ]
    assert meta['be-canton-vote-8']['local'] == {
        'answer': 'accepted',
        'yeas_percentage': 75.0,
        'nays_percentage': 25.0
    }
    assert meta['be-canton-vote-11']['local'] == {
        'answer': 'counter-proposal',
        'yeas_percentage': 87.5,
        'nays_percentage': 12.5
    }

    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/thun',
        'fetch',
    ])
    assert result.exit_code == 0

    assert get_session('be').query(ArchivedResult).count() == 12 + 4
    assert get_session('bern').query(ArchivedResult).count() == 5 + 12
    assert get_session('thun').query(ArchivedResult).count() == 4


def test_send_sms(postgres_dsn, temporary_directory):

    schema = 'onegov_election_day-govikon'
    cfg_path = os.path.join(temporary_directory, 'onegov.yml')
    with open(cfg_path, 'w') as f:
        f.write(yaml.dump({
            'applications': [
                {
                    'path': '/onegov_election_day/*',
                    'application': 'onegov.election_day.ElectionDayApp',
                    'namespace': 'onegov_election_day',
                    'configuration': {
                        'dsn': postgres_dsn,
                        'depot_backend': 'depot.io.memory.MemoryFileStorage',
                        'filestorage': 'fs.osfs.OSFS',
                        'filestorage_options': {
                            'root_path': '{}/file-storage'.format(
                                temporary_directory
                            ),
                            'create': 'true'
                        },
                        'sms_directory': '{}/sms'.format(
                            temporary_directory
                        ),
                    },
                }
            ]
        }))

    principal_path = os.path.join(temporary_directory, 'file-storage', schema)
    os.makedirs(principal_path)
    with open(os.path.join(principal_path, 'principal.yml'), 'w') as f:
        f.write(
            yaml.dump({
                'name': 'Govikon',
                'canton': 'be',
                'color': '#fff',
                'logo': 'canton-be.svg',
            }, default_flow_style=False)
        )

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/govikon',
        'add',
    ])
    assert result.exit_code == 0
    assert "Instance was created successfully" in result.output

    sms_path = os.path.join(temporary_directory, 'sms', schema)
    os.makedirs(sms_path)

    # no sms yet
    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', cfg_path, '--select', '/onegov_election_day/govikon',
        'send_sms', 'username', 'password'
    ])
    assert result.exit_code == 0

    with open(os.path.join(sms_path, '+417772211.000000'), 'w') as f:
        f.write('Fancy new results!')

    with patch('requests.post') as post:
        runner = CliRunner()
        result = runner.invoke(cli, [
            '--config', cfg_path, '--select', '/onegov_election_day/govikon',
            'send_sms', 'username', 'password'
        ])
        assert post.called
        assert post.call_args[0] == (
            'https://json.aspsms.com/SendSimpleTextSMS',
        )
        assert post.call_args[1] == {
            'json': {
                'MessageText': 'Fancy new results!',
                'Originator': 'OneGov',
                'Password': 'password',
                'Recipients': ['+417772211'],
                'UserName': 'username'
            }
        }
        assert result.exit_code == 0
