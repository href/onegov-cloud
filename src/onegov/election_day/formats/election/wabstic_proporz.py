from onegov.ballot import Candidate
from onegov.ballot import CandidateResult
from onegov.ballot import ElectionResult
from onegov.ballot import List
from onegov.ballot import ListConnection
from onegov.ballot import ListResult
from onegov.election_day import _
from onegov.election_day.formats.common import EXPATS, line_is_relevant, \
    validate_integer
from onegov.election_day.formats.common import FileImportError
from onegov.election_day.formats.common import load_csv
from sqlalchemy.orm import object_session
from uuid import uuid4

from onegov.election_day.import_export.mappings import \
    WABSTIC_PROPORZ_HEADERS_WP_WAHL, \
    WABSTIC_PROPORZ_HEADERS_WPSTATIC_GEMEINDEN, \
    WABSTIC_PROPORZ_HEADERS_WP_GEMEINDEN, WABSTIC_PROPORZ_HEADERS_WP_LISTEN, \
    WABSTIC_PROPORZ_HEADERS_WP_LISTENGDE, \
    WABSTIC_PROPORZ_HEADERS_WPSTATIC_KANDIDATEN, \
    WABSTIC_PROPORZ_HEADERS_WP_KANDIDATEN, \
    WABSTIC_PROPORZ_HEADERS_WP_KANDIDATENGDE


def get_entity_id(line, expats):
    col = 'bfsnrgemeinde'
    entity_id = validate_integer(line, col)
    return 0 if entity_id in expats else entity_id


def get_list_id_from_knr(line):
    """
    Takes a line from csv file with a candidate number (knr) in it and
    returns the derived listnr for this candidate. Will also handle the new
    WabstiC Standard 2018.
    """
    if '.' in line.knr:
        return line.knr.split('.')[0]
    return line.knr[0:-2]


def get_list_id(line):
    number = line.listnr or '0'
    # wabstiC 99 is blank list that maps to 999 see open_data_de.md
    number = '999' if number == '99' else number
    return number


