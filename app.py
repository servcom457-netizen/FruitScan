
import os
import json
import base64
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.get("/")
def home():
    return jsonify({
        "app": "FruitScan AI V3",
        "status": "online"
    })

@app.post("/identify")
def identify():
    if "image" not in request.files:
        return jsonify({"error": "Aucune image reçue"}), 400

    image = request.files["image"]
    mime = image.mimetype or ""

    if mime not in ["image/jpeg", "image/png", "image/webp"]:
        return jsonify({"error": "Format JPG, PNG ou WEBP requis"}), 400

    raw = image.read()
    if not raw:
        return jsonify({"error": "Image vide"}), 400

    encoded = base64.b64encode(raw).decode("utf-8")
    image_url = f"data:{mime};base64,{encoded}"

    prompt = """
Identifie le fruit visible sur cette photo, en tenant compte
des fruits courants en Haïti.

Réponds uniquement avec un JSON valide contenant :
name_fr, name_local, name_en, confidence, visual_evidence,
alternatives, nutrition, benefits, caution, limitations.

nutrition doit contenir :
note, calories, carbohydrates, fiber, protein, fat,
vitamin_c, potassium.

Donne des estimations nutritionnelles approximatives pour 100 g
de fruit comestible, avec unités. Mentionne les incertitudes.
Si aucun fruit ne peut être identifié, dis-le clairement.
N'invente pas de certitude ni de données nutritionnelles exactes.
"""

    try:
        response = client.responses.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": image_url,
                        "detail": "low"
                    }
                ]
            }]
        )

        result = json.loads(response.output_text)
        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({"error": "Réponse IA illisible"}), 502
    except Exception:
        app.logger.exception("Erreur d'identification")
        return jsonify({
            "error": "Échec de l'analyse. Vérifie la configuration du serveur."
        }), 502

@app.errorhandler(413)
def too_large(error):
    return jsonify({"error": "Image trop volumineuse"}), 413
