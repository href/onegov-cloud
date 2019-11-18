from cached_property import cached_property

from onegov.core.elements import Link, Confirm, Intercooler, LinkGroup
from onegov.fsi.collections.reservation import ReservationCollection
from onegov.fsi.layout import DefaultLayout
from onegov.fsi import _


class ReservationCollectionLayout(DefaultLayout):

    @property
    def for_himself(self):
        return self.model.attendee_id == self.request.attendee_id

    @cached_property
    def title(self):
        if self.request.view_name == 'add':
            return _('Add Reservation')
        if self.request.view_name == 'add-placeholder':
            return _('Add Placeholder Reservation')
        if self.model.course_event_id:
            return _('Reservations for ${event}',
                     mapping={'event': self.model.course_event.name})
        if self.for_himself:
            return _('My Personal Reservations')
        elif self.model.attendee_id:
            return _('All Reservations for ${attendee}',
                     mapping={'attendee': self.model.attendee})
        return _('All Reservations')

    @cached_property
    def editbar_links(self):
        if not self.request.is_manager:
            return []
        return [
            LinkGroup(
                title=_('Add'),
                links=[
                    Link(
                        _('Reservation'),
                        self.request.link(self.model, name='add'),
                        attrs={'class': 'add-icon'}
                    ),
                    Link(
                        _('Placeholder'),
                        self.request.link(self.model, name='add-placeholder'),
                        attrs={'class': 'add-icon'}
                    )
                ]
            )

        ]

    @cached_property
    def course_event(self):
        return self.model.course_event

    @property
    def send_info_mail_url(self):
        return self.request.link(
            self.course_event.info_template, name='send')

    @cached_property
    def breadcrumbs(self):
        links = super().breadcrumbs
        if self.model.course_event_id:
            links.append(
                Link(
                    self.model.course_event.name,
                    self.request.link(self.model.course_event)
                )
            )
        links.append(
            Link(_('Manage Reservations'), self.request.link(self.model))
        )
        if self.request.view_name in ('add', 'add-placeholder'):
            links.append(Link(_('Add')))
        return links

    def intercooler_btn_for_item(self, reservation):
        return Link(
            text=_("Delete"),
            url=self.csrf_protected_url(
                self.request.link(reservation, name='delete')
            ),
            attrs={'class': 'button tiny alert'},
            traits=(
                Confirm(
                    _("Do you want to cancel the reservation ?"),
                    _("A confirmation email will be sent to you later."),
                    _("Cancel reservation for course event"),
                    _("Cancel")
                ),
                Intercooler(
                    request_method='DELETE',
                    redirect_after=self.request.link(self.model)
                )
            )
        )


class ReservationLayout(DefaultLayout):

    """ Only used for editing since it does not contain fields """

    @cached_property
    def collection(self):
        return ReservationCollection(
            self.request.session,
            attendee_id=None,
            course_event_id=self.model.course_event_id
        )

    @cached_property
    def breadcrumbs(self):
        links = super().breadcrumbs
        links.append(
            Link(
                self.model.course_event.name,
                self.request.link(self.model.course_event)
            )
        )
        links.append(
            Link(_('Manage Reservations'), self.request.link(self.collection))
        )
        links.append(Link(str(self.model)))
        return links