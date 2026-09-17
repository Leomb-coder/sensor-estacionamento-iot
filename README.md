# Sensor de Estacionamento com IOT

## Sobre o Projeto
Nosso projeto simula 3 vagas em um shopping, ele tem como objetivo facilitar a busca por uma vaga em um estacionamento, o funcionamento é o seguinte:<br>
- Quando uma vaga está vazia, uma luz verde ascende, mostrando que a mesma está disponivel para estacionar.<br>
- Quando uma vaga está ocupada, uma luz vermelha ascende, motrando que a vaga não está disponivel.<br>

## Frontend
O projeto deve mostrar as seguintes informações no Frontend:<br><br>
As vagas ocupadas ou desocupadas;<br>
Quando o carro entrou, quando saiu e quanto tempo ficou;<br>
Quais horários têm mais ocupação;<br>
Taxa de ocupação do estacionamento;<br>

## Banco de Dados

vagas<br>
----------------<br>
id<br>
numero<br>
status<br>
<br>
ocupacoes<br>
----------------<br>
id<br>
vaga_id<br>
entrada<br>
saida<br>

# MQTT

Os tópicos são organizados assim:<br>
<br>
senai/estacionamento/vaga/1<br>
senai/estacionamento/vaga/2<br>
senai/estacionamento/vaga/3<br>
senai/estacionamento/vaga/4<br>
<br>
Mensagem:<br>
<br>
{<br>
  "ocupada": true,<br>
  "distancia": 8.4<br>
}<br>

## Fontes Usadas:
Sistema MQTT: [https://www.emqx.com/en/blog/how-to-use-mqtt-in-flask](https://www.emqx.com/en/blog/how-to-use-mqtt-in-flask)
