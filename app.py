from flask import Flask, request, jsonify
from flask_mqtt import Mqtt

app = Flask(__name__)

# Conexão MQTT
app.config['MQTT_BROKER_URL'] = 'broker.hivemq.com'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_PASSWORD'] = ''  # Set this item when you need to verify username and password
app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
app.config['MQTT_TLS_ENABLED'] = False  # If your server supports TLS, set it True
topic = 'senai/leomb/estacionamento/vaga/+'

mqtt_client = Mqtt(app)

@mqtt_client.on_connect() # Conectar no MQTT
def handle_connect(client, userdata, flags, rc):
   if rc == 0:
       print('Conectado com sucesso!')
       mqtt_client.subscribe(topic) # subscribe topic
   else:
       print('Conexão ruim. Código:', rc)

@mqtt_client.on_message() # Receber MSG
def handle_mqtt_message(client, userdata, message):
   data = dict(
       topic=message.topic,
       payload=message.payload.decode()
  )
   print('Received message on topic: {topic} with payload: {payload}'.format(**data))

# Rotas
@app.route('/')
def homepage():
    return "<h1>Hello World</h1>"

if __name__ == "__main__":
    app.run(debug=True)