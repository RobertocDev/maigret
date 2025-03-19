from flask import Flask, request, jsonify
import subprocess
import json
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bem-vindo ao Maigret Flask Backend! Use /search?username=SEU_USERNAME para pesquisar."

@app.route('/search', methods=['GET'])
def search():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "O parâmetro 'username' é obrigatório."}), 400

    try:
        result = subprocess.run(
            ["maigret", username, "-J", "simple", "--top-sites", "20"],
            capture_output=True,
            text=True,
            check=True
        )
        print("Resultado do maigret (stdout):", result.stdout)  # Depuração
        print("Erros do maigret (stderr):", result.stderr)      # Depuração

        json_file_path = f"/workspaces/maigret/reports/report_{username}_simple.json"

        if not os.path.exists(json_file_path):
            return jsonify({"error": "Arquivo JSON não encontrado."}), 500

        with open(json_file_path, "r") as file:
            json_result = json.load(file)

        return jsonify(json_result)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Erro ao executar maigret: {e.stderr}"}), 500
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Erro ao processar o resultado do maigret: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)