from morepath.request import Response
from onegov.ballot import Ballot, Vote
from onegov.core.csv import convert_list_of_dicts_to_csv
from onegov.core.csv import convert_list_of_dicts_to_xlsx
from onegov.core.security import Public
from onegov.core.utils import normalize_for_url
from onegov.election_day import ElectionDayApp
from onegov.election_day.layout import DefaultLayout


@ElectionDayApp.html(model=Vote, template='vote.pt', permission=Public)
def view_vote(self, request):

    layout = DefaultLayout(self, request)
    request.include('ballot_map')

    @request.after
    def add_last_modified(response):
        if self.last_result_change:
            response.headers.add(
                'Last-Modified',
                self.last_result_change.strftime("%a, %d %b %Y %H:%M:%S GMT")
            )

    return {
        'vote': self,
        'layout': layout,
        'counted': self.counted
    }


@ElectionDayApp.json(model=Vote, name='json', permission=Public)
def view_vote_as_json(self, request):

    @request.after
    def add_last_modified(response):
        if self.last_result_change:
            response.headers.add(
                'Last-Modified',
                self.last_result_change.strftime("%a, %d %b %Y %H:%M:%S GMT")
            )

    return self.export()


@ElectionDayApp.view(model=Vote, name='csv', permission=Public)
def view_vote_as_csv(self, request):

    @request.after
    def add_last_modified(response):
        if self.last_result_change:
            response.headers.add(
                'Last-Modified',
                self.last_result_change.strftime("%a, %d %b %Y %H:%M:%S GMT")
            )

    return convert_list_of_dicts_to_csv(self.export())


@ElectionDayApp.view(model=Vote, name='xlsx', permission=Public)
def view_vote_as_xlsx(self, request):

    @request.after
    def add_last_modified(response):
        if self.last_result_change:
            response.headers.add(
                'Last-Modified',
                self.last_result_change.strftime("%a, %d %b %Y %H:%M:%S GMT")
            )

    return Response(
        convert_list_of_dicts_to_xlsx(self.export()),
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ),
        content_disposition='inline; filename={}.xlsx'.format(
            normalize_for_url(self.title)
        )
    )


@ElectionDayApp.json(model=Ballot, permission=Public, name='by-municipality')
def view_ballot_by_municipality(self, request):
    return self.percentage_by_municipality()
