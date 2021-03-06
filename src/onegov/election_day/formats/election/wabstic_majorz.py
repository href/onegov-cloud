from onegov.ballot import Candidate
from onegov.ballot import CandidateResult
from onegov.ballot import ElectionResult
from onegov.election_day import _
from onegov.election_day.formats.common import EXPATS, \
    validate_integer, line_is_relevant
from onegov.election_day.formats.common import FileImportError
from onegov.election_day.formats.common import load_csv
from sqlalchemy.orm import object_session
from uuid import uuid4

from onegov.election_day.import_export.mappings import (
    WABSTIC_MAJORZ_HEADERS_WM_WAHL,
    WABSTIC_MAJORZ_HEADERS_WMSTATIC_GEMEINDEN,
    WABSTIC_MAJORZ_HEADERS_WM_GEMEINDEN, WABSTIC_MAJORZ_HEADERS_WM_KANDIDATEN,
    WABSTIC_MAJORZ_HEADERS_WM_KANDIDATENGDE)


def get_entity_id(line):
    col = 'bfsnrgemeinde'
    entity_id = validate_integer(line, col)
    return 0 if entity_id in EXPATS else entity_id


def import_election_wabstic_majorz(
    election, principal, number, district,
    file_wm_wahl, mimetype_wm_wahl,
    file_wmstatic_gemeinden, mimetype_wmstatic_gemeinden,
    file_wm_gemeinden, mimetype_wm_gemeinden,
    file_wm_kandidaten, mimetype_wm_kandidaten,
    file_wm_kandidatengde, mimetype_wm_kandidatengde
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
    wm_wahl, error = load_csv(
        file_wm_wahl, mimetype_wm_wahl,
        expected_headers=WABSTIC_MAJORZ_HEADERS_WM_WAHL,
        filename='wm_wahl'
    )
    if error:
        errors.append(error)

    wmstatic_gemeinden, error = load_csv(
        file_wmstatic_gemeinden, mimetype_wmstatic_gemeinden,
        expected_headers=WABSTIC_MAJORZ_HEADERS_WMSTATIC_GEMEINDEN,
        filename='wmstatic_gemeinden'
    )
    if error:
        errors.append(error)

    wm_gemeinden, error = load_csv(
        file_wm_gemeinden, mimetype_wm_gemeinden,
        expected_headers=WABSTIC_MAJORZ_HEADERS_WM_GEMEINDEN,
        filename='wm_gemeinden'
    )
    if error:
        errors.append(error)

    wm_kandidaten, error = load_csv(
        file_wm_kandidaten, mimetype_wm_kandidaten,
        expected_headers=WABSTIC_MAJORZ_HEADERS_WM_KANDIDATEN,
        filename='wm_kandidaten'
    )
    if error:
        errors.append(error)

    wm_kandidatengde, error = load_csv(
        file_wm_kandidatengde, mimetype_wm_kandidatengde,
        expected_headers=WABSTIC_MAJORZ_HEADERS_WM_KANDIDATENGDE,
        filename='wm_kandidatengde'
    )
    if error:
        errors.append(error)

    if errors:
        return errors

    # Parse the election
    absolute_majority = None
    remaining_entities = None

    for line in wm_wahl.lines:
        line_errors = []

        if not line_is_relevant(line, number):
            continue

        # Parse the absolute majority, if None, 0 will be returned
        try:
            absolute_majority = validate_integer(line, 'absolutesmehr')
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            if absolute_majority == -1:
                absolute_majority = None

        # Check if remaining entities is 0 is final, else unknown
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
                    error=err, line=line.rownumber, filename='wm_wahl'
                )
                for err in line_errors
            )
            continue

    # Parse the entities
    added_entities = {}
    for line in wmstatic_gemeinden.lines:
        line_errors = []

        if not line_is_relevant(line, number, district=district):
            continue

        # Parse the id of the entity
        try:
            entity_id = get_entity_id(line)
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            if entity_id and entity_id not in entities:
                line_errors.append(
                    _("${name} is unknown", mapping={'name': entity_id}))

            if entity_id in added_entities:
                line_errors.append(
                    _("${name} was found twice", mapping={'name': entity_id}))
            # Skip expats if not enabled
            if entity_id == 0 and not election.expats:
                continue

        # Parse the eligible voters
        try:
            eligible_voters = validate_integer(line, 'stimmberechtigte')
        except ValueError as e:
            line_errors.append(e.args[0])

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber,
                    filename='wmstatic_gemeinden'
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

    for line in wm_gemeinden.lines:
        line_errors = []

        # Parse the id of the entity
        try:
            entity_id = get_entity_id(line)
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
            entity['counted'] = False if validate_integer(
                line, 'sperrung') == 0 else True
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
            blank_votes = validate_integer(line, 'stimmenleer')
            invalid_votes = validate_integer(line, 'stimmenungueltig')
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            entity['received_ballots'] = received_ballots
            entity['blank_ballots'] = blank_ballots
            entity['invalid_ballots'] = invalid_ballots
            entity['blank_votes'] = blank_votes
            entity['invalid_votes'] = invalid_votes

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber, filename='wm_gemeinden'
                )
                for err in line_errors
            )
            continue

    # Parse the candidates
    added_candidates = {}
    for line in wm_kandidaten.lines:
        line_errors = []

        if not line_is_relevant(line, number):
            continue

        try:
            candidate_id = line.knr
            family_name = line.nachname
            first_name = line.vorname
            elected = True if line.gewaehlt == '1' else False
            party = line.partei
        except ValueError as e:
            line_errors.append(e.args[0])
        else:
            added_candidates[candidate_id] = dict(
                id=uuid4(),
                election_id=election_id,
                candidate_id=candidate_id,
                family_name=family_name,
                first_name=first_name,
                elected=elected,
                party=party
            )

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber, filename='wm_kandidaten'
                )
                for err in line_errors
            )
            continue

    # Parse the candidate results
    added_results = {}
    for line in wm_kandidatengde.lines:
        line_errors = []

        if not line_is_relevant(line, number):
            continue

        try:
            entity_id = get_entity_id(line)
            candidate_id = line.knr
            votes = validate_integer(line, 'stimmen', default=None)
        except ValueError:
            line_errors.append(_("Invalid candidate results"))
        else:
            if added_candidates and candidate_id not in added_candidates:
                line_errors.append(
                    _("Candidate with id ${id} not in wm_kandidaten",
                      mapping={'id': candidate_id}))
            if entity_id == 0 and not election.expats:
                # Skip expats if not enabled
                continue

            if entity_id not in added_entities:
                line_errors.append(
                    _("Entity with id ${id} not in wmstatic_gemeinden",
                        mapping={'id': entity_id}))

        # Pass the errors and continue to next line
        if line_errors:
            errors.extend(
                FileImportError(
                    error=err, line=line.rownumber,
                    filename='wm_kandidatengde'
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
                errors.append(FileImportError(_("No clear district")))
        else:
            if len(added_results) != 1:
                errors.append(FileImportError(_("No clear district")))

    if errors:
        return errors

    # Add the results to the DB
    election.clear_results()
    election.absolute_majority = absolute_majority
    election.status = 'unknown'
    if remaining_entities == 0:
        election.status = 'final'

    result_uids = {entity_id: uuid4() for entity_id in added_results}

    session = object_session(election)
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
                invalid_votes=added_entities[entity_id]['invalid_votes']
            )
            for entity_id in added_results.keys()
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
                district=entity.get('district', ''),
                entity_id=entity_id,
                counted=False
            )
        )
    session.bulk_insert_mappings(ElectionResult, result_inserts)

    return []
