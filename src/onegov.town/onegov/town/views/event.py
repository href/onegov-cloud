""" The onegov town collection of images uploaded to the site. """
import morepath

from datetime import date
from dateutil import rrule
from onegov.core.security import Private
from onegov.event import Event, EventCollection, OccurrenceCollection
from onegov.town import _
from onegov.town.app import TownApp
from onegov.town.elements import Link
from onegov.town.forms import EventForm
from onegov.town.layout import DefaultLayout, EventLayout
from sedate import replace_timezone, to_timezone


WEEKDAYS = (
    _("Monday"),
    _("Tuesday"),
    _("Wednesday"),
    _("Thursday"),
    _("Friday"),
    _("Saturday"),
    _("Sunday")
)


def humanize_recurrence(request, recurrence):
    """ Returns a human readable version of an RRULE generated by the form. """

    result = ''

    if recurrence:
        rule = rrule.rrulestr(recurrence)
        if rule._freq == rrule.MONTHLY:
            result = _(
                u"Monthly on the day ${day} of the month until ${end}",
                mapping={
                    'day': ', '.join((str(day) for day in rule._bymonthday)),
                    'end': rule._until.date().strftime('%d.%m.%Y')
                }
            )

        elif rule._freq == rrule.WEEKLY:
            result = _(
                u"Every ${days} until ${end}",
                mapping={
                    'days': ', '.join((
                        request.translate(WEEKDAYS[day])
                        for day in rule._byweekday
                    )),
                    'end': rule._until.date().strftime('%d.%m.%Y')
                }
            )

    return result


@TownApp.html(model=EventCollection, template='events.pt', permission=Private)
def view_events(self, request):
    """ Display all events in a list.

    This view is not actually used.
    """

    layout = DefaultLayout(self, request)
    layout.breadcrumbs = [
        Link(_("Homepage"), layout.homepage_url),
        Link(_("Events"), layout.events_url),
        Link(_("List"), '#')
    ]

    def get_filters():
        states = (
            ('submitted', _("Submitted")),
            ('published', _("Published")),
            ('withdrawn', _("Withdrawn"))
        )

        for id, text in states:
            yield Link(
                text=text,
                url=request.link(self.for_state(id)),
                active=self.state == id
            )

    if self.state == 'submitted':
        events_title = _("Submitted events")
    elif self.state == 'published':
        events_title = _("Published events")
    elif self.state == 'withdrawn':
        events_title = _("Withdrawn events")
    else:
        raise NotImplementedError

    return {
        'title': _("Events"),
        'layout': layout,
        'events': self.batch,
        'filters': tuple(get_filters()),
        'events_title': events_title,
    }


@TownApp.view(model=Event, name='publish', permission=Private)
def publish_event(self, request):
    """ Publish an event. """

    self.publish()

    request.success(_(u"You have published the event ${title}", mapping={
        'title': self.title
    }))

    return morepath.redirect(request.link(self))


@TownApp.view(model=Event, name='withdraw', permission=Private)
def withdraw_event(self, request):
    """ Withdraw an event. """

    self.withdraw()

    request.success(_(u"You have withdrawn the event ${title}", mapping={
        'title': self.title
    }))

    return morepath.redirect(request.link(self))


@TownApp.html(model=Event, template='event.pt', permission=Private)
def view_event(self, request):
    """ View an event. """

    description = self.description.replace('\n', '<br>')
    recurrence = humanize_recurrence(request, self.recurrence)
    occurrences = self.occurrence_dates(localize=True)
    state = ''
    if self.state == 'submitted':
        state = _("Submitted")
    if self.state == 'published':
        state = _("Published")
    if self.state == 'withdrawn':
        state = _("Withdrawn")

    return {
        'title': self.title,
        'layout': EventLayout(self, request),
        'event': self,
        'state': state,
        'description': description,
        'occurrences': occurrences,
        'recurrence': recurrence
    }


@TownApp.form(model=OccurrenceCollection, name='neu', template='form.pt',
              form=EventForm)
def handle_new_event(self, request, form):
    """ Add event form. """
    if request.is_logged_in:
        self.title = _("Add an event")
    else:
        self.title = _("Submit an event")

    if form.submitted(request):
        model = Event()
        form.update_model(model)

        event = EventCollection(self.session).add(
            title=model.title,
            start=model.start,
            end=model.end,
            timezone=model.timezone,
            recurrence=model.recurrence,
            tags=model.tags,
            location=model.location,
            content=model.content,
        )
        # todo: add a preview before submitting?
        event.submit()

        # todo: create ticket and link the new event
        if request.is_logged_in:
            request.success(_("Event added"))
            return morepath.redirect(request.link(event))
        else:
            # More like "Vielen Dank für Ihre Eingabe!" and thank you page etc.
            # like in ticket system/form submission
            request.success(_("Event submitted"))
            return morepath.redirect(request.link(self))

    layout = EventLayout(self, request)
    layout.editbar_links = []

    return {
        'layout': layout,
        'title': self.title,
        'form': form,
        'form_width': 'large'
    }


@TownApp.form(model=Event, name='bearbeiten', template='form.pt',
              permission=Private, form=EventForm)
def handle_edit_event(self, request, form):
    """ Edit an event. """

    if form.submitted(request):
        form.update_model(self)

        request.success(_(u"Your changes were saved"))
        return morepath.redirect(request.link(self))

    form.apply_model(self)

    layout = EventLayout(self, request)
    layout.breadcrumbs.append(Link(_("Edit"), '#'))
    layout.editbar_links = []

    return {
        'layout': layout,
        'title': self.title,
        'form': form,
        'form_width': 'large'
    }


@TownApp.view(model=Event, request_method='DELETE', permission=Private)
def handle_delete_event(self, request):
    """ Delete an event. """

    EventCollection(request.app.session()).delete(self)
