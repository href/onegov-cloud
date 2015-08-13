import threading
import re
import weakref
import zope.sqlalchemy

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool


class SessionManager(object):
    """ Holds sessions and creates schemas before binding sessions to schemas.

    Threadsafe in theory, but not tested or well thought out. No global state
    though, so two different session managers will manage different
    sessions/schemas.

    """

    # describes the accepted characters in a schema name
    _valid_schema_name = re.compile(r'^[a-z0-9_-]+$')

    # describes the prefixes with which a schema may not begin
    _invalid_prefixes = re.compile(r'^([0-9]|pg_)+')

    # holds schemas that may never be used:
    # - information_schema is a sql standard schema that's for internal use
    # - public is the default schema name which should not be used for security
    #   reasons. Someone could figure out a way to set the search_path to
    #   default and to add an application that has the right to change the
    #   public schema.
    _reserved_schemas = {'information_schema', 'public', 'extensions'}

    def __init__(self, dsn, base, engine_config={}, session_config={}):
        """ Configures the data source name/dsn/database url and sets up the
        connection to the database.

        :dsn:
            Database connection string including user, password, host, port
            and database name.

            See: `<http://docs.sqlalchemy.org/en/latest/core/engines.html\
            #database-urls>`_

        :base:
            Declarative base used to define the SQLAlchemy database models.

            Extra bases may be added to the session manager after __init__::

                mgr.bases.append(MyBase)

            The tables in these additional schemas are created on the schema
            alongside the primary base.

        :engine_config:
            Additional configuration passed to SQLAlchemy's `create_engine`.

            See: `<http://docs.sqlalchemy.org/en/latest/core/engines.html\
            #sqlalchemy.create_engine>`

        :session_config:
            Additional configuration passed to SQLAlchemy's sessionmaker.

            See: `<http://docs.sqlalchemy.org/en/latest/orm/session_api.html\
            #sqlalchemy.orm.session.sessionmaker>`

        Note, to connect to another database you need to create a new
        SessionManager instance.

        **Postgres Extensions**

        The session manager supports the setup of postgres extensions.
        Currently those extensions are hard-coded and they are all added to the
        extensions schema. The extensions schema is then added to the search
        path of each query.

        Since extensions can only be created by superusers, this is something
        you might want to do in a separate step in deployment. We don't advise
        you to use a superuser connection for your onegov cloud deployment.

        You may therefore use the list of the required extensions below and
        create a schema 'extensions' with those extensions inside.

        """
        assert 'postgres' in dsn, "Onegov only supports Postgres!"

        self.dsn = dsn
        self.bases = [base]
        self.created_schemas = set()
        self.current_schema = None

        # onegov.core creates extensions that it requires in a separate schema

        # in the future, this might become something we can configure through
        # the setuptools entry_points -> modules could advertise what they need
        # and the core would install the extensions the modules require
        self.required_extensions = {'hstore'}
        self.created_extensions = set()

        self.engine = create_engine(
            self.dsn, poolclass=QueuePool, pool_size=5, max_overflow=5,
            isolation_level='SERIALIZABLE',
            **engine_config)
        self.register_engine(self.engine)

        self.session_factory = scoped_session(
            sessionmaker(bind=self.engine, **session_config),
            scopefunc=self._scopefunc
        )
        zope.sqlalchemy.register(self.session_factory)

    def register_engine(self, engine):
        """ Takes the given engine and registers it with the schema
        switching mechanism. Maybe used to register external engines with
        the session manager.

        If used like this, make sure to call :meth:`bind_session` before using
        the session provided by the external engine.

        """

        @event.listens_for(engine, "before_cursor_execute")
        def _activate_schema(
            conn, cursor, statement, parameters, context, executemany
        ):
            """ Share the 'info' dictionary of Session with Connection
            objects.

            """

            # execution options have priority!
            if 'schema' in conn._execution_options:
                schema = conn._execution_options['schema']
            else:
                if 'session' in conn.info:
                    schema = conn.info['session'].info['schema']
                else:
                    schema = None

            if schema is not None:
                cursor.execute("SET search_path TO %s, extensions", (schema, ))

    def _scopefunc(self):
        """ Returns the scope of the scoped_session used to create new
        sessions. Relies on self.current_schema being set before the
        session is created.

        This function is as internal as they come and it exists only because
        we otherwise would have to create different session factories for each
        schema.

        """
        return (threading.current_thread(), self.current_schema)

    def dispose(self):
        """ Closes the connection to the server and cleans up. This only needed
        for testing.

        """
        self.engine.raw_connection().invalidate()
        self.engine.dispose()

    def is_valid_schema(self, schema):
        """ Returns True if the given schema looks valid enough to be created
        on the database with no danger of SQL injection or other unwanted
        sideeffects.

        """
        if not schema:
            return False

        if schema in self._reserved_schemas:
            return False

        if self._invalid_prefixes.match(schema):
            return False

        # only one consecutive '-' is allowed (-- constitues a comment)
        if '--' in schema:
            return False

        return self._valid_schema_name.match(schema) and True or False

    def set_current_schema(self, schema):
        """ Sets the current schema in use. The current schema is then used
        to bind the session to a schema. Note that this can't be done
        in a functional way. We need the current schema to generate a new
        scope.

        I would very much prefer to bind this to the session but this is not
        at all straight-forward with SQLAlchemy.

        I tried a solution like `this one <https://bitbucket.org/zzzeek/\
        sqlalchemy/wiki/UsageRecipes/SessionModifiedSQL>`_, but it's not good
        enough, because it still relies on some kind of global stage, even if
        it's set locally.

        Ideally a value could be bound to the session and an event would
        trigger every time the connection is used with that session. We
        could then set the schema on the connection every time that happens.

        For now, the global option is okay though, because in practice we
        only set the schema once per request and we don't do threading
        anyway.

        """
        assert self.is_valid_schema(schema)

        self.current_schema = schema
        self.ensure_schema_exists(schema)

    def bind_session(self, session):
        """ Bind the session to the current schema. """
        session.info['schema'] = self.current_schema
        session.connection().info['session'] = weakref.proxy(session)

        return session

    def session(self):
        """ Returns a new session or an existing session. Sessions with
        different schemas are kept independent, though they might reuse
        each others connections.

        This means that a session retrieved thusly::

            mgr = SessionManager('postgres://...')
            mgr.set_current_schema('foo')
            session = mgr.session()

        Will not see objects attached to this session::

            mgr.set_current_schema('bar')
            session = mgr.session()

        """

        return self.bind_session(self.session_factory())

    def list_schemas(self, limit_to_namespace=None):
        """ Returns a list containing *all* schemas defined in the current
        database.

        """
        conn = self.engine.execution_options(schema=None)
        query = text("SELECT schema_name FROM information_schema.schemata")

        if limit_to_namespace is not None:
            return [
                r[0] for r in conn.execute(query).fetchall()
                if r[0].startswith(limit_to_namespace + '-')
            ]
        else:
            return [r[0] for r in conn.execute(query).fetchall()]

    def is_schema_found_on_database(self, schema):
        """ Returns True if the given schema exists on the database. """

        conn = self.engine.execution_options(schema=None)
        result = conn.execute(text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.schemata "
            "WHERE schema_name = :schema)"
        ), schema=schema)

        return result.first()[0]

    def create_required_extensions(self):
        """ Creates the required extensions once per lifetime of the manager.

        """
        if self.required_extensions != self.created_extensions:

            # extensions are a all added to a shared schema
            if not self.is_schema_found_on_database('extensions'):
                conn = self.engine.execution_options(schema=None)
                conn.execute('CREATE SCHEMA "extensions"')
                conn.execute('COMMIT')

            conn = self.engine.execution_options(schema='extensions')
            for ext in self.required_extensions - self.created_extensions:
                conn.execute(
                    'CREATE EXTENSION IF NOT EXISTS "{}" '
                    'SCHEMA "extensions"'.format(ext)
                )
                conn.execute('COMMIT')
                self.created_extensions.add(ext)

    def ensure_schema_exists(self, schema):
        """ Makes sure the schema exists on the database. If it doesn't, it
        is created.

        """
        assert self.engine is not None

        if schema not in self.created_schemas:

            # this is important because CREATE SCHEMA is done in a possibly
            # dangerous way!
            assert self.is_valid_schema(schema)

            # setup the extensions right before we activate our first schema
            self.create_required_extensions()

            # psycopg2 doesn't know how to correctly build a CREATE
            # SCHEMA statement, so we need to do it manually.
            # self.is_valid_schema should've checked that no sql
            # injections are possible.
            #
            # this is the *only* place where this happens - if anyone
            # knows how to do this using sqlalchemy/psycopg2, come forward!
            if not self.is_schema_found_on_database(schema):
                conn = self.engine.execution_options(schema=None)
                conn.execute('CREATE SCHEMA "{}"'.format(schema))
                conn.execute('COMMIT')

            conn = self.engine.execution_options(schema=schema)

            try:
                for base in self.bases:
                    base.metadata.schema = schema
                    base.metadata.create_all(conn)

                conn.execute('COMMIT')
            finally:
                # reset the schema on the global base variable - this state
                # sticks around otherwise and haunts us in the tests
                for base in self.bases:
                    base.metadata.schema = None

            self.created_schemas.add(schema)
