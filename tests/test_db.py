from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

import db


@pytest.fixture
def mock_connection():
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value.__enter__.return_value = cursor

    return conn, cursor


def test_get_connection():
    fake_connection = MagicMock()

    with patch("db.psycopg2.connect", return_value=fake_connection) as mock_connect:
        conn = db.get_connection()

        assert conn == fake_connection
        mock_connect.assert_called_once()


def test_get_connection_erro():
    with patch(
        "db.psycopg2.connect",
        side_effect=Exception("Erro de conexão")
    ):
        conn = db.get_connection()

        assert conn is None


def test_init_db(mock_connection):
    conn, cursor = mock_connection

    with patch("db.get_connection", return_value=conn):
        db.init_db()

    # CREATE TABLE vagas
    # CREATE TABLE ocupacoes
    # INSERT das vagas 1, 2 e 3
    assert cursor.execute.call_count == 5

    conn.commit.assert_called_once()
    conn.close.assert_called_once()


def test_atualizar_status_vaga_ocupada(mock_connection):
    conn, cursor = mock_connection

    # Vaga 1 existe e está livre
    cursor.fetchone.return_value = (1, False)

    with patch("db.get_connection", return_value=conn):
        resultado = db.atualizar_status_vaga(1, True)

    assert resultado is True

    # UPDATE vagas
    # INSERT ocupação
    assert cursor.execute.call_count == 3

    conn.commit.assert_called_once()
    conn.close.assert_called_once()


def test_atualizar_status_vaga_livre(mock_connection):
    conn, cursor = mock_connection

    # Vaga 1 existe e está ocupada
    cursor.fetchone.return_value = (1, True)

    with patch("db.get_connection", return_value=conn):
        resultado = db.atualizar_status_vaga(1, False)

    assert resultado is True

    # SELECT
    # UPDATE vagas
    # UPDATE ocupacoes
    assert cursor.execute.call_count == 3

    conn.commit.assert_called_once()
    conn.close.assert_called_once()


def test_atualizar_status_sem_mudanca(mock_connection):
    conn, cursor = mock_connection

    # Vaga já está ocupada
    cursor.fetchone.return_value = (1, True)

    with patch("db.get_connection", return_value=conn):
        resultado = db.atualizar_status_vaga(1, True)

    assert resultado is False

    # Apenas o SELECT deve ter sido executado
    assert cursor.execute.call_count == 1

    conn.commit.assert_not_called()
    conn.close.assert_called_once()


def test_atualizar_status_vaga_inexistente(mock_connection):
    conn, cursor = mock_connection

    cursor.fetchone.return_value = None

    with patch("db.get_connection", return_value=conn):
        resultado = db.atualizar_status_vaga(99, True)

    assert resultado is False

    assert cursor.execute.call_count == 1

    conn.commit.assert_not_called()
    conn.close.assert_called_once()


def test_atualizar_status_sem_conexao():
    with patch("db.get_connection", return_value=None):
        resultado = db.atualizar_status_vaga(1, True)

    assert resultado is False


def test_get_vagas_status(mock_connection):
    conn, cursor = mock_connection

    entrada = datetime(2026, 9, 18, 10, 30)

    cursor.fetchall.return_value = [
        (1, False, None),
        (2, True, entrada),
        (3, False, None)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_vagas_status()

    assert resultado == [
        {
            "numero": 1,
            "ocupada": False,
            "entrada": None
        },
        {
            "numero": 2,
            "ocupada": True,
            "entrada": "2026-09-18T10:30:00"
        },
        {
            "numero": 3,
            "ocupada": False,
            "entrada": None
        }
    ]

    conn.close.assert_called_once()


def test_get_vagas_status_sem_conexao():
    with patch("db.get_connection", return_value=None):
        resultado = db.get_vagas_status()

    assert resultado == []


def test_get_ocupacoes(mock_connection):
    conn, cursor = mock_connection

    entrada = datetime(2026, 9, 18, 10, 0)
    saida = datetime(2026, 9, 18, 11, 30)

    cursor.fetchall.return_value = [
        (1, entrada, saida)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_ocupacoes()

    assert resultado == [
        {
            "vaga": 1,
            "entrada": "2026-09-18T10:00:00",
            "saida": "2026-09-18T11:30:00",
            "duracao_min": 90.0
        }
    ]

    conn.close.assert_called_once()


def test_get_ocupacoes_vaga_especifica(mock_connection):
    conn, cursor = mock_connection

    entrada = datetime(2026, 9, 18, 10, 0)
    saida = datetime(2026, 9, 18, 11, 0)

    cursor.fetchall.return_value = [
        (2, entrada, saida)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_ocupacoes(
            vaga_numero=2,
            limite=10
        )

    assert resultado == [
        {
            "vaga": 2,
            "entrada": "2026-09-18T10:00:00",
            "saida": "2026-09-18T11:00:00",
            "duracao_min": 60.0
        }
    ]

    cursor.execute.assert_called_once()


def test_get_ocupacoes_vaga_em_aberto(mock_connection):
    conn, cursor = mock_connection

    entrada = datetime(2026, 9, 18, 10, 0)

    cursor.fetchall.return_value = [
        (1, entrada, None)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_ocupacoes()

    assert resultado == [
        {
            "vaga": 1,
            "entrada": "2026-09-18T10:00:00",
            "saida": None,
            "duracao_min": None
        }
    ]


def test_get_taxa_ocupacao(mock_connection):
    conn, cursor = mock_connection

    # Primeiro fetchone: total
    # Segundo fetchone: ocupadas
    cursor.fetchone.side_effect = [
        (3,),
        (1,)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_taxa_ocupacao()

    assert resultado == {
        "total": 3,
        "ocupadas": 1,
        "taxa": 33.3
    }

    assert cursor.execute.call_count == 2
    conn.close.assert_called_once()


def test_get_taxa_ocupacao_todas_livres(mock_connection):
    conn, cursor = mock_connection

    cursor.fetchone.side_effect = [
        (3,),
        (0,)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_taxa_ocupacao()

    assert resultado == {
        "total": 3,
        "ocupadas": 0,
        "taxa": 0.0
    }


def test_get_taxa_ocupacao_sem_vagas(mock_connection):
    conn, cursor = mock_connection

    cursor.fetchone.side_effect = [
        (0,),
        (0,)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_taxa_ocupacao()

    assert resultado == {
        "total": 0,
        "ocupadas": 0,
        "taxa": 0
    }


def test_get_horarios_pico(mock_connection):
    conn, cursor = mock_connection

    cursor.fetchall.return_value = [
        (8, 5),
        (12, 10),
        (18, 7)
    ]

    with patch("db.get_connection", return_value=conn):
        resultado = db.get_horarios_pico()

    assert resultado == [
        {"hora": 8, "total": 5},
        {"hora": 12, "total": 10},
        {"hora": 18, "total": 7}
    ]

    conn.close.assert_called_once()


def test_get_horarios_pico_sem_conexao():
    with patch("db.get_connection", return_value=None):
        resultado = db.get_horarios_pico()

    assert resultado == []