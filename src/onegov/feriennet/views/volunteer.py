from itertools import groupby
from onegov.activity import VolunteerCollection
from onegov.core.security import Public, Secret
from onegov.feriennet import FeriennetApp, _
from onegov.feriennet.forms import VolunteerForm
from onegov.feriennet.layout import DefaultLayout
from onegov.feriennet.layout import VolunteerFormLayout
from onegov.feriennet.layout import VolunteerLayout
from onegov.feriennet.models import VolunteerCart
from onegov.feriennet.models import VolunteerCartAction
from operator import attrgetter
from uuid import uuid4


@FeriennetApp.html(
    model=VolunteerCollection,
    template='volunteers.pt',
    permission=Secret)
def view_volunteers(self, request):

    def grouped(records, name):
        return tuple(
            tuple(g) for k, g in groupby(records, key=attrgetter(name)))

    return {
        'layout': VolunteerLayout(self, request),
        'title': _("Volunteers"),
        'records': self.report(),
        'grouped': grouped,
        'periods': request.app.periods,
        'period': self.period,
        'model': self,
    }


# Public, even though this is personal data -> the storage is limited to the
# current browser session, which is separated from other users
@FeriennetApp.json(model=VolunteerCart, permission=Public)
def view_cart(self, request):
    return list(self.for_frontend(DefaultLayout(self, request)))


@FeriennetApp.json(
    model=VolunteerCartAction,
    permission=Public,
    request_method='POST')
def execute_cart_action(self, request):

    # The CSRF check is disabled here, to make it easier to build the URL
    # in Javascript. This should be an exception, as this function here does
    # not provide a big attack surface, if any.
    #
    # request.assert_valid_csrf_token()

    return self.execute(request, VolunteerCart.from_request(request))


@FeriennetApp.form(
    model=VolunteerCart,
    permission=Public,
    form=VolunteerForm,
    template='volunteer_form.pt',
    name='submit')
def submit_volunteer(self, request, form):
    layout = VolunteerFormLayout(self, request)
    request.include('volunteer-cart')
    complete = False

    if form.submitted(request):
        volunteers = VolunteerCollection(request.session, period=None)
        cart = VolunteerCart.from_request(request)
        token = uuid4()

        for need_id in cart.ids():
            volunteers.add(
                token=token,
                need_id=need_id,
                **{
                    k: v for k, v in form.data.items() if k != 'csrf_token'
                })

        cart.clear()
        complete = True

    return {
        'layout': layout,
        'form': form,
        'title': _("Register as Volunteer"),
        'complete': complete,
        'cart_url': request.class_link(VolunteerCart),
        'cart_submit_url': request.class_link(VolunteerCart, name='submit'),
        'cart_action_url': request.class_link(VolunteerCartAction, {
            'action': 'action',
            'target': 'target',
        }),
    }