def import_election_wabstic_proporz(
    election=None, principal=None, number=None, district=None,
    file_wp_wahl=None, mimetype_wp_wahl=None,
    file_wpstatic_gemeinden=None,
    mimetype_wpstatic_gemeinden=None,
    file_wp_gemeinden=None, mimetype_wp_gemeinden=None,
    file_wp_listen=None, mimetype_wp_listen=None,
    file_wp_listengde=None, mimetype_wp_listengde=None,
    file_wpstatic_kandidaten=None, mimetype_wpstatic_kandidaten=None,
    file_wp_kandidaten=None, mimetype_wp_kandidaten=None,
    file_wp_kandidatengde=None, mimetype_wp_kandidatengde=None
):
    """ Tries to import the given CSV files from a WabstiCExport.

    This function is typically called automatically every few minutes during
    an election day - we use bulk inserts to speed up the import.

    :return:
        A list containing errors.

    """

    errors = []
    entities = principal.entities[election.date.year]
    election_id = election.id

    # Read the files
    wp_wahl, error = load_csv(
        file_wp_wahl, mimetype_wp_wahl,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WP_WAHL,
        filename='wp_wahl'
    )
    if error:
        errors.append(error)

    wpstatic_gemeinden, error = load_csv(
        file_wpstatic_gemeinden, mimetype_wpstatic_gemeinden,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WPSTATIC_GEMEINDEN,
        filename='wpstatic_gemeinden'
    )
    if error:
        errors.append(error)

    wp_gemeinden, error = load_csv(
        file_wp_gemeinden, mimetype_wp_gemeinden,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WP_GEMEINDEN,
        filename='wp_gemeinden'
    )
    if error:
        errors.append(error)

    wp_listen, error = load_csv(
        file_wp_listen, mimetype_wp_listen,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WP_LISTEN,
        filename='wp_listen'
    )
    if error:
        errors.append(error)

    wp_listengde, error = load_csv(
        file_wp_listengde, mimetype_wp_listengde,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WP_LISTENGDE,
        filename='wp_listengde'
    )
    if error:
        errors.append(error)

    wpstatic_kandidaten, error = load_csv(
        file_wpstatic_kandidaten, mimetype_wpstatic_kandidaten,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WPSTATIC_KANDIDATEN,
        filename='wpstatic_kandidaten'
    )
    if error:
        errors.append(error)

    wp_kandidaten, error = load_csv(
        file_wp_kandidaten, mimetype_wp_kandidaten,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WP_KANDIDATEN,
        filename='wp_kandidaten'
    )
    if error:
        errors.append(error)

    wp_kandidatengde, error = load_csv(
        file_wp_kandidatengde, mimetype_wp_kandidatengde,
        expected_headers=WABSTIC_PROPORZ_HEADERS_WP_KANDIDATENGDE,
        filename='wp_kandidatengde'
    )
    if error:
        errors.append(error)

    if errors:
        return errors

    # Parse the election

    remaining_entities = None

    for line in wp_wahl.lines:
        line_errors = []

        if not line_is_relevant(line, number):
            continue
        try:
            remaining_entities = validate_integer(
                line, 'anzpendentgde', default=None)
        except Exception as e:
            line_errors.append(
                _("Error in anzpendentgde: ${msg}",
                  mapping={'msg': e.args[0]}))

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber, filename='wp_wahl'
                )
                for err in line_errors
            )
            continue

    # Parse the entities
    added_entities = {}

    for line in wpstatic_gemeinden.lines:
        line_errors = []

        if not line_is_relevant(line, number, district=district):
            continue

        # Parse the id of the entity
        try:
            entity_id = get_entity_id(line, EXPATS)
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            if entity_id and entity_id not in entities:
                line_errors.append(
                    _("${name} is unknown", mapping={'name': entity_id}))

            if entity_id in added_entities:
                line_errors.append(
                    _("${name} was found twice", mapping={'name': entity_id}))

        # Parse the eligible voters
        try:
            eligible_voters = validate_integer(line, 'stimmberechtigte')
        except ValueError as e:
            line_errors.append(e.args[0])

        # Skip expats if not enabled
        if entity_id == 0 and not election.expats:
            continue

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber,
                    filename='wpstatic_gemeinden'
                )
                for err in line_errors
            )
            continue

        entity = entities.get(entity_id, {})
        added_entities[entity_id] = {
            'name': entity.get('name', ''),
            'district': entity.get('district', ''),
            'eligible_voters': eligible_voters
        }

    for line in wp_gemeinden.lines:
        line_errors = []

        # Parse the id of the entity
        try:
            entity_id = get_entity_id(line, EXPATS)
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            if entity_id and entity_id not in entities:
                line_errors.append(
                    _("${name} is unknown", mapping={'name': entity_id}))

            if entity_id not in added_entities:
                # Only add it if present (there is there no SortGeschaeft)
                # .. this also skips expats if not enabled
                continue

        entity = added_entities[entity_id]

        # Check if the entity is counted
        try:
            # From wabstic export docs: Einheit ist grün-gesperrt
            # (1442=14:42 Uhr von der Oberbehörde gesperrt), sonst leer
            locking_time = validate_integer(line, 'sperrung', default=False)
            entity['counted'] = False if not locking_time else True
        except ValueError as e:
            line_errors.append(e.args[0])

        # Parse the eligible voters
        try:
            eligible_voters = validate_integer(line, 'stimmberechtigte')
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            eligible_voters = (
                eligible_voters
                or added_entities.get(entity_id, {}).get('eligible_voters', 0)
            )
            entity['eligible_voters'] = eligible_voters

        # Parse the ballots and votes
        try:
            received_ballots = validate_integer(line, 'stmabgegeben')
            blank_ballots = validate_integer(line, 'stmleer')
            invalid_ballots = validate_integer(line, 'stmungueltig')
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            entity['received_ballots'] = received_ballots
            entity['blank_ballots'] = blank_ballots
            entity['invalid_ballots'] = invalid_ballots
            entity['blank_votes'] = 0  # they are in the list results

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber, filename='wp_gemeinden'
                )
                for err in line_errors
            )
            continue

    # Parse the lists
    added_lists = {}
    added_connections = {}
    for line in wp_listen.lines:
        line_errors = []

        if not line_is_relevant(line, number):
            continue

        try:
            list_id = get_list_id(line)
            name = line.listcode
            number_of_mandates = validate_integer(line, 'sitze')
            connection = line.listverb or None
            subconnection = line.listuntverb or None
            if subconnection:
                assert connection, _('${var} is missing.',
                                     mapping={'var': 'connection'})
        except (ValueError, AssertionError) as e:
            line_errors.append(e.args[0])
        else:
            if list_id in added_lists:
                line_errors.append(
                    _("${name} was found twice", mapping={'name': list_id}))

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber, filename='wp_listen')
                for err in line_errors
            )
            continue

        connection_id = None
        if connection:
            parent_id = None
            if subconnection:
                parent_id = added_connections.setdefault(
                    (connection, None),
                    dict(
                        id=uuid4(),
                        election_id=election_id,
                        connection_id=connection
                    )
                )['id']

            connection_id = added_connections.setdefault(
                (connection, subconnection),
                dict(
                    id=uuid4(),
                    election_id=election_id,
                    parent_id=parent_id,
                    connection_id=subconnection or connection,
                )
            )['id']

        added_lists[list_id] = dict(
            id=uuid4(),
            election_id=election_id,
            list_id=list_id,
            name=name,
            number_of_mandates=number_of_mandates,
            connection_id=connection_id
        )

    # Parse the list results

    added_list_results = {}
    for line in wp_listengde.lines:

        line_errors = []

        try:
            entity_id = get_entity_id(line, EXPATS)
            list_id = get_list_id(line)
            votes = validate_integer(line, 'stimmentotal')
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            if entity_id not in added_entities:
                # Only add the list result if the entity is present (there is
                # no SortGeschaeft in this file)
                # .. this also skips expats if not enabled
                continue

            if entity_id not in added_entities:
                line_errors.append(
                    _("Entity with id ${id} not in added_entities",
                      mapping={'id': entity_id}))

            if list_id in added_list_results.get(entity_id, {}):
                line_errors.append(
                    _(
                        "${name} was found twice",
                        mapping={
                            'name': '{}/{}'.format(entity_id, list_id)
                        }
                    )
                )

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber, filename='wp_listengde')
                for err in line_errors
            )
            continue

        if list_id == '999':
            added_entities[entity_id]['blank_votes'] = votes

        if entity_id not in added_list_results:
            added_list_results[entity_id] = {}
        added_list_results[entity_id][list_id] = votes

    # Parse the candidates

    added_candidates = {}
    for line in wpstatic_kandidaten.lines:
        line_errors = []

        if not line_is_relevant(line, number):
            continue

        try:
            candidate_id = line.knr
            list_id = get_list_id_from_knr(line)
            family_name = line.nachname
            first_name = line.vorname
        except TypeError:
            line_errors.append(_("Invalid candidate values"))
        else:
            if candidate_id in added_candidates:
                line_errors.append(
                    _("${name} was found twice",
                      mapping={'name': candidate_id}))

            if list_id not in added_lists:
                line_errors.append(
                    _("List_id ${list_id} has not been found in list numbers",
                        mapping={
                            'list_id': list_id
                        })
                )

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber,
                    filename='wpstatic_kandidaten'
                )
                for err in line_errors
            )
            continue

        added_candidates[candidate_id] = dict(
            id=uuid4(),
            election_id=election_id,
            candidate_id=candidate_id,
            family_name=family_name,
            first_name=first_name,
            list_id=added_lists[list_id]['id']
        )

    for line in wp_kandidaten.lines:
        line_errors = []

        if not line_is_relevant(line, number):
            continue

        try:
            candidate_id = line.knr
            gewaehlt = validate_integer(line, 'gewaehlt')
            elected = True if gewaehlt == 1 else False
        except ValueError as e:
            line_errors.append(e.args[0])

        else:
            if candidate_id not in added_candidates:
                line_errors.append(
                    _("Candidate with id ${id} not in wpstatic_kandidaten",
                      mapping={'id': candidate_id}))
            added_candidates[candidate_id]['elected'] = elected

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber,
                    filename='wp_kandidaten'
                )
                for err in line_errors
            )
            continue

    added_results = {}
    for line in wp_kandidatengde.lines:
        line_errors = []

        try:
            entity_id = get_entity_id(line, EXPATS)
            candidate_id = line.knr
            votes = validate_integer(line, 'stimmen')
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            if (
                entity_id not in added_entities
                or candidate_id not in added_candidates
            ):
                # Only add the candidate result if the entity and the candidate
                # are present (there is no SortGeschaeft in this file)
                # .. this also skips expats if not enabled
                continue

            if candidate_id in added_results.get(entity_id, {}):
                line_errors.append(
                    _(
                        "${name} was found twice",
                        mapping={
                            'name': '{}/{}'.format(entity_id, candidate_id)
                        }
                    )
                )

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber,
                    filename='wp_kandidatengde'
                )
                for err in line_errors
            )
            continue

        if entity_id not in added_results:
            added_results[entity_id] = {}
        added_results[entity_id][candidate_id] = votes

    # Check if all results are from the same district if regional election
    districts = set([result['district'] for result in added_entities.values()])
    if election.domain == 'region' and districts and election.distinct:
        if principal.has_districts:
            if len(districts) != 1:
                # FIXME: Distinguish between the two errors
                errors.append(FileImportError(_("No clear district")))
        else:
            if len(added_results) != 1:
                errors.append(FileImportError(_("No clear district")))

    if errors:
        return errors

    # Add the results to the DB
    election.clear_results()
    election.status = 'unknown'
    if remaining_entities == 0:
        election.status = 'final'

    result_uids = {entity_id: uuid4() for entity_id in added_results}

    session = object_session(election)
    session.bulk_insert_mappings(
        ListConnection,
        (
            added_connections[key]
            for key in sorted(added_connections, key=lambda x: x[1] or '')
        )
    )
    session.bulk_insert_mappings(
        List,
        (
            added_lists[key]
            for key in filter(lambda x: x != '999', added_lists)
        )
    )
    session.bulk_insert_mappings(Candidate, added_candidates.values())
    session.bulk_insert_mappings(
        ElectionResult,
        (
            dict(
                id=result_uids[entity_id],
                election_id=election_id,
                name=added_entities[entity_id]['name'],
                district=added_entities[entity_id]['district'],
                entity_id=entity_id,
                counted=added_entities[entity_id]['counted'],
                eligible_voters=added_entities[entity_id]['eligible_voters'],
                received_ballots=added_entities[entity_id]['received_ballots'],
                blank_ballots=added_entities[entity_id]['blank_ballots'],
                invalid_ballots=added_entities[entity_id]['invalid_ballots'],
                blank_votes=added_entities[entity_id]['blank_votes'],
            )
            for entity_id in added_results
        )
    )
    session.bulk_insert_mappings(
        CandidateResult,
        (
            dict(
                id=uuid4(),
                election_result_id=result_uids[entity_id],
                votes=votes,
                candidate_id=added_candidates[candidate_id]['id']
            )
            for entity_id in added_results
            for candidate_id, votes in added_results[entity_id].items()
        )
    )
    session.bulk_insert_mappings(
        ListResult,
        (
            dict(
                id=uuid4(),
                election_result_id=result_uids[entity_id],
                votes=votes,
                list_id=added_lists[list_id]['id']
            )
            for entity_id in added_results
            for list_id, votes in added_list_results[entity_id].items()
            if list_id != '999'
        )
    )

    # Add the missing entities
    result_inserts = []
    remaining = set(entities.keys())
    if election.expats:
        remaining.add(0)
    remaining -= set(added_results.keys())
    for entity_id in remaining:
        entity = entities.get(entity_id, {})
        district = entity.get('district', '')
        if election.domain == 'region':
            if not election.distinct:
                continue
            if not principal.has_districts:
                continue
            if district not in districts:
                continue
        result_inserts.append(
            dict(
                id=uuid4(),
                election_id=election_id,
                name=entity.get('name', ''),
                district=district,
                entity_id=entity_id,
                counted=False
            )
        )
    session.bulk_insert_mappings(ElectionResult, result_inserts)

    return []
