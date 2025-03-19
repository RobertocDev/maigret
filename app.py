from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

# Cria o diretório 'reports' se ele não existir
os.makedirs("reports", exist_ok=True)

@app.route('/')
def home():
    return "Bem-vindo ao Maigret Flask Backend! Use /search?username=SEU_USERNAME para pesquisar."

@app.route('/search', methods=['GET'])
def search():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "O parâmetro 'username' é obrigatório."}), 400

    try:
        # Executa o maigret
        result = subprocess.run(
            ["maigret", username, "-J", "simple", "--top-sites", "300"],  # Verifica os 300 principais sites
            capture_output=True,
            text=True,
            check=True
        )
        print("Resultado do maigret (stdout):", result.stdout)  # Depuração
        print("Erros do maigret (stderr):", result.stderr)      # Depuração

        # Caminho do arquivo JSON gerado pelo maigret
        json_file_path = f"reports/report_{username}_simple.json"

        # Verifica se o arquivo JSON existe
        if not os.path.exists(json_file_path):
            print("Arquivo JSON não encontrado:", json_file_path)  # Depuração
            return jsonify({"error": "Arquivo JSON não encontrado."}), 500

        # Lê o conteúdo do arquivo JSON
        with open(json_file_path, "r") as file:
            json_result = json.load(file)

        # Processa o JSON para extrair as URLs encontradas
        all_urls = []  # Lista para armazenar todas as URLs encontradas
        details = {}   # Dicionário para armazenar os detalhes de cada site

        for site, data in json_result.items():
            if data.get("url_user"):  # Verifica se a URL do usuário existe
                all_urls.append(data["url_user"])
                details[site] = {
                    "status": "✅ Encontrado",
                    "url": data["url_user"]
                }
            else:
                details[site] = {
                    "status": "❌ Não encontrado",
                    "url": None
                }

        # Junta todas as URLs em um único texto
        all_urls_text = "\n".join(all_urls) if all_urls else "Nenhum perfil encontrado."

        # Estrutura a resposta para o Typebot
        response_data = {
            "statusCode": 200,
            "result": all_urls_text,  # Todas as URLs em um único texto
            "details":