from datetime import datetime, timezone
from flask import Flask, Response, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import json
import paho.mqtt.client as mqtt
import os

# ********************* CONEXÃO BANCO DE DADOS *********************************

app = Flask('registro')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Configura o SQLAlchemy para rastrear modificações dos objetos, o que não é recomendado para produção.
# O SQLAlchemy cria e modifica todos os dados da nossa tabela de forma automatica 
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://jessica:senai%40134@projetointegradorbanco.mysql.database.azure.com:3306/bd_medidorgranja'



# Configuração do servidor
server_name = 'projetointegradorbanco.mysql.database.azure.com'
port='3306'
username = 'jessica'
password = 'senai%40134'
database = 'medidor'


# # Caminho para o certificado CA (neste exemplo, assumindo que está no diretório raiz do projeto)
ca_certificate_path = 'DigiCertGlobalRootCA.crt.pem'

# # Construção da URI com SSL
uri = f"mysql://{username}:{password}@{server_name}:3306/{database}"
ssl_options = f"?ssl_ca={ca_certificate_path}"

app.config['SQLALCHEMY_DATABASE_URI'] = uri + ssl_options

# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://jessica:senai%40134@projetointegradorbanco.mysql.database.azure.com/medidor'
# Configura a URI de conexão com o banco de dados MySQL.
# Senha -> senai@134, porém aqui a senha passa a ser -> senai%40134
# app.config['SQLALCHEMY_ECHO'] = True  # Habilita o log de SQLAlchemy

mybd = SQLAlchemy(app)
# Cria uma instância do SQLAlchemy, passando a aplicação Flask como parâmetro.

# ********************* CONEXÃO SENSORES *********************************

mqtt_data = {}

def on_connect(client, userdata, flags, rc):
    # client: A instância do cliente MQTT.
    # userdata: Dados do usuário definidos quando o cliente foi configurado (geralmente None).
    # flags: Dicionário contendo sinalizadores de resposta do broker.
    # rc: Código de resultado da conexão (0 significa sucesso; valores diferentes de zero indicam erros).
    print("Connected with result code " + str(rc))
    client.subscribe("projeto_integrado/SENAI134/Cienciadedados/GrupoABC")

def on_message(client, userdata, msg):
    global mqtt_data
 # Decodifica a mensagem recebida de bytes para string
    payload = msg.payload.decode('utf-8')
    
    # Converte a string JSON em um dicionário Python
    mqtt_data = json.loads(payload)
    
    # Imprime a mensagem recebida
    print(f"Received message: {mqtt_data}")

    # Adiciona o contexto da aplicação para a manipulação do banco de dados
    with app.app_context():
        try:
            temperatura = mqtt_data.get('temperature')
            pressao = mqtt_data.get('pressure')
            altitude = mqtt_data.get('altitude')
            umidade = mqtt_data.get('humidity')
            co2 = mqtt_data.get('CO2')
            poeira1 = mqtt_data.get('particula1')
            poeira2 = mqtt_data.get('particula2')
            timestamp_unix = mqtt_data.get('timestamp')

            if timestamp_unix is None:
                print("Timestamp não encontrado no payload")
                return

            # Converte timestamp Unix para datetime
            try:
                timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc)
            except (ValueError, TypeError) as e:
                print(f"Erro ao converter timestamp: {str(e)}")
                return

            # Cria o objeto Registro com os dados
            new_data = Registro(
                temperatura=temperatura,
                pressao=pressao,
                altitude=altitude,
                umidade=umidade,
                co2=co2,
                poeira1=poeira1,
                poeira2=poeira2,
                tempo_registro=timestamp
            )

            # Adiciona o novo registro ao banco de dados
            mybd.session.add(new_data)
            mybd.session.commit()
            print("Dados inseridos no banco de dados com sucesso")

        except Exception as e:
            print(f"Erro ao processar os dados do MQTT: {str(e)}")
            mybd.session.rollback()

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("test.mosquitto.org", 1883, 60)

def start_mqtt():
    mqtt_client.loop_start()
    

