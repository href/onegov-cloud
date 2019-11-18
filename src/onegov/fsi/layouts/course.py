from cached_property import cached_property

from onegov.core.elements import Link, Confirm, Intercooler
from onegov.fsi.collections.course import CourseCollection
from onegov.fsi.collections.course_event import CourseEventCollection
from onegov.fsi.layout import DefaultLayout
from onegov.fsi import _
from onegov.org.elements import LinkGroup


class CourseCollectionLayout(DefaultLayout):
    @cached_property
    def title(self):
        return _('Course management') if self.request.is_manager else _(
            'Courses')

    @cached_property
    def breadcrumbs(self):
        """ Returns the breadcrumbs for the current page. """
        links = super().breadcrumbs
        links.append(
            Link(
                self.title,
                self.request.class_link(CourseCollection)))
        return links

    @cached_property
    def editbar_links(self):
        links = []
        if self.request.is_manager:
            links.append(
                Link(
                    text=_("Add Course"),
                    url=self.request.class_link(
                        CourseCollection, name='add'
                    ),
                    attrs={'class': 'add-icon'}
                )
            )

        return links

    @property
    def accordion_items(self):
        return tuple(
            dict(
                title=c.name,
                content=c.description,
                url=self.request.link(c),
                edit_url=self.request.link(c, name='edit')
            ) for c in self.model.query()
        )


class CourseLayout(DefaultLayout):

    @cached_property
    def event_collection(self):
        return CourseEventCollection(
            self.request.session, course_id=self.model.id)

    @cached_property
    def breadcrumbs(self):
        """ Returns the breadcrumbs for the detail page. """
        links = super().breadcrumbs
        links.append(
            Link(self.model.name, self.request.link(self.model))
        )
        return links

    @cached_property
    def editbar_links(self):
        if not self.request.is_manager:
            return []
        return [
            LinkGroup(
                title=_('Add'),
                links=(
                    Link(
                        _('New Course'),
                        self.request.class_link(
                            CourseCollection, name='add'
                        ),
                        attrs={'class': 'new-link'}
                    ),
                    Link(
                        _('Event'),
                        self.request.link(self.event_collection, name='add'),
                        attrs={'class': 'new-link'}
                    )
                )
            ),
            Link(
                _('Edit'),
                self.request.link(self.model, name='edit'),
                attrs={'class': 'edit-link'}
            ),

            Link(
                _('Delete'),
                self.csrf_protected_url(
                    self.request.link(self.model)
                ),
                attrs={'class': 'delete-link'},
                traits=(
                    Confirm(
                        _("Do you really want to delete this course ?"),
                        _("This cannot be undone."),
                        _("Delete course event"),
                        _("Cancel")
                    ),
                    Intercooler(
                        request_method='DELETE',
                        redirect_after=self.request.class_link(
                            CourseCollection
                        )
                    )
                )
            ),
        ]


class AddCourseLayout(CourseCollectionLayout):
    @cached_property
    def title(self):
        return _('Add Course')


class EditCourseLayout(CourseLayout):
    @cached_property
    def title(self):
        return _('Edit Course')