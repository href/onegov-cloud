import textwrap

from onegov.election_day.models import Principal
from onegov.election_day.models.principal import cantons


def test_load_principal():
    principal = Principal.from_yaml(textwrap.dedent("""
        name: Foobar
        logo:
        canton: zg
        color: '#000'
    """))

    assert principal.name == 'Foobar'
    assert principal.name == 'Foobar'
    assert principal.logo is None
    assert principal.canton == 'zg'
    assert principal.color == '#000'
    assert principal.base is None
    assert principal.analytics is None

    principal = Principal.from_yaml(textwrap.dedent("""
        name: Foobar
        logo:
        canton: zg
        color: '#000'
        base: 'http://www.zg.ch'
        analytics: "<script type=\\"text/javascript\\"></script>"
    """))

    assert principal.name == 'Foobar'
    assert principal.logo is None
    assert principal.canton == 'zg'
    assert principal.color == '#000'
    assert principal.base == 'http://www.zg.ch'
    assert principal.analytics == '<script type="text/javascript"></script>'


def test_municipalities():
    principal = Principal(name='Zug', canton='zg', logo=None, color=None)

    municipalities = {
        1701: {'name': 'Baar'},
        1702: {'name': 'Cham'},
        1703: {'name': 'Hünenberg'},
        1704: {'name': 'Menzingen'},
        1705: {'name': 'Neuheim'},
        1706: {'name': 'Oberägeri'},
        1707: {'name': 'Risch'},
        1708: {'name': 'Steinhausen'},
        1709: {'name': 'Unterägeri'},
        1710: {'name': 'Walchwil'},
        1711: {'name': 'Zug'},
    }

    assert principal.municipalities == {
        2013: municipalities,
        2014: municipalities,
        2015: municipalities,
        2016: municipalities,
    }

    for canton in cantons:
        principal = Principal(
            name=canton, canton=canton, logo=None, color=None
        )

        assert principal.municipalities[2013]
        assert principal.municipalities[2014]
        assert principal.municipalities[2015]
