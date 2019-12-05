from onegov.fsi.models import Course


def test_add_course(client):
    view = '/fsi/courses/add'
    client.login_editor()
    client.get(view, status=403)

    client.login_admin()
    new = client.get(view)
    new.form['description'] = 'New Course'
    new.form['name'] = 'New Course'
    new.form.submit()


def test_course_details(client_with_db):
    client = client_with_db
    session = client.app.session()
    course = session.query(Course).first()
    view = f'/fsi/course/{course.id}'
    client.get(view, status=403)

    client.login_member()
    page = client.get(view)

    assert course.name in page
    assert course.description in page


def test_edit_course(client_with_db):
    client = client_with_db
    session = client.app.session()
    course = session.query(Course).first()
    view = f'/fsi/course/{course.id}/edit'

    client.login_editor()
    client.get(view, status=403)

    client.login_admin()
    new = client.get(view)
    new.form['description'] = 'Changed'
    new.form['name'] = 'Changed'
    page = new.form.submit().follow()
    assert 'Changed' in page


def test_delete_course_1(client_with_db):
    client = client_with_db
    assert client.use_intercooler is True
    session = client.app.session()
    course = session.query(Course).first()
    # course_id = course.id
    view = f'/fsi/course/{course.id}'
    client.login_admin()
    assert not course.events.count()

    # csrf protected url must be used
    client.delete(view, status=403)
    page = client.get(view)
    page.click('Löschen')

    page = client.get(view)
    assert "Dieser Kurs besitzt bereits Durchführungen " \
           "und kann nicht gelöscht werden." in page
    # for event in course.events:
    #     session.delete(event)
    # session.flush()
    #
    # page = client.get(view)
    # assert "Keine Einträge gefunden" in page
    # assert not session.query(Course).filter_by(id=course_id).first()


def test_course_invite(client_with_db):
    client = client_with_db
    session = client.app.session()
    course = session.query(Course).first()
    view = f'/fsi/course/{course.id}/invite'

    client.login_member()
    client.get(view, status=403)

    client.login_editor()
    client.get(view)


def test_course_collection(client):
    view = '/fsi/courses'
    client.get(view, status=403)

    client.login_member(to=view)
    client.get(view)


def test_course_1(client_with_db):
    client = client_with_db
    session = client.app.session()
    course = session.query(Course).first()
    view = f'/fsi/course/{course.id}'
    client.get(view, status=403)

    client.login_member()
    client.get(view, status=200)