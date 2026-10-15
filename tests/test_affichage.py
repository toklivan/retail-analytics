from datetime import date

from retail_analytics.affichage import date_fr, euros, nombre, pourcentage


def test_euros():
    assert euros(1234560) == "12 345,60 €"
    assert euros(7) == "0,07 €"
    assert euros(0) == "0,00 €"
    assert euros(-110) == "-1,10 €"
    assert euros(123456789) == "1 234 567,89 €"


def test_pourcentage():
    assert pourcentage(0.0328) == "3,3 %"
    assert pourcentage(0) == "0,0 %"


def test_date_fr():
    assert date_fr(date(2026, 3, 2)) == "02/03/2026"


def test_nombre():
    assert nombre(28578) == "28 578"
    assert nombre(12) == "12"