class Registro(mybd.Model):
    __tablename__ = 'registro'
    id = mybd.Column(mybd.Integer, primary_key=True, autoincrement=True)
    temperatura = mybd.Column(mybd.Numeric(10, 2))
    pressao = mybd.Column(mybd.Numeric(10, 2))
    altitude = mybd.Column(mybd.Numeric(10, 2))
    umidade = mybd.Column(mybd.Numeric(10, 2))
    co2 = mybd.Column(mybd.Numeric(10, 2))
    poeira1 = mybd.Column(mybd.Numeric(10, 2))
    poeira2 = mybd.Column(mybd.Numeric(10, 2))
    tempo_registro = mybd.Column(mybd.DateTime)
    
    def to_json(self):# Define um método 'to_json' que será usado para converter um objeto em um dicionário JSON.
        return {  # Inicia a construção do dicionário que representará os dados em formato JSON.
            "id": self.id,
            "temperatura": float(self.temperatura),
            "pressao": float(self.pressao),
            "altitude": float(self.altitude),
            "umidade": float(self.umidade),
            "co2": float(self.co2),
            "poeira1": float(self.poeira1),
            "poeira2": float(self.poeira2),
            "tempo_registro": self.tempo_registro.strftime('%Y-%m-%d %H:%M:%S') if self.tempo_registro else None 
            # Verifica se 'tempo_registro' existe. Se existir, converte para uma string no formato 'YYYY-MM-DD HH:MM:SS';
            # caso contrário, adiciona None ao dicionário.
        }

    
# ********************************************************************************************************


@app.route('/data', methods=['GET']) # Define uma rota '/data' que aceita apenas requisições do tipo GET.
def get_data(): # Define a função 'get_data' que será chamada quando a rota '/data' for acessada.
    return jsonify(mqtt_data)  # Retorna os dados 'mqtt_data' em formato JSON. O jsonify converte um dicionário Python em JSON.


# **********************************************************************************

@app.route("/registro", methods=["GET"]) # Define uma rota '/registro' que aceita apenas requisições do tipo GET.
def seleciona_registro():
    registro_objetos = Registro.query.all()  # Faz uma consulta ao banco de dados para obter todos os registros da tabela 'Registro' e armazena os objetos resultantes na variável 'registro_objetos'.
    registro_json = [registro.to_json() for registro in registro_objetos] # Usa uma list comprehension para converter cada objeto de registro em um dicionário JSON, chamando o método 'to_json()' de cada objeto, e armazena o resultado na lista 'registro_json'.
    return gera_response(200, "registro", registro_json)  # Retorna uma resposta gerada pela função 'gera_response', com um status de 200 (OK), uma mensagem "registro" e os dados JSON dos registros.


# *******************************************************************************

@app.route("/registro/<id>", methods=["GET"]) # Define uma rota '/registro/<id>' que aceita requisições do tipo GET. O '<id>' é um parâmetro dinâmico na URL.
def seleciona_registro_id(id):
    registro_objetos = Registro.query.filter_by(id=id).first()  # Realiza uma consulta ao banco de dados para buscar o primeiro registro na tabela 'Registro' que tenha o 'id' especificado. O resultado é armazenado na variável 'registro_objetos'.
    if registro_objetos: # Verifica se um objeto de registro foi encontrado.
        registro_json = registro_objetos.to_json() # Se encontrado, converte o objeto de registro em um dicionário JSON usando o método 'to_json()'.
        return gera_response(200, "registro", registro_json)
    else:  # Se nenhum registro correspondente for encontrado..
        return gera_response(404, "registro", {}, "Registro não encontrado") # Retorna uma resposta gerada pela função 'gera_response' com status 404 (Não Encontrado), uma mensagem "registro", um dicionário vazio e uma mensagem adicional informando que o registro não foi encontrado.

# *************************************************************************************


