from flask import Flask, request, jsonify
import subprocess
import json
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests
from PIL import Image
from io import BytesIO
import cv2  # Importa o OpenCV (headless)
import numpy as npCLOUDINARY_API_KEY

# Configura o Cloudinary
cloudinary.config(
    cloud_name="CLOUDINARY_CLOUD_NAME",
    api_key="CLOUDINARY_API_KEY",
    api_secret="CLOUDINARY_API_SECRET-Z0Kb-sHE"
)

app = Flask(__name__)

# URL da imagem fixa (Display Name borrada) no Cloudinary
FIXED_IMAGE_PUBLIC_ID = "maigret_gifs/vi2yk0cklersjy7bnagp"
FIXED_IMAGE_URL = cloudinary.utils.cloudinary_url(FIXED_IMAGE_PUBLIC_ID)[0]

# Carrega o classificador Haar Cascade para detecção de rostos
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
if face_cascade.empty():
    raise Exception("Erro: Não foi possível carregar o classificador Haar Cascade. Verifique a instalação do OpenCV.")

def resize_image(img, target_size=(70, 70)):
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    img.thumbnail(target_size, Image.Resampling.LANCZOS)
    
    new_img = Image.new("RGB", target_size, (255, 255, 255))
    new_img.paste(
        img,
        (
            (target_size[0] - img.size[0]) // 2,
            (target_size[1] - img.size[1]) // 2
        ),
    )
    return new_img

def upload_image_to_cloudinary(image):
    try:
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        response = cloudinary.uploader.upload(img_byte_arr, folder="maigret_gifs")
        return response["secure_url"]
    except Exception as e:
        print(f"Erro ao enviar imagem para o Cloudinary: {e}")
        return None

def has_face(image):
    """
    Verifica se a imagem contém um rosto humano usando OpenCV Haar Cascade com rigor mínimo.
    """
    try:
        img_rgb = np.array(image.convert("RGB"))
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        faces = face_cascade.detectMultiScale(
            img_gray,
            scaleFactor=1.01,  # Quase não reduz escala, muito permissivo
            minNeighbors=0,    # Sem exigência de vizinhos, aceita qualquer detecção
            minSize=(5, 5)     # Aceita rostos minúsculos
        )
        print(f"Detectados {len(faces)} rostos na imagem")  # Depuração
        return len(faces) > 0
    except Exception as e:
        print(f"Erro ao detectar rosto: {e}")
        return False

def create_gif(image_urls, username, duration=1000):
    """
    Cria um GIF com imagens que têm rostos ou retorna a imagem fixa se nenhuma for encontrada.
    """
    try:
        uploaded_images = []
        for url in image_urls:
            print(f"Baixando e redimensionando imagem: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                if has_face(img):
                    img_resized = resize_image(img, target_size=(70, 70))
                    img_url = upload_image_to_cloudinary(img_resized)
                    if img_url:
                        uploaded_images.append(img_url)
                        print(f"Imagem com rosto enviada com sucesso: {img_url}")
                    else:
                        print(f"Falha ao enviar imagem com rosto: {url}")
                else:
                    print(f"Imagem sem rosto descartada: {url}")
            else:
                print(f"Erro ao baixar imagem: {url}")
        
        # Se houver imagens com rostos, cria o GIF com a imagem fixa no final
        if uploaded_images:
            uploaded_images.append(FIXED_IMAGE_URL)
            print(f"Imagem fixa adicionada ao GIF: {FIXED_IMAGE_URL}")
            response = cloudinary.uploader.multi(
                urls=uploaded_images,
                delay=duration,
                folder="maigret_gifs",
                format="gif",
                public_id=f"{username}_profile"
            )
            gif_url = response.get("secure_url")
            if gif_url:
                print(f"GIF criado com sucesso: {gif_url}")
                return gif_url
            else:
                print("Erro: URL do GIF não retornada.")
                return None
        # Se nenhuma imagem com rosto for encontrada, retorna a URL da imagem fixa
        else:
            print("Nenhuma imagem com rosto válida encontrada. Retornando imagem fixa.")
            return FIXED_IMAGE_URL
            
    except Exception as e:
        print(f"Erro ao criar o GIF no Cloudinary: {e}")
        return None

@app.route('/search', methods=['GET'])
def search():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "O parâmetro 'username' é obrigatório."}), 400

    try:
        result = subprocess.run(
            ["maigret", username, "-J", "simple"],
            capture_output=True,
            text=True,
            check=True
        )
        print("Resultado do maigret (stdout):", result.stdout)
        print("Erros do maigret (stderr):", result.stderr)

        json_file_path = f"reports/report_{username}_simple.json"

        if not os.path.exists(json_file_path):
            print("Arquivo JSON não encontrado:", json_file_path)
            return jsonify({"error": "Arquivo JSON não encontrado."}), 500

        with open(json_file_path, "r") as file:
            json_result = json.load(file)

        print("JSON gerado pelo Maigret:", json.dumps(json_result, indent=2))

        results = []
        image_urls = []

        for site, data in json_result.items():
            if data.get("url_user"):
                image_url = data.get("status", {}).get("ids", {}).get("image")
                if image_url:
                    image_urls.append(image_url)
                    print(f"Imagem encontrada para {site}: {image_url}")
                results.append({
                    "site": site,
                    "url_user": data["url_user"],
                    "image": image_url
                })

        print("URLs de imagens encontradas:", image_urls)

        gif_url = create_gif(image_urls, username)
        
        if os.path.exists(json_file_path):
            os.remove(json_file_path)
            print(f"Arquivo JSON removido: {json_file_path}")
        
        if gif_url:
            response_data = {
                "statusCode": 200,
                "result": results,
                "gif_url": gif_url  # Pode ser a URL da imagem fixa ou do GIF
            }
            return jsonify(response_data)
        else:
            return jsonify({"error": "Erro ao processar as imagens."}), 500

    except subprocess.CalledProcessError as e:
        print("Erro ao executar maigret:", e.stderr)
        return jsonify({"error": f"Erro ao executar maigret: {e.stderr}"}), 500
    except json.JSONDecodeError as e:
        print("Erro ao processar o JSON:", str(e))
        return jsonify({"error": f"Erro ao processar o resultado do maigret: {str(e)}"}), 500
    except Exception as e:
        print("Erro inesperado:", str(e))
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)