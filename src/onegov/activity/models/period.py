import sedate

from datetime import date, datetime
from onegov.activity.models.age_barrier import AgeBarrier
from onegov.activity.models.booking import Booking
from onegov.activity.models.occasion import Occasion
from onegov.core.orm import Base
from onegov.core.orm.mixins import TimestampMixin
from onegov.core.orm.types import UUID, JSON
from sqlalchemy import Boolean
from sqlalchemy import desc, not_, distinct
from sqlalchemy import CheckConstraint
from sqlalchemy import column
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import Text
from sqlalchemy.orm import object_session, relationship, joinedload, defer
from sqlalchemy.orm import validates
from uuid import uuid4


class Period(Base, TimestampMixin):

    __tablename__ = 'periods'

    # It's doubtful that the Ferienpass would ever run anywhere else but
    # in Switzerland ;)
    timezone = 'Europe/Zurich'

    #: The public id of this period
    id = Column(UUID, primary_key=True, default=uuid4)

    #: The public title of this period
    title = Column(Text, nullable=False)

    #: Only one period is active at a time
    active = Column(Boolean, nullable=False, default=False)

    #: A confirmed period may not be automatically matched anymore and all
    #: booking changes to it are communicted to the customer
    confirmed = Column(Boolean, nullable=False, default=False)

    #: A confirmable period has a prebooking phase, while an unconfirmable
    # booking does not. An unconfirmable booking starts as `confirmed` for
    # legacy reasons (even though it doesn't sound sane to have an
    # unconfirmable period that is confirmed).
    confirmable = Column(Boolean, nullable=False, default=True)

    #: A finalized period may not have any change in bookings anymore
    finalized = Column(Boolean, nullable=False, default=False)

    #: A finalizable period may have invoices associated with it, an
    #: unfinalizable period may not
    finalizable = Column(Boolean, nullable=False, default=True)

    #: An archived period has been entirely completed
    archived = Column(Boolean, nullable=False, default=False)

    #: Start of the wishlist-phase
    prebooking_start = Column(Date, nullable=False)

    #: End of the wishlist-phase
    prebooking_end = Column(Date, nullable=False)

    #: Start of the booking-phase
    booking_start = Column(Date, nullable=False)

    #: End of the booking-phase
    booking_end = Column(Date, nullable=False)

    #: Date of the earliest possible occasion start of this period
    execution_start = Column(Date, nullable=False)

    #: Date of the latest possible occasion end of this period
    execution_end = Column(Date, nullable=False)

    #: Extra data stored on the period
    data = Column(JSON, nullable=False, default=dict)

    #: Maximum number of bookings per attendee
    max_bookings_per_attendee = Column(Integer, nullable=True)

    #: Base cost for one or many bookings
    booking_cost = Column(Numeric(precision=8, scale=2), nullable=True)

    #: True if the booking cost is meant for all bookings in a period
    #: or for each single booking
    all_inclusive = Column(Boolean, nullable=False, default=False)

    #: True if the costs of an occasions need to be paid to the organiser
    pay_organiser_directly = Column(Boolean, nullable=False, default=False)

    #: Time between bookings in minutes
    minutes_between = Column(Integer, nullable=True, default=0)

    #: The alignment of bookings in the matching
    alignment = Column(Text, nullable=True)

    #: Deadline for booking occasions. A deadline of 3 means that 3 days before
    #: an occasion is set to start, bookings are disabled.
    #:
    #: Note, unless book_finalized is set to True, this setting has no effect
    #: in a finalized period.
    #:
    #: Also, if deadline_days is None, bookings can't be created in a
    #: finalized period either, as deadline_days is a prerequisite for the
    #: book_finalized setting.
    deadline_days = Column(Integer, nullable=True)

    #: True if bookings can be created by normal users in finalized periods.
    #: The deadline_days are still applied for these normal users.
    #: Admins can always create bookings during any time, deadline_days and
    #: book_finalized are ignored.
    book_finalized = Column(Boolean, nullable=False, default=False)

    #: Date after which no bookings can be canceled by a mere member
    cancellation_date = Column(Date, nullable=True)

    #: Days between the occasion and the cancellation (an alternative to
    #: the cancellation_date)
    cancellation_days = Column(Integer, nullable=True)

    #: The age barrier implementation in use
    age_barrier_type = Column(Text, nullable=False, default='exact')

    __table_args__ = (
        CheckConstraint(' AND '.join((
            # ranges should be valid
            'prebooking_start <= prebooking_end',
            'booking_start <= booking_end',
            'execution_start <= execution_end',

            # pre-booking must happen before booking and execution
            'prebooking_end <= booking_start',
            'prebooking_end <= execution_start',

            # booking and execution may overlap, but the execution cannot
            # start before booking begins
            'booking_start <= execution_start',
            'booking_end <= execution_end',
        )), name='period_date_order'),
        Index(
            'only_one_active_period', 'active',
            unique=True, postgresql_where=column('active') == True
        )
    )

    #: The occasions linked to this period
    occasions = relationship(
        'Occasion',
        order_by='Occasion.order',
        backref='period'
    )

    #: The bookings linked to this period
    bookings = relationship(
        'Booking',
        backref='period'
    )

    @validates('age_barrier_type')
    def validate_age_barrier_type(self, key, age_barrier_type):
        assert age_barrier_type in AgeBarrier.registry
        return age_barrier_type

    @property
    def age_barrier(self):
        return AgeBarrier.from_name(self.age_barrier_type)

    def activate(self):
        """ Activates the current period, causing all occasions and activites
        to update their status and book-keeping.

        It also makes sure no other period is active.

        """
        if self.active:
            return

        session = object_session(self)
        model = self.__class__

        active_period = session.query(model)\
            .filter(model.active == True).first()

        if active_period:
            active_period.deactivate()

        # avoid triggering the only_one_active_period index constraint
        session.flush()

        self.active = True

    def deactivate(self):
        """ Deactivates the current period, causing all occasions and activites
        to update their status and book-keeping.

        """

        if not self.active:
            return

        self.active = False

    def confirm(self):
        """ Confirms the current period. """

        self.confirmed = True

        # open bookings are marked as denied during completion
        # and the booking costs are copied over permanently (so they can't
        # change anymore)
        b = object_session(self).query(Booking)
        b = b.filter(Booking.period_id == self.id)
        b = b.options(joinedload(Booking.occasion))
        b = b.options(
            defer(Booking.group_code),
            defer(Booking.attendee_id),
            defer(Booking.priority),
            defer(Booking.username),
        )

        for booking in b:
            if booking.state == 'open':
                booking.state = 'denied'

            booking.cost = booking.occasion.total_cost

    def archive(self):
        """ Moves all accepted activities with an occasion in this period
        into the archived state, unless there's already another occasion
        in a period newer than the current period.

        """
        assert self.confirmed and self.finalized or not self.finalizable

        self.archived = True
        self.active = False

        session = object_session(self)

        def future_periods():
            p = session.query(Period)
            p = p.order_by(desc(Period.execution_start))
            p = p.with_entities(Period.id)

            for period in p:
                if period.id == self.id:
                    break
                yield period.id

        # get the activities which have an occasion in a future period
        f = session.query(Occasion)
        f = f.with_entities(Occasion.activity_id)
        f = f.filter(Occasion.period_id.in_(tuple(future_periods())))

        # get the activities which have an occasion in the given period but
        # no occasion in any future period
        o = session.query(Occasion)
        o = o.filter(Occasion.period_id == self.id)
        o = o.filter(not_(Occasion.activity_id.in_(f.subquery())))
        o = o.options(joinedload(Occasion.activity))

        # archive those
        for occasion in o:
            if occasion.activity.state == 'accepted':
                occasion.activity.archive()

        # also archive all activities without an occasion
        w = session.query(Occasion)
        w = w.with_entities(distinct(Occasion.activity_id))

        # XXX circular import
        from onegov.activity.models.activity import Activity

        a = session.query(Activity)
        a = a.filter(not_(Activity.id.in_(w.subquery())))
        a = a.filter(Activity.state == 'accepted')

        for activity in a:
            activity.archive()

    @property
    def booking_limit(self):
        """ Returns the max_bookings_per_attendee limit if it applies. """
        return self.all_inclusive and self.max_bookings_per_attendee

    def as_local_datetime(self, day):
        return sedate.standardize_date(
            datetime(day.year, day.month, day.day, 0, 0),
            self.timezone
        )

    @property
    def phase(self):
        local = self.as_local_datetime
        today = local(date.today())

        if not self.active or today < local(self.prebooking_start):
            return 'inactive'

        if not self.confirmed:
            return 'wishlist'

        if today < local(self.booking_start):
            return 'inactive'

        if not self.finalized and local(self.booking_end) < today:
            return 'inactive'

        if not self.finalized:
            return 'booking'

        if today < local(self.execution_start):
            return 'payment'

        if local(self.execution_start) <= today <= local(self.execution_end):
            return 'execution'

        if today > local(self.execution_end):
            return 'archive'

    def confirm_and_start_booking_phase(self):
        """ Confirms the period and sets the booking phase to now.

        This is mainly an internal convenience function to activate the
        previous behaviour before a specific booking phase date was introduced.

        """

        self.confirmed = True
        self.prebooking_end = date.today()
        self.booking_start = date.today()

    @property
    def wishlist_phase(self):
        return self.phase == 'wishlist'

    @property
    def booking_phase(self):
        return self.phase == 'booking'

    @property
    def payment_phase(self):
        return self.phase == 'payment'

    @property
    def execution_phase(self):
        return self.phase == 'execution'

    @property
    def archive_phase(self):
        return self.phase == 'archive'

    @property
    def is_prebooking_in_future(self):
        today = self.as_local_datetime(date.today())
        start = self.as_local_datetime(self.prebooking_start)

        return today < start

    @property
    def is_currently_prebooking(self):
        if not self.wishlist_phase:
            return False

        today = self.as_local_datetime(date.today())
        start = self.as_local_datetime(self.prebooking_start)
        end = self.as_local_datetime(self.prebooking_end)

        return start <= today <= end

    @property
    def is_prebooking_in_past(self):
        today = self.as_local_datetime(date.today())
        start = self.as_local_datetime(self.prebooking_start)
        end = self.as_local_datetime(self.prebooking_end)

        if today > end:
            return True

        return start <= today and not self.wishlist_phase

    @property
    def is_booking_in_future(self):
        today = self.as_local_datetime(date.today())
        start = self.as_local_datetime(self.booking_start)

        return today < start

    @property
    def is_currently_booking(self):
        if not self.booking_phase:
            return False

        today = self.as_local_datetime(date.today())
        start = self.as_local_datetime(self.booking_start)
        end = self.as_local_datetime(self.booking_end)

        return start <= today <= end

    @property
    def is_booking_in_past(self):
        today = self.as_local_datetime(date.today())
        start = self.as_local_datetime(self.booking_start)
        end = self.as_local_datetime(self.booking_end)

        if today > end:
            return True

        return start <= today and not self.booking_phase

    @property
    def is_execution_in_past(self):
        today = self.as_local_datetime(date.today())
        end = self.as_local_datetime(self.execution_end)

        return today > end

    @property
    def scoring(self):
        # circular import
        from onegov.activity.matching.score import Scoring

        return Scoring.from_settings(
            settings=self.data.get('match-settings', {}),
            session=object_session(self))

    @scoring.setter
    def scoring(self, scoring):
        self.data['match-settings'] = scoring.settings
