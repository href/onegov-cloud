from collections import namedtuple

from cached_property import cached_property

from onegov.core.elements import Link, Confirm, Intercooler
from onegov.fsi.collections.notification_template import \
    CourseNotificationTemplateCollection
from onegov.fsi.layout import DefaultLayout
from onegov.org.layout import DefaultMailLayout as OrgDefaultMailLayout
from onegov.fsi import _


class MailLayout(OrgDefaultMailLayout):

    """Layout for emails expecting the model to be a reservation object."""

    def __init__(self, *args, notification_type=None):
        super().__init__(*args)
        self.notification_type = notification_type

    @cached_property
    def title(self):
        return _('Preview Info Mail for ${course_event}', mapping=dict(
            course_event=self.model.course_event.name))

    @cached_property
    def edit_link(self):
        return self.request.link(self.model, name='edit')

    @cached_property
    def base(self):
        return self.template_loader['mail_layout.pt']

    @cached_property
    def course_start(self):
        return self.format_date(
            self.model.course_event.start, self.time_format)

    @cached_property
    def course_end(self):
        return self.format_date(self.model.course_event.end, self.time_format)

    @cached_property
    def course_date(self):
        return self.format_date(self.model.course_event.end, self.date_format)

    @cached_property
    def course_name(self):
        return self.model.course.name

    @cached_property
    def course_description(self):
        return self.model.course.description

    @cached_property
    def reservation_name(self):
        return str(self.model)

    @cached_property
    def course_event_url(self):
        return self.request.link(self.model.course_event)


class NotificationTemplateCollectionLayout(DefaultLayout):
    @cached_property
    def title(self):
        return _('Manage Notification Templates')

    @cached_property
    def breadcrumbs(self):
        links = super().breadcrumbs
        links.append(
            Link(self.model.course_event.name, self.request.link(
                self.model.course_event))
        )
        links.append(
            Link(_('Manage Notification Templates'),
                 self.request.link(self.model)),
        )
        return links

    def accordion_items(self):
        template = namedtuple('Template',
                              ['subject', 'text', 'url', 'edit_url'])
        return tuple(
            template(
                item.subject,
                item.text,
                self.request.link(item),
                self.request.link(item, name='edit')
            ) for item in self.model.query()
        )


class NotificationTemplateLayout(DefaultLayout):

    @cached_property
    def title(self):
        return _('${type} Notification Template', mapping=dict(
            type=self.format_notification_type(self.model.type)))

    @cached_property
    def collection(self):
        return CourseNotificationTemplateCollection(
            self.request.session,
            course_event_id=self.model.course_event_id
        )

    @cached_property
    def breadcrumbs(self):
        links = super().breadcrumbs
        links.append(Link(self.model.course_event.name,
                          self.request.link(self.model.course_event)))
        links.append(Link(_('Manage Notification Templates'),
                          self.request.link(self.collection)))
        links.append(Link(self.format_notification_type(self.model.type),
                          self.request.link(self.model)))
        return links

    @cached_property
    def editbar_links(self):
        return [
            Link(_('Edit'), self.request.link(self.model, name='edit'),
                 attrs={'class': 'edit-link'})
        ]


class EditNotificationTemplateLayout(NotificationTemplateLayout):
    @cached_property
    def title(self):
        return _('Edit ${type} Notification Template', mapping=dict(
            type=self.format_notification_type(self.model.type)))

    @cached_property
    def breadcrumbs(self):
        links = super().breadcrumbs
        links.append(
            Link(_('Edit'), self.request.link(self.model, name='edit')))
        return links


class SendNotificationTemplateLayout(NotificationTemplateLayout):
    @cached_property
    def title(self):
        return _('Mailing')

    @cached_property
    def breadcrumbs(self):
        breadcrumbs = super().breadcrumbs
        breadcrumbs.append(Link(_('Send')))
        return breadcrumbs
