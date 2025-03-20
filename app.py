from flask import Flask, request, jsonify, send_file
import subprocess
import json
import os
import sys
from io import BytesIO

sys.setrecursionlimit(1500)

try:
    import requests
    from PIL import Image
    import imageio
except ImportError as e:
    print(f"Erro: {e}. Instale as dependências necessárias.")
    sys.exit(1)

app = Flask(__name__)
os.makedirs("reports", exist_ok=True)

def download_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Erro ao baixar a imagem {url}: {e}")
    return None

def resize_and_center_image(img, target_size=(150, 150)):
    img.thumbnail(target_size, Image.LANCZOS)
    new_img = Image.new("RGB", target_size, (255, 255, 255))
    paste_x = (target_size[0] - img.size[0]) // 2
    paste_y = (target_size[1] - img.size[1]) // 2
    new_img.paste(img, (paste_x, paste_y))
    return new_img

def create_gif(image_urls, output_path, duration=500, target_size=(150, 150)):
    images = []
    for url in image_urls:
        img = download_image(url)
        if img:
            img_resized = resize_and_center_image(img, target_size)
            images.append(img_resized)
    
    if images:
        try:
            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:],
                loop=0,
                duration=duration,
                optimize=True,
            )
            return True
        except Exception as e:
            print(f"Erro ao criar o GIF: {e}")
    return False

@app.route('/search', methods=['GET'])
def search():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "O parâmetro 'username' é obrigatório."}), 400

    try:
        result = subprocess.run([
            "maigret", username, "-J", "simple"], capture_output=True, text=True, check=True)
        json_file_path = f"reports/report_{username}_simple.json"

        if not os.path.exists(json_file_path):
            return jsonify({"error": "Arquivo JSON não encontrado."}), 500

        with open(json_file_path, "r") as file:
            json_result = json.load(file)

        results = []
        image_urls = []
        for site, data in json_result.items():
            if data.get("url_user"):
                image_url = data.get("status", {}).get("ids", {}).get("image")
                if image_url:
                    image_urls.append(image_url)
                results.append({
                    "site": site,
                    "url_user": data["url_user"],
                    "image": image_url
                })

        gif_path = f"reports/{username}_profile.gif"
        if create_gif(image_urls, gif_path):
            return jsonify({
                "statusCode": 200,
                "result": results,
                "gif_url": f"/download-gif/{username}"
            })
        else:
            return jsonify({"error": "Nenhuma imagem encontrada para criar o GIF."}), 404

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Erro ao executar maigret: {e.stderr}"}), 500
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Erro ao processar o resultado do maigret: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

@app.route('/download-gif/<username>', methods=['GET'])
def download_gif(username):
    gif_path = f"reports/{username}_profile.gif"
    if os.path.exists(gif_path):
        return send_file(gif_path, mimetype='image/gif', as_attachment=True, download_name=f"{username}_profile.gif")
    else:
        return jsonify({"error": "GIF não encontrado."}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
