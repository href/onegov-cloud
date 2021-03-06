from onegov.core.security import Private
from onegov.org import OrgApp
from onegov.org.models import PersonMove


@OrgApp.view(model=PersonMove, permission=Private, request_method='PUT')
def move_page(self, request):
    request.assert_valid_csrf_token()
    self.execute()
