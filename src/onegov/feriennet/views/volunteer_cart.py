from onegov.core.security import Public
from onegov.feriennet import FeriennetApp
from onegov.feriennet.layout import DefaultLayout
from onegov.feriennet.models import VolunteerCart
from onegov.feriennet.models import VolunteerCartAction


# Public, even though this is personal data -> the storage is limited to the
# current browser session, which is separated from other users
@FeriennetApp.json(model=VolunteerCart, permission=Public)
def view_cart(self, request):
    return list(self.for_frontend(DefaultLayout(self, request)))


@FeriennetApp.view(
    model=VolunteerCartAction,
    permission=Public,
    request_method='POST')
def execute_cart_action(self, request):
    request.assert_valid_csrf_token()
    self.execute(request, VolunteerCart.from_request(request))
