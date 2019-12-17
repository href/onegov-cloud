from onegov.activity import VolunteerCollection
from onegov.core.security import Public
from onegov.feriennet import FeriennetApp, _
from onegov.feriennet.layout import DefaultLayout, VolunteerFormLayout
from onegov.feriennet.models import VolunteerCart
from onegov.feriennet.models import VolunteerCartAction
from onegov.feriennet.forms import VolunteerForm
from uuid import uuid4


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
        volunteers = VolunteerCollection(request.session)
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
