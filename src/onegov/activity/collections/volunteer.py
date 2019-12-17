from onegov.activity.models import Volunteer
from onegov.core.collection import GenericCollection


class VolunteerCollection(GenericCollection):

    @property
    def model_class(self):
        return Volunteer
