from onegov.election_day import _
from onegov.form import Form
from onegov.form.fields import UploadField
from onegov.form.validators import WhitelistedMimeType, FileSizeLimit
from wtforms import BooleanField, IntegerField, RadioField
from wtforms.validators import (
    DataRequired, InputRequired, NumberRange, Optional
)


ALLOWED_MIME_TYPES = {
    'application/excel',
    'application/vnd.ms-excel',
    'text/plain',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

MAX_FILE_SIZE = 10 * 1024 * 1024


class UploadElectionForm(Form):

    file_format = RadioField(
        _("File format"),
        choices=[
            ('sesam', _("SESAM")),
            ('wabsti', _("Wabsti")),
            ('internal', _("OneGov Cloud")),
        ],
        validators=[
            InputRequired()
        ],
        default='sesam'
    )

    results = UploadField(
        label=_("Results"),
        validators=[
            DataRequired(),
            WhitelistedMimeType(ALLOWED_MIME_TYPES),
            FileSizeLimit(MAX_FILE_SIZE)
        ],
        render_kw=dict(force_simple=True)
    )

    connections = UploadField(
        label=_("List connections"),
        validators=[
            WhitelistedMimeType(ALLOWED_MIME_TYPES),
            FileSizeLimit(MAX_FILE_SIZE)
        ],
        depends_on=('file_format', 'wabsti'),
        render_kw=dict(force_simple=True)
    )

    elected = UploadField(
        label=_("Elected Candidates"),
        validators=[
            WhitelistedMimeType(ALLOWED_MIME_TYPES),
            FileSizeLimit(MAX_FILE_SIZE)
        ],
        depends_on=('file_format', 'wabsti'),
        render_kw=dict(force_simple=True)
    )

    statistics = UploadField(
        label=_("Election statistics"),
        validators=[
            WhitelistedMimeType(ALLOWED_MIME_TYPES),
            FileSizeLimit(MAX_FILE_SIZE)
        ],
        depends_on=('file_format', 'wabsti'),
        render_kw=dict(force_simple=True)
    )

    complete = BooleanField(
        label=_("Complete"),
        depends_on=('file_format', 'wabsti'),
        render_kw=dict(force_simple=True)
    )

    majority = IntegerField(
        label=_("Absolute majority"),
        depends_on=('file_format', '!internal'),
        validators=[
            Optional(),
            NumberRange(min=1)
        ]
    )

    def apply_model(self, model):
        if model.type == 'majorz':
            self.connections.render_kw['data-depends-on'] = 'file_format/none'
            self.statistics.render_kw['data-depends-on'] = 'file_format/none'
        else:
            self.connections.render_kw['data-depends-on'] = \
                'file_format/wabsti'
            self.statistics.render_kw['data-depends-on'] = 'file_format/wabsti'
            self.majority.render_kw = {'data-depends-on': 'file_format/none'}


class UploadVoteForm(Form):

    file_format = RadioField(
        _("File format"),
        choices=[
            ('default', _("Default")),
            ('internal', _("OneGov Cloud")),
        ],
        validators=[
            InputRequired()
        ],
        default='default'
    )

    type = RadioField(
        _("Type"),
        choices=[
            ('simple', _("Simple Vote")),
            ('complex', _("Vote with Counter-Proposal")),
        ],
        validators=[
            InputRequired()
        ],
        depends_on=('file_format', '!internal'),
        default='simple'
    )

    proposal = UploadField(
        label=_("Proposal"),
        validators=[
            DataRequired(),
            WhitelistedMimeType(ALLOWED_MIME_TYPES),
            FileSizeLimit(MAX_FILE_SIZE)
        ],
        render_kw={'force_simple': True}
    )

    counter_proposal = UploadField(
        label=_("Counter-Proposal"),
        validators=[
            DataRequired(),
            WhitelistedMimeType(ALLOWED_MIME_TYPES),
            FileSizeLimit(MAX_FILE_SIZE)
        ],
        depends_on=('file_format', 'default', 'type', 'complex'),
        render_kw=dict(force_simple=True)
    )

    tie_breaker = UploadField(
        label=_("Tie-Breaker"),
        validators=[
            DataRequired(),
            WhitelistedMimeType(ALLOWED_MIME_TYPES),
            FileSizeLimit(MAX_FILE_SIZE)
        ],
        depends_on=('file_format', 'default', 'type', 'complex'),
        render_kw=dict(force_simple=True)
    )
