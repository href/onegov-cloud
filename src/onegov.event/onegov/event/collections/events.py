from datetime import date
from datetime import datetime
from datetime import timedelta
from icalendar import Calendar as vCalendar
from onegov.core.collection import Pagination
from onegov.core.utils import increment_name
from onegov.core.utils import normalize_for_url
from onegov.event.models import Event
from onegov.gis import Coordinates
from pytz import UTC
from sedate import as_datetime
from sedate import replace_timezone
from sedate import standardize_date
from sedate import to_timezone
from sqlalchemy import and_
from sqlalchemy import or_


class EventCollection(Pagination):

    """ Manage a list of events. """

    def __init__(self, session, page=0, state=None):
        self.session = session
        self.page = page
        self.state = state

    def __eq__(self, other):
        return self.state == other.state and self.page == other.page

    def subset(self):
        return self.query()

    @property
    def page_index(self):
        return self.page

    def page_by_index(self, index):
        return self.__class__(self.session, index, self.state)

    def for_state(self, state):
        """ Returns a new instance of the collection with the given state. """

        return self.__class__(self.session, 0, state)

    def query(self):
        query = self.session.query(Event)
        if self.state:
            query = query.filter(Event.state == self.state)
        query = query.order_by(Event.start)
        return query

    def _get_unique_name(self, name):
        """ Create a unique, URL-friendly name. """

        # it's possible for `normalize_for_url` to return an empty string...
        name = normalize_for_url(name) or "event"

        session = self.session
        while session.query(Event.name).filter(Event.name == name).first():
            name = increment_name(name)

        return name

    def add(self, title, start, end, timezone, autoclean=True, **optional):
        """ Add a new event.

        A unique, URL-friendly name is created automatically for this event
        using the title and optionally numbers for duplicate names.

        Every time a new event is added, old, stale events are deleted unless
        disabled with the ``autoclean`` option.

        Returns the created event or None if already automatically deleted.
        """
        if not start.tzinfo:
            start = replace_timezone(start, timezone)
        if not end.tzinfo:
            end = replace_timezone(end, timezone)

        event = Event(
            state='initiated',
            title=title,
            start=start,
            end=end,
            timezone=timezone,
            name=self._get_unique_name(title),
            **optional
        )

        self.session.add(event)
        self.session.flush()

        if autoclean:
            self.remove_stale_events()

        return event

    def delete(self, event):
        """ Delete an event. """

        self.session.delete(event)
        self.session.flush()

    def remove_stale_events(self, max_stale=None):
        """ Remove events which have never been submitted and are created more
        than five days ago.

        """

        if max_stale is None:
            max_stale = datetime.utcnow() - timedelta(days=5)
            max_stale = standardize_date(max_stale, 'UTC')

        events = self.session.query(Event).filter(
            Event.state == 'initiated',
            and_(
                or_(Event.created < max_stale, Event.created.is_(None)),
                or_(Event.modified < max_stale, Event.modified.is_(None))
            )
        )
        for event in events:
            self.session.delete(event)

        self.session.flush()

    def by_name(self, name):
        """ Returns an event by its URL-friendly name. """

        query = self.session.query(Event).filter(Event.name == name)
        return query.first()

    def by_id(self, id):
        """ Return an event by its id. """

        query = self.session.query(Event).filter(Event.id == id)
        return query.first()

    def from_ical(self, ical):
        """ Imports the events from an iCalender string.

        We assume the timezone to be Europe/Zurich!

        """

        cal = vCalendar.from_ical(ical)
        for vevent in cal.walk('vevent'):
            timezone = 'Europe/Zurich'
            start = vevent.get('dtstart')
            start = start.dt if start else None
            if type(start) is date:
                start = replace_timezone(as_datetime(start), UTC)
            elif type(start) is datetime:
                if start.tzinfo is None:
                    start = standardize_date(start, timezone)
                else:
                    start = to_timezone(start, UTC)

            end = vevent.get('dtend')
            end = end.dt if end else None
            if type(end) is date:
                end = replace_timezone(as_datetime(end), UTC)
                end = end - timedelta(microseconds=1)
            elif type(end) is datetime:
                if end.tzinfo is None:
                    end = standardize_date(end, timezone)
                else:
                    end = to_timezone(end, UTC)

            duration = vevent.get('duration')
            duration = duration.dt if duration else None
            if start and not end and duration:
                end = start + duration

            if not start and not end:
                raise(ValueError("Invalid date"))

            recurrence = vevent.get('rrule', '')
            if recurrence:
                recurrence = 'RRULE:{}'.format(recurrence.to_ical().decode())

            coordinates = vevent.get('geo')
            if coordinates:
                coordinates = Coordinates(
                    coordinates.latitude, coordinates.longitude
                )

            tags = vevent.get('categories')
            if tags:
                tags = [str(tag) for tag in tags]

            uid = str(vevent.get('uid', ''))
            description = str(vevent.get('description', ''))
            organizer = str(vevent.get('organizer', ''))
            location = str(vevent.get('location', ''))

            event = self.add(
                title=str(vevent.get('summary', '')),
                start=start,
                end=end,
                timezone=timezone,
                description=description,
                organizer=organizer,
                recurrence=recurrence,
                location=location,
                coordinates=coordinates,
                tags=tags,
                meta={'ical_uid': uid},
                autoclean=False
            )
            event.submit()
            event.publish()