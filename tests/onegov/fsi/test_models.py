import datetime

from onegov.fsi.models.course import Course
from onegov.fsi.models.course_event import CourseEvent
from onegov.fsi.models.reservation import Reservation


def test_course_1(session, course, attendee):
    course, data = course
    for key, val in data.items():
        assert getattr(course, key) == val

    assert course.events == []

    # Add an event
    today = datetime.datetime.today()
    event = CourseEvent(
        course_id=course.id,
        name='N',
        start=today,
        end=today + datetime.timedelta(hours=2),
        presenter_name='P',
        presenter_company='C'
    )
    course.events.append(event)
    assert len(course.events) == 1
    assert session.query(CourseEvent).one()


def test_attendee(session, attendee, course_event):
    attendee, data = attendee
    for key, val in data.items():
        assert getattr(attendee, key) == val
    assert attendee.reservations.count() == 0

    # Add a reservation
    reservation = Reservation(
        course_event_id=course_event[0].id, attendee_id=attendee.id)
    session.add(reservation)
    session.flush()
    assert attendee.reservations.count() == 1

    # Test reservation backref
    assert reservation.attendee == attendee

    # Check the event of the the reservation
    assert attendee.reservations[0].course_event == course_event[0]

    # delete the reservation
    attendee.reservations.remove(reservation)

    # and add it differently
    attendee.reservations.append(reservation)
    assert attendee.reservations.count() == 1


def test_course_event(session, course_event, placeholder):
    event, data = course_event
    for key, val in data.items():
        assert getattr(event, key) == val

    assert event.attendees.all() == []
    assert event.reservations.all() == []

    # Add a participant via a reservation
    reservation = Reservation(
        course_event_id=event.id, attendee_id=placeholder[0].id)
    session.add(reservation)
    session.flush()

    assert event.reservations.count() == 1
    assert event.attendees.count() == 1


def test_reservation(session, attendee, course_event):
    res = Reservation(
        course_event_id=course_event[0].id,
        attendee_id=attendee[0].id
    )
    session.add(res)
    session.flush()

    # Test backrefs
    assert res.course_event == course_event[0]
    assert res.attendee == attendee[0]


def test_cascading_course_deletion(db_mock_session):
    # When a course is deleted, all course events should be deleted as well
    session = db_mock_session
    course = session.query(Course).one()
    session.delete(course)
    session.flush()
    assert session.query(CourseEvent).count() == 0
    assert session.query(Reservation).count() == 0


def test_cascading_event_deletion(db_mock_session, course_event):
    # If a course event is deleted, all the reservations should be deleted
    session = db_mock_session
    assert session.query(Reservation).count() == 2
    session.delete(course_event[0])
    session.flush()
    assert session.query(Reservation).count() == 0


def test_cascading_attendee_deletion(db_mock_session, attendee):
    # If an attendee is deleted, his reservations should be deleted
    session = db_mock_session
    assert session.query(Reservation).count() == 2
    session.delete(attendee[0])
    session.flush()
    assert session.query(Reservation).count() == 1