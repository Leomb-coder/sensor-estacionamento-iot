from flask import Flask, render_template, jsonify, request
import json
from flask_mqtt import Mqtt

from db import (
    init_db,
    atualizar_status_vaga,
    get_vagas_status,
    get_ocupacoes,
    get_taxa_ocupacao,
    get_horarios_pico,
)

app = Flask(__name__)

# ---------- Conexão MQTT ----------
app.config['MQTT_BROKER_URL'] = 'broker.hivemq.com'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False

# ATENÇÃO: seu app.py original assinava 'senai/leomb/estacionamento/vaga/+',
# mas o README e o exemplo de payload usam 'senai/estacionamento/vaga/+'.
# Confirme com o firmware do ESP32 qual tópico ele realmente publica e ajuste aqui.
TOPIC = 'senai/leomb/estacionamento/vaga/+'

mqtt_client = Mqtt(app)


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print('[MQTT] Conectado com sucesso!')
        mqtt_client.subscribe(TOPIC)
    else:
        print('[MQTT] Conexão ruim. Código:', rc)


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    try:
        payload = message.payload.decode()
        print(f"[MQTT] Recebido em {message.topic}: {payload}")

        # extrai o número da vaga do próprio tópico (.../vaga/1, .../vaga/2, ...)
        numero_vaga = int(message.topic.rstrip('/').split('/')[-1])

        data = json.loads(payload)
        ocupada = bool(data["ocupada"])

        mudou = atualizar_status_vaga(numero_vaga, ocupada)
        if mudou:
            estado = "OCUPADA" if ocupada else "LIVRE"
            print(f"[DB] Vaga {numero_vaga} -> {estado}")

    except (KeyError, ValueError, json.JSONDecodeError) as ex:
        print("[MQTT] Mensagem inválida, ignorada:", ex)


# ---------- Páginas ----------

@app.route('/')
def homepage():
    return render_template('index.html')


# ---------- API para o Frontend ----------

@app.route('/api/vagas')
def api_vagas():
    """Status atual das vagas: livre/ocupada e, se ocupada, desde quando."""
    return jsonify(get_vagas_status())


@app.route('/api/ocupacoes')
def api_ocupacoes():
    """Histórico de entradas/saídas. Filtros opcionais: ?vaga=1&limite=20"""
    vaga = request.args.get('vaga', type=int)
    limite = request.args.get('limite', default=30, type=int)
    return jsonify(get_ocupacoes(vaga_numero=vaga, limite=limite))


@app.route('/api/estatisticas/taxa-ocupacao')
def api_taxa_ocupacao():
    """Percentual de vagas ocupadas agora."""
    return jsonify(get_taxa_ocupacao())


@app.route('/api/estatisticas/horarios-pico')
def api_horarios_pico():
    """Quantidade de entradas por hora do dia (0-23), para o gráfico."""
    return jsonify(get_horarios_pico())


if __name__ == "__main__":
    init_db()
    app.run(debug=True)