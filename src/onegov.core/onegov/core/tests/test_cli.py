# -*- coding: utf-8 -*-
import os.path
import yaml

from click.testing import CliRunner
from email.header import decode_header
from onegov.core import Framework
from onegov.core.cli import cli


def test_sendmail(smtpserver, temporary_directory):

    cfg = {
        'applications': [
            {
                'path': '/foobar/*',
                'application': 'onegov.core.Framework',
                'namespace': 'foobar',
                'configuration': {
                    'mail_use_directory': True,
                    'mail_directory': os.path.join(
                        temporary_directory, 'mails')
                }
            }
        ]
    }

    os.makedirs(os.path.join(temporary_directory, 'mails'))
    os.makedirs(os.path.join(temporary_directory, 'mails', 'new'))
    os.makedirs(os.path.join(temporary_directory, 'mails', 'cur'))
    os.makedirs(os.path.join(temporary_directory, 'mails', 'tmp'))

    with open(os.path.join(temporary_directory, 'onegov.yml'), 'w') as f:
        f.write(yaml.dump(cfg))

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', os.path.join(temporary_directory, 'onegov.yml'),
        'sendmail',
        '--hostname', smtpserver.addr[0],
        '--port', smtpserver.addr[1]
    ])

    assert result.exit_code == 0
    assert len(smtpserver.outbox) == 0

    app = Framework()
    app.mail_sender = 'noreply@example.org'
    app.mail_use_directory = True
    app.mail_directory = os.path.join(temporary_directory, 'mails')

    result = app.send_email(
        reply_to='Govikon <info@example.org>',
        receivers=['recipient@example.org'],
        subject="Test E-Mail",
        content="This e-mail is just a test"
    )

    assert result.ok
    assert len(smtpserver.outbox) == 0

    result = runner.invoke(cli, [
        '--config', os.path.join(temporary_directory, 'onegov.yml'),
        'sendmail',
        '--hostname', smtpserver.addr[0],
        '--port', smtpserver.addr[1]
    ])

    assert result.exit_code == 0
    assert len(smtpserver.outbox) == 1

    result = runner.invoke(cli, [
        '--config', os.path.join(temporary_directory, 'onegov.yml'),
        'sendmail',
        '--hostname', smtpserver.addr[0],
        '--port', smtpserver.addr[1]
    ])

    assert result.exit_code == 0
    assert len(smtpserver.outbox) == 1

    message = smtpserver.outbox[0]

    assert message['Sender'] == 'Govikon <noreply@example.org>'
    assert message['From'] == 'Govikon <noreply@example.org>'
    assert message['Reply-To'] == 'Govikon <info@example.org>'
    assert message['Subject'] == 'Test E-Mail'
    assert message.get_payload()[0].as_string() == (
        'Content-Type: text/html; charset="iso-8859-1"\n'
        'MIME-Version: 1.0\n'
        'Content-Transfer-Encoding: quoted-printable\n\n'
        'This e-mail is just a test'
    )


def test_sendmail_unicode(smtpserver, temporary_directory):

    cfg = {
        'applications': [
            {
                'path': '/foobar/*',
                'application': 'onegov.core.Framework',
                'namespace': 'foobar',
                'configuration': {
                    'mail_use_directory': True,
                    'mail_directory': os.path.join(
                        temporary_directory, 'mails')
                }
            }
        ]
    }

    os.makedirs(os.path.join(temporary_directory, 'mails'))
    os.makedirs(os.path.join(temporary_directory, 'mails', 'new'))
    os.makedirs(os.path.join(temporary_directory, 'mails', 'cur'))
    os.makedirs(os.path.join(temporary_directory, 'mails', 'tmp'))

    with open(os.path.join(temporary_directory, 'onegov.yml'), 'w') as f:
        f.write(yaml.dump(cfg))

    app = Framework()
    app.mail_sender = u'noreply@exämple.org'
    app.mail_use_directory = True
    app.mail_directory = os.path.join(temporary_directory, 'mails')

    app.send_email(
        reply_to=u'Gövikon <info@exämple.org>',
        receivers=[u'recipient@exämple.org'],
        subject=u"Test E-Mäil",
        content=u"This e-mäil is just a test"
    )

    CliRunner().invoke(cli, [
        '--config', os.path.join(temporary_directory, 'onegov.yml'),
        'sendmail',
        '--hostname', smtpserver.addr[0],
        '--port', smtpserver.addr[1]
    ])

    message = smtpserver.outbox[0]

    def decode(header):
        return decode_header(header)[0][0].decode('utf-8')

    assert decode(message['Sender']) == u"Gövikon <noreply@exämple.org>"
    assert decode(message['From']) == u"Gövikon <noreply@exämple.org>"
    assert decode(message['Reply-To']) == u"Gövikon <info@exämple.org>"
    assert decode(message['Subject']) == u"Test E-Mäil"
    assert message.get_payload()[0].as_string() == (
        'Content-Type: text/html; charset="iso-8859-1"\n'
        'MIME-Version: 1.0\n'
        'Content-Transfer-Encoding: quoted-printable\n\n'
        'This e-m=E4il is just a test'
    )
