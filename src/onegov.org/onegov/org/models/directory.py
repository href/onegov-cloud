import sedate

from datetime import timedelta
from onegov.core.orm.mixins import meta_property, content_property
from onegov.core.utils import linkify
from onegov.directory import Directory, DirectoryEntry
from onegov.form import as_internal_id, Extendable, FormSubmission
from onegov.org.models.extensions import CoordinatesExtension
from onegov.org.models.extensions import HiddenFromPublicExtension
from sqlalchemy import and_
from sqlalchemy.orm import object_session


class ExtendedDirectory(Directory, HiddenFromPublicExtension, Extendable):
    __mapper_args__ = {'polymorphic_identity': 'extended'}

    es_type_name = 'extended_directories'

    enable_map = meta_property('enable_map')
    enable_submissions = meta_property('enable_submissions')

    guideline = content_property('guideline')
    price = content_property('price')
    price_per_submission = content_property('price_per_submission')
    currency = content_property('currency')

    payment_method = meta_property('payment_method')

    @property
    def form_class_for_submissions(self):
        return self.extend_form_class(self.form_class, self.extensions)

    @property
    def extensions(self):
        if self.enable_map:
            return ('coordinates', 'submitter')
        else:
            return ('submitter', )

    def remove_old_pending_submissions(self):
        session = object_session(self)
        horizon = sedate.utcnow() - timedelta(hours=24)

        submissions = session.query(FormSubmission).filter(and_(
            FormSubmission.state == 'pending',
            FormSubmission.meta['directory'] == self.id.hex,
            FormSubmission.last_change < horizon
        ))

        for submission in submissions:
            session.delete(submission)


class ExtendedDirectoryEntry(DirectoryEntry, CoordinatesExtension,
                             HiddenFromPublicExtension):
    __mapper_args__ = {'polymorphic_identity': 'extended'}

    es_type_name = 'extended_directory_entries'

    @property
    def display_config(self):
        return self.directory.configuration.display or {}

    @property
    def contact(self):
        contact_config = tuple(
            as_internal_id(name) for name in
            self.display_config.get('contact', tuple())
        )

        if contact_config:
            values = (self.values.get(name) for name in contact_config)
            value = '\n'.join(linkify(v) for v in values if v)

            return '<ul><li>{}</li></ul>'.format(
                '</li><li>'.join(linkify(value).splitlines())
            )

    @property
    def content_fields(self):
        content_config = {
            as_internal_id(k)
            for k in self.display_config.get('content', tuple())
        }

        if content_config:
            form = self.directory.form_class(data=self.values)

            return tuple(
                field for field in form._fields.values()
                if field.id in content_config and field.data
            )
