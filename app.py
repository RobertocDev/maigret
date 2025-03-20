from flask import Flask, request, jsonify, send_file
import subprocess
import json
import os
import sys
from io import BytesIO

# Verifica se as dependências estão instaladas
try:
    import requests
    from PIL import Image
    import imageio
except ImportError as e:
    print(f"Erro: {e}. Instale as dependências necessárias.")
    sys.exit(1)

app = Flask(__name__)

# Cria o diretório 'reports' se ele não existir
os.makedirs("reports", exist_ok=True)

def download_image(url):
    """Baixa uma imagem a partir de uma URL."""
    try:
        response = requests.get(url, timeout=10)  # Adiciona um timeout para evitar loops
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Erro ao baixar a imagem {url}: {e}")
    return None

def create_gif(image_urls, output_path, duration=500):
    """Cria um GIF a partir de uma lista de URLs de imagens."""
    images = []
    for url in image_urls:
        print(f"Baixando imagem: {url}")  # Depuração
        img = download_image(url)
        if img:
            print(f"Imagem baixada com sucesso: {url}")  # Depuração
            images.append(img)
        else:
            print(f"Falha ao baixar a imagem: {url}")  # Depuração
    
    if images:
        try:
            # Salva as imagens como GIF
            images[0].save(output_path, save_all=True, append_images=images[1:], loop=0, duration=duration)
            print(f"GIF criado com sucesso: {output_path}")  # Depuração
            return True
        except Exception as e:
            print(f"Erro ao criar o GIF: {e}")
    return False

@app.route('/')
def home():
    return "Bem-vindo ao Maigret Flask Backend! Use /search?username=SEU_USERNAME para pesquisar."

@app.route('/search', methods=['GET'])
def search():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "O parâmetro 'username' é obrigatório."}), 400

    try:
        # Executa o maigret para verificar todos os sites
        result = subprocess.run(
            ["maigret", username, "-J", "simple"],  # Verifica todos os sites
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

        # Depuração: Imprime o JSON completo no console
        print("JSON gerado pelo Maigret:", json.dumps(json_result, indent=2))

        # Processa o JSON para extrair url_user e image
        results = []  # Lista para armazenar os resultados
        image_urls = []  # Lista para armazenar URLs das imagens

        for site, data in json_result.items():
            if data.get("url_user"):  # Verifica se a URL do usuário existe
                image_url = data.get("status", {}).get("ids", {}).get("image")
                if image_url:  # Adiciona apenas se a imagem existir
                    image_urls.append(image_url)
                    print(f"Imagem encontrada para {site}: {image_url}")  # Depuração
                results.append({
                    "site": site,
                    "url_user": data["url_user"],
                    "image": image_url
                })

        # Depuração: Imprime a lista de URLs de imagens
        print("URLs de imagens encontradas:", image_urls)

        # Cria o GIF a partir das imagens
        gif_path = f"reports/{username}_profile.gif"
        if create_gif(image_urls, gif_path):
            # Retorna o JSON com os resultados e o link para o GIF
            response_data = {
                "statusCode": 200,
                "result": results,  # Lista de sites com url_user e image
                "gif_url": f"/download-gif/{username}"  # Link para baixar o GIF
            }
            return jsonify(response_data)
        else:
            return jsonify({"error": "Nenhuma imagem encontrada para criar o GIF."}), 404

    except subprocess.CalledProcessError as e:
        print("Erro ao executar maigret:", e.stderr)  # Depuração
        return jsonify({"error": f"Erro ao executar maigret: {e.stderr}"}), 500
    except json.JSONDecodeError as e:
        print("Erro ao processar o JSON:", str(e))  # Depuração
        return jsonify({"error": f"Erro ao processar o resultado do maigret: {str(e)}"}), 500
    except Exception as e:
        print("Erro inesperado:", str(e))  # Depuração
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

@app.route('/download-gif/<username>', methods=['GET'])
def download_gif(username):
    """Rota para baixar o GIF gerado."""
    gif_path = f"reports/{username}_profile.gif"
    if os.path.exists(gif_path):
        return send_file(gif_path, mimetype='image/gif', as_attachment=True, download_name=f"{username}_profile.gif")
    else:
        return jsonify({"error": "GIF não encontrado."}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)