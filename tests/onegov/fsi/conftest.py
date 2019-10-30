import datetime

import pytest
import transaction

from onegov.core.crypto import hash_password
from onegov.fsi.models.course_attendee import CourseAttendee
from onegov.fsi.models.course import Course
from onegov.fsi.models.course_event import CourseEvent
from onegov.fsi.models.reservation import Reservation
from onegov.user import User
from onegov.fsi import FsiApp
from onegov.fsi.initial_content import create_new_organisation
from tests.shared.utils import create_app
from tests.onegov.org.conftest import Client


@pytest.fixture(scope='session')
def hashed_password():
    return hash_password('test_password')


@pytest.yield_fixture(scope='function')
def fsi_app(request, hashed_password):
    yield create_fsi_app(request, False, hashed_password)


@pytest.yield_fixture(scope='function')
def es_fsi_app(request, hashed_password):
    yield create_fsi_app(request, True, hashed_password)


@pytest.fixture(scope='function')
def client(fsi_app):
    return Client(fsi_app)


@pytest.fixture(scope='function')
def client_with_es(es_fsi_app):
    return Client(es_fsi_app)


@pytest.fixture(scope='function')
def admin(session, hashed_password):
    admin = session.query(User).filter_by(
        username='admin@example.org').first()
    if not admin:
        admin = User(
            username='admin@example.org',
            password_hash=hashed_password,
            role='admin'
        )
        session.add(admin)
        session.flush()
    return admin


@pytest.fixture(scope='function')
def member(session, hashed_password):
    member = session.query(User).filter_by(
        username='member@example.org').first()
    if not member:
        member = User(
            username='member@example.org',
            password_hash=hashed_password,
            role='member'
        )
        session.add(member)
        session.flush()
    return member


@pytest.fixture(scope='function')
def course(session):
    data = dict(
        description='Desc',
        name='Course',
        presenter_name='Pres',
        presenter_company='Company',
        mandatory_refresh=True,
        refresh_interval=datetime.timedelta(days=30)
    )
    course = Course(**data)
    session.add(course)
    session.flush()
    return course, data


@pytest.fixture(scope='function')
def course_event(session, course):
    data = dict(
        course_id=course[0].id,
        name='Event',
        start=datetime.datetime(2019, 1, 1, 12, 0),
        end=datetime.datetime(2019, 1, 1, 14, 0),
        presenter_name='Presenter',
        presenter_company='Company'

    )
    course_event = CourseEvent(**data)
    session.add(course_event)
    session.flush()
    return course_event, data


@pytest.fixture(scope='function')
def proto_reservation(session):
    return Reservation()


@pytest.fixture(scope='function')
def placeholder(session):
    data = dict(
        first_name='F',
        last_name='L',
        email='placeholder@example.org',
        address='Address'
    )
    attendee = session.query(CourseAttendee).filter_by(
        email='placeholder@example.org').first()
    if not attendee:
        attendee = CourseAttendee(**data)
        session.add(attendee)
        session.flush()
    return attendee, data


@pytest.fixture(scope='function')
def attendee(session, admin):
    attendee = session.query(CourseAttendee).filter_by(
        email='attendee@example.org').first()
    data = dict(
        first_name='F',
        last_name='L',
        email='attendee@example.org',
        address='Address',
        user_id=admin.id
    )
    if not attendee:
        attendee = CourseAttendee(**data)
        session.add(attendee)
        session.flush()
    return attendee, data


@pytest.fixture(scope='function')
def db_mock_session(
        session, course_event, course, member, attendee, placeholder):
    # Create Reservations
    res = Reservation(
        attendee_id=attendee[0].id,
        course_event_id=course_event[0].id)
    res2 = Reservation(
        attendee_id=placeholder[0].id,
        course_event_id=course_event[0].id)
    session.add_all([res, res2])
    session.flush()
    return session


def create_fsi_app(request, use_elasticsearch, hashed_password):

    app = create_app(
        app_class=FsiApp,
        request=request,
        use_elasticsearch=use_elasticsearch)

    session = app.session()

    org = create_new_organisation(app, name="Kursverwaltung")
    org.meta['reply_to'] = 'mails@govikon.ch'
    org.meta['locales'] = 'de_CH'

    # usually we don't want to create the users directly, anywhere else you
    # *need* to go through the UserCollection. Here however, we can improve
    # the test speed by not hashing the password for every test.

    session.add(User(
        username='admin@example.org',
        password_hash=hashed_password,
        role='admin'
    ))
    session.add(User(
        username='editor@example.org',
        password_hash=hashed_password,
        role='editor'
    ))

    session.add(User(
        username='member@example.org',
        password_hash=hashed_password,
        role='member'
    ))

    transaction.commit()
    session.close_all()

    return app