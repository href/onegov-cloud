from onegov.fsi import FsiApp
from onegov.fsi.collections.course import CourseCollection
from onegov.fsi.collections.course_event import CourseEventCollection
from onegov.fsi.forms.course import CourseForm
from onegov.fsi import _
from onegov.fsi.layouts.course import CourseCollectionLayout, CourseLayout, \
    AddCourseLayout, EditCourseLayout

from onegov.fsi.models.course import Course


@FsiApp.html(
    model=CourseCollection,
    template='courses.pt')
def view_course_collection(self, request):
    layout = CourseCollectionLayout(self, request)
    layout.include_accordion()
    return {
        'layout': layout,
        'model': self,
    }


@FsiApp.form(
    model=CourseCollection,
    template='form.pt',
    name='add',
    form=CourseForm
)
def view_add_course_event(self, request, form):
    layout = AddCourseLayout(self, request)
    layout.include_editor()

    if form.submitted(request):
        course = self.add(**form.get_useful_data())
        request.success(_("Added a new course"))
        return request.redirect(request.link(course))

    return {
        'layout': layout,
        'model': self,
        'form': form
    }


@FsiApp.html(
    model=Course,
    template='course.pt')
def view_course_event(self, request):
    layout = CourseLayout(self, request)
    return {
        'layout': layout,
        'model': self,
    }


@FsiApp.form(
    model=Course,
    template='form.pt',
    name='edit',
    form=CourseForm
)
def view_edit_course_event(self, request, form):
    layout = EditCourseLayout(self, request)
    layout.include_editor()

    if form.submitted(request):
        form.update_model(self)

        request.success(_("Your changes were saved"))
        return request.redirect(request.link(self))

    if not form.errors:
        form.apply_model(self)

    return {
        'layout': layout,
        'model': self,
        'form': form
    }


@FsiApp.view(
    model=Course,
    request_method='DELETE',
)
def delete_course(self, request):
    request.assert_valid_csrf_token()
    if self.events.count() == 0:
        CourseEventCollection(request.session).delete(self)
    else:
        request.error(_('This course has events and can not be deleted'))
