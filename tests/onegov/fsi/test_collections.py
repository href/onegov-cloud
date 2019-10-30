import datetime
from uuid import uuid4

from onegov.fsi.collections.attendee import CourseAttendeeCollection
from onegov.fsi.collections.course import CourseCollection
from onegov.fsi.collections.course_event import CourseEventCollection
from onegov.fsi.models.course import Course
from mixer.backend.sqlalchemy import mixer

from onegov.fsi.models.course_event import CourseEvent
from tests.onegov.fsi.common import collection_attr_eq_test


def test_course_collection(session):
    new_courses = (
        mixer.blend(
            Course,
            refresh_interval=datetime.timedelta(days=20)
        ) for i in range(11)
    )

    collection = CourseCollection(session)
    session.add_all(new_courses)
    session.flush()

    # Test pagination
    assert len(collection.batch) == 10
    assert collection.page_index == 0
    assert collection.pages_count == 2

    result = collection.query()
    assert result.count() == 11

    next_ = collection.next
    assert next_.page_index != collection.page_index
    by_index = collection.page_by_index(2)

    collection_attr_eq_test(collection, by_index)

    # assert descending order
    assert result[0].created > result[1].created


def test_course_event_collection(session, course):
    now = datetime.date.today()     # model is actually DateTime
    new_course_events = (
        mixer.blend(
            CourseEvent,
            start=now + datetime.timedelta(days=i),
            course_id=course[0].id

        ) for i in (-1, 1, 2)
    )
    session.add_all(new_course_events)
    session.flush()

    collection = CourseEventCollection(session)
    collection_attr_eq_test(collection, collection.page_by_index(1))
    result = collection.query()

    # Should return upcoming events by default
    assert result.count() == 2

    # Test ordering and timestamp mixin
    assert result[0].created > result[1].created

    # Test all results
    collection = CourseEventCollection(session, upcoming_only=False)
    assert collection.query().count() == 3

    # Test filtering with wrong course id
    collection = CourseEventCollection(session, course_id=uuid4())
    assert collection.query().count() == 0

    # Test all past events
    collection = CourseEventCollection(session, past_only=True)
    assert collection.query().count() == 1

    # Test from specific date
    tmr = now + datetime.timedelta(days=1)
    collection = CourseEventCollection(session, from_date=tmr)
    assert collection.query().count() == 1


def test_attendee_collection(session, attendee, placeholder):
    collection = CourseAttendeeCollection(session)
    collection_attr_eq_test(collection, collection.page_by_index(1))

    assert collection.query().count() == 2

    # Exlude placeholders and return real users
    collection = CourseAttendeeCollection(session, no_placeholders=True)
    assert collection.query().count() == 1