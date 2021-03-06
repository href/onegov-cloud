from datetime import date
from onegov.ballot import Election
from onegov.election_day import _
from onegov.election_day.layouts import DefaultLayout
from onegov.form import Form
from onegov.form.fields import ChosenSelectMultipleField
from wtforms import BooleanField
from wtforms import RadioField
from wtforms import StringField
from wtforms.fields.html5 import DateField
from wtforms.fields.html5 import URLField
from wtforms.validators import InputRequired


class ElectionCompoundForm(Form):

    domain = RadioField(
        label=_("Type"),
        choices=[
            ('canton', _("Cantonal"))
        ],
        default='canton',
        validators=[
            InputRequired()
        ]
    )

    date = DateField(
        label=_("Date"),
        validators=[
            InputRequired()
        ],
        default=date.today
    )

    shortcode = StringField(
        label=_("Shortcode")
    )

    election_de = StringField(
        label=_("German"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'de'}
    )
    election_fr = StringField(
        label=_("French"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'fr'}
    )
    election_it = StringField(
        label=_("Italian"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'it'}
    )
    election_rm = StringField(
        label=_("Romansh"),
        fieldset=_("Title of the election"),
        render_kw={'lang': 'rm'}
    )

    elections = ChosenSelectMultipleField(
        label=_("Elections"),
        choices=[],
        validators=[
            InputRequired()
        ],
    )

    related_link = URLField(
        label=_("Link"),
        fieldset=_("Related link")
    )

    related_link_label_de = StringField(
        label=_("Link label german"),
        fieldset=_("Related link"),
        render_kw={'lang': 'de'}
    )
    related_link_label_fr = StringField(
        label=_("Link label french"),
        fieldset=_("Related link"),
        render_kw={'lang': 'fr'}
    )
    related_link_label_it = StringField(
        label=_("Link label italian"),
        fieldset=_("Related link"),
        render_kw={'lang': 'it'}
    )
    related_link_label_rm = StringField(
        label=_("Link label romansh"),
        fieldset=_("Related link"),
        render_kw={'lang': 'rm'}
    )

    show_party_strengths = BooleanField(
        label=_("Party strengths"),
        fieldset=_("Views"),
        render_kw=dict(force_simple=True)
    )

    show_mandate_allocation = BooleanField(
        label=_("Mandate allocation"),
        fieldset=_("Views"),
        render_kw=dict(force_simple=True)
    )

    def validate(self):
        result = super(ElectionCompoundForm, self).validate()

        if self.elections.data:
            query = self.request.session.query(Election.type.distinct())
            query = query.filter(Election.id.in_(self.elections.data))
            if query.count() > 1:
                self.elections.errors.append(
                    _("Select either majorz or proporz elections.")
                )
                result = False

        return result

    def on_request(self):
        self.election_de.validators = []
        self.election_fr.validators = []
        self.election_it.validators = []
        self.election_rm.validators = []

        default_locale = self.request.default_locale
        if default_locale.startswith('de'):
            self.election_de.validators.append(InputRequired())
        if default_locale.startswith('fr'):
            self.election_fr.validators.append(InputRequired())
        if default_locale.startswith('it'):
            self.election_de.validators.append(InputRequired())
        if default_locale.startswith('rm'):
            self.election_de.validators.append(InputRequired())

        layout = DefaultLayout(None, self.request)

        query = self.request.session.query(Election)
        query = query.order_by(Election.date.desc(), Election.shortcode)
        query = query.filter(Election.domain == 'region')
        self.elections.choices = [
            (
                item.id,
                '{} {} {} ({})'.format(
                    layout.format_date(item.date, 'date'),
                    item.shortcode or '',
                    item.title,
                    item.type
                ).replace("  ", " ")
            ) for item in query
        ]

    def update_model(self, model):
        model.domain = self.domain.data
        model.date = self.date.data
        model.shortcode = self.shortcode.data
        model.related_link = self.related_link.data
        model.show_party_strengths = self.show_party_strengths.data
        model.show_mandate_allocation = self.show_mandate_allocation.data

        elections = self.request.session.query(Election)
        elections = elections.filter(Election.id.in_(self.elections.data))
        model.elections = elections

        titles = {}
        if self.election_de.data:
            titles['de_CH'] = self.election_de.data
        if self.election_fr.data:
            titles['fr_CH'] = self.election_fr.data
        if self.election_it.data:
            titles['it_CH'] = self.election_it.data
        if self.election_rm.data:
            titles['rm_CH'] = self.election_rm.data
        model.title_translations = titles

        link_labels = {}
        if self.related_link_label_de.data:
            link_labels['de_CH'] = self.related_link_label_de.data
        if self.related_link_label_fr.data:
            link_labels['fr_CH'] = self.related_link_label_fr.data
        if self.related_link_label_it.data:
            link_labels['it_CH'] = self.related_link_label_it.data
        if self.related_link_label_rm.data:
            link_labels['rm_CH'] = self.related_link_label_rm.data
        model.related_link_label = link_labels

    def apply_model(self, model):
        titles = model.title_translations or {}
        self.election_de.data = titles.get('de_CH')
        self.election_fr.data = titles.get('fr_CH')
        self.election_it.data = titles.get('it_CH')
        self.election_rm.data = titles.get('rm_CH')

        link_labels = model.related_link_label or {}
        self.related_link_label_de.data = link_labels.get('de_CH', '')
        self.related_link_label_fr.data = link_labels.get('fr_CH', '')
        self.related_link_label_it.data = link_labels.get('it_CH', '')
        self.related_link_label_rm.data = link_labels.get('rm_CH', '')

        self.domain.data = model.domain
        self.date.data = model.date
        self.shortcode.data = model.shortcode
        self.related_link.data = model.related_link
        self.show_party_strengths.data = model.show_party_strengths
        self.show_mandate_allocation.data = model.show_mandate_allocation
        self.elections.data = [election.id for election in model.elections]
