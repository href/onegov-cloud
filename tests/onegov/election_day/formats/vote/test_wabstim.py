import tarfile
from datetime import date
from io import BytesIO
from onegov.ballot import Vote
from onegov.election_day.formats import import_vote_wabstim
from onegov.election_day.models import Municipality
from tests.onegov.election_day.common import get_tar_file_path


def test_import_wabstim_vote_1(session):
    domain = 'municipality'

    session.add(
        Vote(title='vote', domain=domain, date=date(2016, 2, 28))
    )
    session.flush()
    vote = session.query(Vote).one()

    tar_file = get_tar_file_path(model='vote', api_format='wabstim')

    # The tar file contains vote results from Walenstadt
    with tarfile.open(tar_file, 'r|gz') as f:
        xlsx = f.extractfile(f.next()).read()

    principal = Municipality(municipality='3298', name='Walenstadt')
    errors = import_vote_wabstim(
        vote, principal, BytesIO(xlsx), 'application/excel'
    )
    assert not errors
    assert vote.completed
    assert vote.ballots.count() == 1
    assert round(vote.turnout, 2) == 47.44
    assert vote.eligible_voters == 3638
    assert vote.cast_ballots == 1726
    assert vote.answer == 'rejected'
    assert vote.proposal.results.count() == 1
    assert vote.proposal.yeas == 439
    assert vote.proposal.nays == 1262


def test_import_wabstim_vote_utf16(session):
    session.add(
        Vote(title='vote', domain='municipality', date=date(2017, 2, 12))
    )
    session.flush()
    vote = session.query(Vote).one()
    principal = Municipality(municipality='3427')

    errors = import_vote_wabstim(
        vote, principal,
        BytesIO((
            '\n'.join((
                ','.join((
                    'Freigegeben',
                    'StiLeer',
                    'StiUngueltig',
                    'StiJaHG',
                    'StiNeinHG',
                    'StiOhneAwHG',
                    'StiJaN1',
                    'StiNeinN1',
                    'StiOhneAwN1',
                    'StiJaN2',
                    'StiNeinN2',
                    'StiOhneAwN2',
                    'Stimmberechtigte',
                    'BFS',
                )),
            ))
        ).encode('utf-16-le')),
        'text/plain'
    )
    assert [e.error for e in errors] == ['No data found']


def test_import_wabstim_vote_missing_headers(session):
    session.add(
        Vote(title='vote', domain='municipality', date=date(2017, 2, 12))
    )
    session.flush()
    vote = session.query(Vote).one()
    principal = Municipality(municipality='3427')

    errors = import_vote_wabstim(
        vote, principal,
        BytesIO((
            '\n'.join((
                ','.join((
                    'Freigegeben',
                    'StiLeer',
                    'StiUngueltig',
                    'StiJaHG',
                    'StiNeinHG',
                    'StiOhneAwHG',
                    'StiJaN1',
                    'StiNeinN1',
                    'StiOhneAwN1',
                    'StiJaN2',
                    'StiNeinN2',
                    'StiOhneAwN2',
                    'BFS',
                )),
            ))
        ).encode('utf-8')),
        'text/plain'
    )
    assert [e.error.interpolate() for e in errors] == [
        "Missing columns: 'stimmberechtigte'"
    ]


