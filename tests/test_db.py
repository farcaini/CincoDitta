import sqlite3

import pytest

from cincoditta.db import connect


def test_migrazioni_applicate_una_sola_volta(conn):
    versione = conn.execute("PRAGMA user_version").fetchone()[0]
    assert versione == 1
    with conn:
        conn.execute("INSERT INTO presse (codice) VALUES ('P1')")

    seconda = connect()

    assert seconda.execute("PRAGMA user_version").fetchone()[0] == 1
    assert seconda.execute("SELECT COUNT(*) FROM presse").fetchone()[0] == 1
    seconda.close()


def test_chiavi_esterne_rispettate(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO articoli (codice, stampo) VALUES ('A', 'INESISTENTE')")
