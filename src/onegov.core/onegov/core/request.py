from cached_property import cached_property
from more.webassets.core import IncludeRequest
from onegov.core import utils


class CoreRequest(IncludeRequest):
    """ Extends the default Morepath request with virtual host support and
    other useful methods.

    Virtual hosting might be supported by Morepath directly in the future:
    https://github.com/morepath/morepath/issues/185

    """

    def link_prefix(self):
        """ Override the `link_prefix` with the application base path provided
        by onegov.server, because the default link_prefix contains the
        hostname, which is not useful in our case - we'll add the hostname
        ourselves later.

        """
        return getattr(self.app, 'application_base_path', '')

    @cached_property
    def x_vhm_host(self):
        """ Return the X_VHM_HOST variable or an empty string.

        X_VHM_HOST acts like a prefix to all links generated by Morepath.
        If this variable is not empty, it will be added in front of all
        generated urls.
        """
        return self.headers.get('X_VHM_HOST', '').rstrip('/')

    @cached_property
    def x_vhm_root(self):
        """ Return the X_VHM_ROOT variable or an empty string.

        X_VHM_ROOT is a bit more tricky than X_VHM_HOST. It tells Morepath
        where the root of the application is situated. This means that the
        value of X_VHM_ROOT must be an existing path inside of Morepath.

        We can understand this best with an example. Let's say you have a
        Morepath application that serves a blog under /blog. You now want to
        serve the blog under a separate domain, say blog.example.org.

        If we just served Morepath under blog.example.org, we'd get urls like
        this one::

            blog.example.org/blog/posts/2014-11-17-16:00

        In effect, this subdomain would be no different from example.org
        (without the blog subdomain). However, we want the root of the host to
        point to /blog.

        To do this we set X_VHM_ROOT to /blog. Morepath will then automatically
        return urls like this::

            blog.example.org/posts/2014-11-17-16:00

        """
        return self.headers.get('X_VHM_ROOT', '').rstrip('/')

    def transform(self, url):
        """ Applies X_VHM_HOST and X_VHM_ROOT to the given url (which is
        expected to not contain a host yet!). """
        if self.x_vhm_root:
            url = '/' + utils.lchop(url, self.x_vhm_root).lstrip('/')

        if self.x_vhm_host:
            url = self.x_vhm_host + url

        return url

    def link(self, *args, **kwargs):
        """ Extends the default link generating function of Morepath. """
        return self.transform(
            super(CoreRequest, self).link(*args, **kwargs))

    def filestorage_link(self, path):
        """ Takes the given filestorage path and returns an url if the path
        exists. The url might point to the local server or it might point to
        somehwere else on the web.

        """

        app = self.app

        if not app.filestorage.exists(path):
            return None

        url = app.filestorage.getpathurl(path, allow_none=True)

        if url:
            return url
        else:
            return self.link(app.modules.filestorage.FilestorageFile(path))

    @cached_property
    def theme_link(self):
        """ Returns the link to the current theme. Computed once per request.

        The theme is automatically compiled and stored if it doesn't exist yet,
        or if it is outdated.

        """
        theme = self.app.registry.settings.core.theme
        assert theme is not None, "Do not call if no theme is used"

        filename = self.app.modules.theme.compile(
            self.app.themestorage, theme, self.app.theme_options,
            force=self.app.always_compile_theme
        )

        return self.link(self.app.modules.theme.ThemeFile(filename))

    def get_form(self, form_class):
        """ Returns an instance of the given form class, set up with the
        correct translator and with CSRF protection enabled (the latter
        doesn't work yet).

        """
        translate = self.get_translate(for_chameleon=False)
        form_class = self.app.modules.i18n.get_translation_bound_form(
            form_class, translate)

        return form_class(self.POST, meta={'locales': self.app.languages})

    def get_translate(self, for_chameleon=False):
        """ Returns the translate method to the given request, or None
        if no such method is availabe.

        :for_chameleon:
            True if the translate instance is used for chameleon (which is
            special).

        """
        if not self.app.languages:
            return None

        settings = self.app.registry.settings

        locale = settings.i18n.locale_negotiator(self.app.languages, self)
        locale = locale or settings.i18n.default_locale

        if for_chameleon:
            return self.app.chameleon_translations.get(locale)
        else:
            return self.app.translations.get(locale)
