from onegov.activity.models import Activity
from onegov.core.collection import Pagination
from onegov.core.utils import get_unique_hstore_keys
from onegov.core.utils import increment_name
from onegov.core.utils import normalize_for_url
from sqlalchemy.dialects.postgresql import array


class ActivityCollection(Pagination):

    def __init__(self, session, type='*', page=0, tags=None):
        self.session = session
        self.type = type
        self.page = page
        self.tags = set(tags) if tags else set()

    def __eq__(self, other):
        self.type == type and self.page == other.page

    def subset(self):
        return self.query()

    @property
    def page_index(self):
        return self.page

    def page_by_index(self, index):
        return self.__class__(self.session, self.type, index)

    @property
    def model_class(self):
        return Activity.get_polymorphic_class(self.type, Activity)

    def query(self):
        model_class = self.model_class
        query = self.session.query(model_class)

        if self.type != '*':
            query = query.filter(model_class.type == self.type)

        if self.tags:
            query = query.filter(model_class._tags.has_any(array(self.tags)))

        return query

    def for_filter(self, tag):
        """ Returns a new collection instance.

        The given tag is excluded if already in the list, included if not
        yet in the list.

        """

        if tag in self.tags:
            tags = self.tags - {tag}
        else:
            tags = self.tags | {tag}

        return self.__class__(self.session, self.type, 0, tags)

    def without_tag(self, tag):
        """ Returns a new collection instance excluding the given tag.

        The page is reset to 0.

        """

        return self.__class__(
            self.session, 0, [t for t in self.tags if t != tag])

    def by_id(self, id):
        return self.query().filter(Activity.id == id).first()

    def by_name(self, name):
        return self.query().filter(Activity.name == name).first()

    def by_user(self, user):
        return self.query().filter(Activity.username == user.username)

    def by_username(self, username):
        return self.query().filter(Activity.username == username)

    @property
    def used_tags(self):
        """ Returns a list of all the tags used on *all* activites of
        the current type.

        """

        return get_unique_hstore_keys(self.session, self.model_class._tags)

    def get_unique_name(self, name):
        """ Given a desired name, finds a variant of that name that's not
        yet used. So if 'foobar' is already used, 'foobar-1' will be returned.

        """
        name = normalize_for_url(name)

        existing = Activity.name.like('{}%'.format(name))
        existing = self.query().filter(existing)
        existing = existing.with_entities(Activity.name)
        existing = set(r[0] for r in existing.all())

        while name in existing:
            name = increment_name(name)

        return name

    def add(self, title, username, lead=None, text=None, tags=None, name=None):

        type = self.type != '*' and self.type or None

        name = name or self.get_unique_name(title)

        activity = self.model_class(
            name=name,
            title=title,
            tags=tags,
            type=type,
            username=username,
            lead=lead,
            text=text
        )

        self.session.add(activity)
        self.session.flush()

        return activity

    def delete(self, activity):
        self.session.delete(activity)
        self.sesison.flush()