def test_import_wabstim_vote_invalid_values(session):
    session.add(
        Vote(title='vote', domain='municipality', date=date(2017, 2, 12))
    )
    session.flush()
    vote = session.query(Vote).one()
    principal = Municipality(municipality='3427')

    errors = import_vote_wabstim(
        vote, principal,
        BytesIO((
            '\n'.join((
                ','.join((
                    'Freigegeben',
                    'StiLeer',
                    'StiUngueltig',
                    'StiJaHG',
                    'StiNeinHG',
                    'StiOhneAwHG',
                    'StiJaN1',
                    'StiNeinN1',
                    'StiOhneAwN1',
                    'StiJaN2',
                    'StiNeinN2',
                    'StiOhneAwN2',
                    'Stimmberechtigte',
                    'BFS',
                )),
                ','.join((
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                    'xxx',
                )),
                ','.join((
                    '14:15',  # Freigegeben
                    '0',  # StiLeer
                    '0',  # StiUngueltig
                    '10',  # StiJaHG
                    '20',  # StiNeinHG
                    '',  # StiOhneAwHG
                    '',  # StiJaN1
                    '',  # StiNeinN1
                    '',  # StiOhneAwN1
                    '',  # StiJaN2
                    '',  # StiNeinN2
                    '',  # StiOhneAwN2
                    '100',  # Stimmberechtigte
                    '3427',  # BFS
                )),
                ','.join((
                    '14:15',  # Freigegeben
                    '0',  # StiLeer
                    '0',  # StiUngueltig
                    '10',  # StiJaHG
                    '20',  # StiNeinHG
                    '',  # StiOhneAwHG
                    '',  # StiJaN1
                    '',  # StiNeinN1
                    '',  # StiOhneAwN1
                    '',  # StiJaN2
                    '',  # StiNeinN2
                    '',  # StiOhneAwN2
                    '100',  # Stimmberechtigte
                    '3427',  # BFS
                )),
                ','.join((
                    '14:15',  # Freigegeben
                    '0',  # StiLeer
                    '0',  # StiUngueltig
                    '10',  # StiJaHG
                    '20',  # StiNeinHG
                    '',  # StiOhneAwHG
                    '',  # StiJaN1
                    '',  # StiNeinN1
                    '',  # StiOhneAwN1
                    '',  # StiJaN2
                    '',  # StiNeinN2
                    '',  # StiOhneAwN2
                    '100',  # Stimmberechtigte
                    '3428',  # BFS
                ))
            ))
        ).encode('utf-8')),
        'text/plain',
    )
    errors = sorted(set([
        (e.line, e.error.interpolate()) for e in errors
    ]))
    print(errors)
    assert errors == [
        (2, 'Invalid integer: bfs'),
        (2, 'Invalid integer: stijahg'),
        (2, 'Invalid integer: stileer'),
        (2, 'Invalid integer: stimmberechtigte'),
        (2, 'Invalid integer: stineinhg'),
        (2, 'Invalid integer: stiungueltig'),
        (4, '3427 was found twice'),
        (5, '3428 is unknown'),
    ]


def test_import_wabstim_vote_expats(session):
    session.add(
        Vote(title='vote', domain='municipality', date=date(2017, 2, 12))
    )
    session.flush()
    vote = session.query(Vote).one()
    principal = Municipality(municipality='3427')

    for expats in (False, True):
        vote.expats = expats
        errors = import_vote_wabstim(
            vote, principal,
            BytesIO((
                '\n'.join((
                    ','.join((
                        'Freigegeben',
                        'StiLeer',
                        'StiUngueltig',
                        'StiJaHG',
                        'StiNeinHG',
                        'StiOhneAwHG',
                        'StiJaN1',
                        'StiNeinN1',
                        'StiOhneAwN1',
                        'StiJaN2',
                        'StiNeinN2',
                        'StiOhneAwN2',
                        'Stimmberechtigte',
                        'BFS',
                    )),
                    ','.join((
                        '14:15',  # Freigegeben
                        '0',  # StiLeer
                        '0',  # StiUngueltig
                        '10',  # StiJaHG
                        '20',  # StiNeinHG
                        '',  # StiOhneAwHG
                        '',  # StiJaN1
                        '',  # StiNeinN1
                        '',  # StiOhneAwN1
                        '',  # StiJaN2
                        '',  # StiNeinN2
                        '',  # StiOhneAwN2
                        '100',  # Stimmberechtigte
                        '0',  # BFS
                    )),
                ))
            ).encode('utf-8')),
            'text/plain',
        )
        errors = [e.error.interpolate() for e in errors]
        if expats:
            assert errors == []
        else:
            assert errors == ['No data found']


def test_import_wabstim_vote_temporary_results(session):
    session.add(
        Vote(title='vote', domain='municipality', date=date(2017, 2, 12))
    )
    session.flush()
    vote = session.query(Vote).one()
    principal = Municipality(municipality='3427', name='Wil')

    errors = import_vote_wabstim(
        vote, principal,
        BytesIO((
            '\n'.join((
                ','.join((
                    'Freigegeben',
                    'StiLeer',
                    'StiUngueltig',
                    'StiJaHG',
                    'StiNeinHG',
                    'StiOhneAwHG',
                    'StiJaN1',
                    'StiNeinN1',
                    'StiOhneAwN1',
                    'StiJaN2',
                    'StiNeinN2',
                    'StiOhneAwN2',
                    'Stimmberechtigte',
                    'BFS',
                )),
                ','.join((
                    '',  # Freigegeben
                    '0',  # StiLeer
                    '0',  # StiUngueltig
                    '10',  # StiJaHG
                    '20',  # StiNeinHG
                    '',  # StiOhneAwHG
                    '',  # StiJaN1
                    '',  # StiNeinN1
                    '',  # StiOhneAwN1
                    '',  # StiJaN2
                    '',  # StiNeinN2
                    '',  # StiOhneAwN2
                    '100',  # Stimmberechtigte
                    '3427',  # BFS
                ))
            ))
        ).encode('utf-8')),
        'text/plain',
    )
    assert not errors
    assert [
        v.entity_id for v in vote.proposal.results.filter_by(counted=True)
    ] == []
    assert [
        v.entity_id for v in vote.proposal.results.filter_by(counted=False)
    ] == [3427]