# Cadastrar
@app.route('/data', methods=['POST'])
def post_data():
    try: 
        data = request.get_json() # Obtém os dados enviados na requisição em formato JSON.

        if not data: # Verifica se nenhum dado foi fornecido.
            return jsonify({"error": "Nenhum dado fornecido"}), 400 # Retorna um erro com status 400 (Bad Request) se não houver dados.

        # Adiciona logs para depuração
        print(f"Dados recebidos: {data}") # Imprime os dados recebidos no console para depuração.

        temperatura = data.get('temperatura')
        pressao = data.get('pressao')
        altitude = data.get('altitude')
        umidade = data.get('umidade')
        co2 = data.get('co2')
        poeira1 = data.get('particula1')
        poeira2 = data.get('particula2')
        timestamp_unix = data.get('tempo_registro')

        # Converte timestamp Unix para datetime
        try:
            timestamp = datetime.fromtimestamp(int(timestamp_unix), tz=timezone.utc) # Converte o timestamp Unix em um objeto datetime.
        except ValueError as e: # Captura erros de valor durante a conversão.
            print(f"Erro no timestamp: {str(e)}") # Imprime a mensagem de erro no console.
            return jsonify({"error": "Timestamp inválido"}), 400  # Retorna um erro com status 400 se o timestamp for inválido.

        # Cria o objeto Registro com os dados
        new_data = Registro( # Cria uma nova instância do modelo 'Registro' com os dados recebidos.
            temperatura=temperatura,
            pressao=pressao,
            altitude=altitude,
            umidade=umidade,
            co2=co2,
            poeira1=poeira1,
            poeira2=poeira2,
            tempo_registro=timestamp
        )

        # Adiciona o novo registro ao banco de dados
        mybd.session.add(new_data)  # Adiciona o novo objeto de registro à sessão do banco de dados
        print("Adicionando o novo registro") # Imprime uma mensagem indicando que o novo registro está sendo adicionado

        # Tenta confirmar a transação
        mybd.session.commit()
        print("Dados inseridos no banco de dados com sucesso")

        return jsonify({"message": "Data received successfully"}), 201 # Retorna uma mensagem de sucesso com status 201 (Created).

    except Exception as e:
        print(f"Erro ao processar a solicitação: {str(e)}")
        mybd.session.rollback()  # Reverte qualquer alteração em caso de erro
        return jsonify({"error": "Falha ao processar os dados"}), 500  # Retorna um erro com status 500 (Internal Server Error) se algo falhar.
 

# *************************************************************************************

@app.route("/registro/<id>", methods=["DELETE"])  # Define uma rota '/registro/<id>' que aceita requisições do tipo DELETE.
def deleta_registro(id):  # Define a função 'deleta_registro' que será chamada ao receber uma requisição DELETE para essa rota.
    registro_objetos = Registro.query.filter_by(id=id).first()  # Busca o primeiro registro no banco de dados com o ID fornecido na URL.

    if registro_objetos:  # Verifica se um registro foi encontrado.
        try:
            mybd.session.delete(registro_objetos)  # Remove o objeto encontrado da sessão do banco de dados.
            mybd.session.commit()  # Tenta confirmar a transação para deletar o registro do banco de dados.
            return gera_response(200, "registro", registro_objetos.to_json(), "Deletado com sucesso")  # Retorna uma resposta de sucesso com status 200 (OK).
        except Exception as e:  # Captura qualquer exceção que ocorra durante a tentativa de deletar o registro.
            print('Erro', e)  # Imprime a mensagem de erro no console para depuração.
            mybd.session.rollback()  # Reverte qualquer alteração na sessão do banco de dados em caso de erro.
            return gera_response(400, "registro", {}, "Erro ao deletar")  # Retorna uma resposta de erro com status 400 (Bad Request).
    else:  # Se nenhum registro foi encontrado com o ID fornecido.
        return gera_response(404, "registro", {}, "Registro não encontrado")  # Retorna uma resposta de erro com status 404 (Not Found) indicando que o registro não foi encontrado.

    
# **************************************************************************

def gera_response(status, nome_do_conteudo, conteudo, mensagem=False):  # Define uma função chamada 'gera_response' que cria uma resposta JSON.
    body = {}  # Inicializa um dicionário vazio para armazenar o corpo da resposta.
    body[nome_do_conteudo] = conteudo  # Adiciona o conteúdo ao dicionário usando 'nome_do_conteudo' como chave.
    
    if mensagem:  # Verifica se a variável 'mensagem' foi fornecida (ou seja, não é False).
        body["mensagem"] = mensagem  # Se for, adiciona essa mensagem ao dicionário de resposta.
    
    return Response(json.dumps(body), status=status, mimetype="application/json")  # Retorna uma resposta HTTP com o corpo em formato JSON, o status e o tipo MIME apropriado.

if __name__ == '__main__':  # Verifica se este arquivo está sendo executado como o programa principal.
    with app.app_context():  # Cria um contexto de aplicativo Flask para executar a criação do banco de dados.
        # mybd.create_all()  # Chama o método 'create_all' para criar todas as tabelas definidas no modelo do banco de dados.
    
        start_mqtt()  # Chama a função 'start_mqtt', que presumivelmente inicia um cliente MQTT (protocolo de mensagens para dispositivos).
        port = int(os.environ.get("PORT", 8080))  # Azure define a porta automaticamente
        app.run(host='0.0.0.0', port=port)  # Ouvir em todas as interfaces e usar a porta fornecida pela Azure
