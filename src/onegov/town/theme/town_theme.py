from onegov.core.utils import module_path
from onegov.org.theme import OrgTheme


# options editable by the user
user_options = {
    'primary-color': '#006fba',
}


class TownTheme(OrgTheme):
    name = 'onegov.town.foundation'

    @property
    def post_imports(self):
        return super().post_imports + [
            'town'
        ]

    @property
    def extra_search_paths(self):
        base_paths = super().extra_search_paths
        return [module_path('onegov.town.theme', 'styles')] + base_paths
