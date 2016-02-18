from datetime import date
from onegov.ballot import Election, ElectionCollection, Vote, VoteCollection


def test_elections_by_date(session):
    session.add(Election(
        title="first",
        domain='federation',
        type='majorz',
        date=date(2015, 6, 14)
    ))
    session.add(Election(
        title="last",
        domain='canton',
        type='majorz',
        date=date(2015, 6, 14)
    ))
    session.add(Election(
        title="second",
        domain='federation',
        type='majorz',
        date=date(2015, 6, 14)
    ))
    session.add(Election(
        title="ignore",
        domain='canton',
        type='majorz',
        date=date(2015, 6, 12)
    ))

    session.flush()

    collection = ElectionCollection(session)

    # sort by domain, then by date
    assert [v.title for v in collection.by_date(date(2015, 6, 14))] == [
        'first',
        'second',
        'last'
    ]


def test_elections_get_latest(session):
    session.add(Election(
        title="latest",
        domain='federation',
        type='majorz',
        date=date(2015, 6, 14)
    ))
    session.add(Election(
        title="older",
        domain='canton',
        type='majorz',
        date=date(2015, 6, 12)
    ))

    session.flush()

    collection = ElectionCollection(session)

    # sort by domain, then by date
    assert [v.title for v in collection.get_latest()] == ['latest']


def test_elections_get_years(session):
    session.add(Election(
        title="latest",
        domain='federation',
        type='majorz',
        date=date(2015, 6, 14)
    ))
    session.add(Election(
        title="older",
        domain='federation',
        type='majorz',
        date=date(2015, 3, 14)
    ))
    session.add(Election(
        title="even-older",
        domain='canton',
        type='majorz',
        date=date(2013, 6, 12)
    ))

    session.flush()

    assert ElectionCollection(session).get_years() == [2015, 2013]


def test_elections_by_years(session):
    session.add(Election(
        title="latest",
        domain='federation',
        type='majorz',
        date=date(2015, 6, 14)
    ))
    session.add(Election(
        title="older",
        domain='canton',
        type='majorz',
        date=date(2014, 6, 12)
    ))

    session.flush()

    elections = ElectionCollection(session, year=2015)
    assert len(elections.by_year()) == 1
    assert elections.by_year()[0].title == "latest"

    assert len(elections.by_year(2014)) == 1
    assert elections.by_year(2014)[0].title == "older"

    assert len(elections.by_year(2013)) == 0


def test_elections_shortcode_order(session):
    session.add(Election(
        title="A",
        shortcode="Z",
        domain='federation',
        type='majorz',
        date=date(2015, 6, 14)
    ))
    session.add(Election(
        title="Z",
        shortcode="A",
        domain='federation',
        type='majorz',
        date=date(2015, 6, 14)
    ))

    session.flush()

    elections = ElectionCollection(session, year=2015).by_year()
    assert elections[0].title == "Z"
    assert elections[1].title == "A"


def test_votes_by_date(session):
    session.add(Vote(
        title="first",
        domain='federation',
        date=date(2015, 6, 14)
    ))
    session.add(Vote(
        title="last",
        domain='canton',
        date=date(2015, 6, 14)
    ))
    session.add(Vote(
        title="second",
        domain='federation',
        date=date(2015, 6, 14)
    ))
    session.add(Vote(
        title="ignore",
        domain='canton',
        date=date(2015, 6, 12)
    ))

    session.flush()

    collection = VoteCollection(session)

    # sort by domain, then by date
    assert [v.title for v in collection.by_date(date(2015, 6, 14))] == [
        'first',
        'second',
        'last'
    ]


def test_votes_get_latest(session):
    session.add(Vote(
        title="latest",
        domain='federation',
        date=date(2015, 6, 14)
    ))
    session.add(Vote(
        title="older",
        domain='canton',
        date=date(2015, 6, 12)
    ))

    session.flush()

    collection = VoteCollection(session)

    # sort by domain, then by date
    assert [v.title for v in collection.get_latest()] == ['latest']


def test_votes_get_years(session):
    session.add(Vote(
        title="latest",
        domain='federation',
        date=date(2015, 6, 14)
    ))
    session.add(Vote(
        title="older",
        domain='federation',
        date=date(2015, 3, 14)
    ))
    session.add(Vote(
        title="even-older",
        domain='canton',
        date=date(2013, 6, 12)
    ))

    session.flush()

    assert VoteCollection(session).get_years() == [2015, 2013]


def test_votes_by_years(session):
    session.add(Vote(
        title="latest",
        domain='federation',
        date=date(2015, 6, 14)
    ))
    session.add(Vote(
        title="older",
        domain='canton',
        date=date(2014, 6, 12)
    ))

    session.flush()

    votes = VoteCollection(session, year=2015)
    assert len(votes.by_year()) == 1
    assert votes.by_year()[0].title == "latest"

    assert len(votes.by_year(2014)) == 1
    assert votes.by_year(2014)[0].title == "older"

    assert len(votes.by_year(2013)) == 0


def test_votes_shortcode_order(session):
    session.add(Vote(
        title="A",
        shortcode="Z",
        domain='federation',
        date=date(2015, 6, 14)
    ))
    session.add(Vote(
        title="Z",
        shortcode="A",
        domain='federation',
        date=date(2015, 6, 14)
    ))

    session.flush()

    votes = VoteCollection(session, year=2015).by_year()
    assert votes[0].title == "Z"
    assert votes[1].title == "A"
