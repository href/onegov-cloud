from onegov.core.utils import module_path
from onegov.org.theme import OrgTheme


# options editable by the user
user_options = {
    'primary-color': '#e33521',
}


class WinterthurTheme(OrgTheme):
    name = 'onegov.winterthur.foundation'

    @property
    def post_imports(self):
        return super().post_imports + [
            'winterthur'
        ]

    @property
    def extra_search_paths(self):
        base_paths = super().extra_search_paths
        return [module_path('onegov.winterthur.theme', 'styles')] + base_paths

    @property
    def pre_imports(self):
        return super().pre_imports + [
            'font-newsgot',
            'winterthur-foundation-mods'
        ]
