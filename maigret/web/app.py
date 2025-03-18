#!/usr/bin/env python3
from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/search', methods=['GET'])
def search():
    # Obtém o nome de usuário da query string
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "O parâmetro 'username' é obrigatório."}), 400

    try:
        # Executa o maigret
        result = subprocess.run(
            ["maigret", username, "-J", "simple"],
            capture_output=True,
            text=True,
            check=True
        )
        # Converte a saída para JSON
        json_result = json.loads(result.stdout)
        return jsonify(json_result)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Erro ao executar maigret: {e.stderr}"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Erro ao processar o resultado do maigret."}), 500

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    app.run(debug=debug_mode)
#fim