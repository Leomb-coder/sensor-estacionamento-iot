import json
from unittest.mock import patch

import pytest

from app import app, handle_mqtt_message


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_homepage(client):
    response = client.get("/")

    assert response.status_code == 200


@patch("app.get_vagas_status")
def test_api_vagas(mock_get_vagas_status, client):
    mock_get_vagas_status.return_value = [
        {
            "numero": 1,
            "ocupada": False,
            "entrada": None
        },
        {
            "numero": 2,
            "ocupada": True,
            "entrada": "2026-09-18T10:00:00"
        }
    ]

    response = client.get("/api/vagas")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "numero": 1,
            "ocupada": False,
            "entrada": None
        },
        {
            "numero": 2,
            "ocupada": True,
            "entrada": "2026-09-18T10:00:00"
        }
    ]

    mock_get_vagas_status.assert_called_once()


@patch("app.get_ocupacoes")
def test_api_ocupacoes(mock_get_ocupacoes, client):
    mock_get_ocupacoes.return_value = [
        {
            "vaga": 1,
            "entrada": "2026-09-18T10:00:00",
            "saida": "2026-09-18T11:00:00",
            "duracao_min": 60.0
        }
    ]

    response = client.get("/api/ocupacoes")

    assert response.status_code == 200
    assert response.get_json() == mock_get_ocupacoes.return_value

    mock_get_ocupacoes.assert_called_once_with(
        vaga_numero=None,
        limite=30
    )


@patch("app.get_ocupacoes")
def test_api_ocupacoes_com_filtros(mock_get_ocupacoes, client):
    mock_get_ocupacoes.return_value = []

    response = client.get("/api/ocupacoes?vaga=2&limite=10")

    assert response.status_code == 200
    assert response.get_json() == []

    mock_get_ocupacoes.assert_called_once_with(
        vaga_numero=2,
        limite=10
    )


@patch("app.get_taxa_ocupacao")
def test_api_taxa_ocupacao(mock_get_taxa, client):
    mock_get_taxa.return_value = {
        "total": 3,
        "ocupadas": 1,
        "taxa": 33.3
    }

    response = client.get("/api/estatisticas/taxa-ocupacao")

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 3,
        "ocupadas": 1,
        "taxa": 33.3
    }

    mock_get_taxa.assert_called_once()


@patch("app.get_horarios_pico")
def test_api_horarios_pico(mock_get_horarios, client):
    mock_get_horarios.return_value = [
        {"hora": 8, "total": 5},
        {"hora": 12, "total": 10},
        {"hora": 18, "total": 7}
    ]

    response = client.get("/api/estatisticas/horarios-pico")

    assert response.status_code == 200
    assert response.get_json() == mock_get_horarios.return_value

    mock_get_horarios.assert_called_once()


def test_mqtt_ocupacao():
    message = type(
        "Message",
        (),
        {
            "topic": "senai/leomb/estacionamento/vaga/1",
            "payload": json.dumps({"ocupada": True}).encode()
        }
    )()

    with patch("app.atualizar_status_vaga") as mock_atualizar:
        mock_atualizar.return_value = True

        handle_mqtt_message(None, None, message)

        mock_atualizar.assert_called_once_with(1, True)


def test_mqtt_vaga_livre():
    message = type(
        "Message",
        (),
        {
            "topic": "senai/leomb/estacionamento/vaga/2",
            "payload": json.dumps({"ocupada": False}).encode()
        }
    )()

    with patch("app.atualizar_status_vaga") as mock_atualizar:
        mock_atualizar.return_value = True

        handle_mqtt_message(None, None, message)

        mock_atualizar.assert_called_once_with(2, False)


def test_mqtt_mensagem_invalida():
    message = type(
        "Message",
        (),
        {
            "topic": "senai/leomb/estacionamento/vaga/1",
            "payload": b'{"errado": true}'
        }
    )()

    with patch("app.atualizar_status_vaga") as mock_atualizar:
        handle_mqtt_message(None, None, message)

        mock_atualizar.assert_not_called()


def test_mqtt_json_invalido():
    message = type(
        "Message",
        (),
        {
            "topic": "senai/leomb/estacionamento/vaga/1",
            "payload": b'isso nao e json'
        }
    )()

    with patch("app.atualizar_status_vaga") as mock_atualizar:
        handle_mqtt_message(None, None, message)

        mock_atualizar.assert_not_called()