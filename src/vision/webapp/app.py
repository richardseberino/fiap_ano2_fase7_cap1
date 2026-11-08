import os
import time
import io
import base64
import numpy as np
from flask import Flask, request, render_template, jsonify
from tensorflow import keras
from PIL import Image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB

MODEL_PATH = os.getenv('MODEL_PATH', os.path.join(os.path.dirname(__file__), '..', 'cnn_ecg_model.keras'))
IMG_SIZE = (224, 224)
CLASSES = ['anormal', 'hist_inf_mio', 'inf_mio', 'normal']
CLASS_LABELS = {
    'anormal':      'Anormal',
    'hist_inf_mio': 'Histórico de Infarto do Miocárdio',
    'inf_mio':      'Infarto do Miocárdio',
    'normal':       'Normal',
}
CLASS_COLORS = {
    'anormal':      '#e74c3c',
    'hist_inf_mio': '#e67e22',
    'inf_mio':      '#c0392b',
    'normal':       '#27ae60',
}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}

print("Carregando modelo...")
model = keras.models.load_model(MODEL_PATH)
print("Modelo carregado.")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def preprocess(file_bytes):
    img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
    img = img.resize(IMG_SIZE, Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)


CLASS_DESCRIPTIONS = {
    'anormal':      'Padrão de batimentos cardíacos anormais (arritmia). Recomenda-se avaliação cardiológica.',
    'hist_inf_mio': 'Sinais compatíveis com infarto do miocárdio prévio. Acompanhamento cardiológico indicado.',
    'inf_mio':      'Padrão compatível com infarto do miocárdio em curso. Procure atendimento de emergência (192).',
    'normal':       'Traçado sem alterações relevantes segundo o modelo.',
}
CLASS_SEVERITY = {'normal': 'BAIXO', 'hist_inf_mio': 'MODERADO', 'anormal': 'ALTO', 'inf_mio': 'CRITICO'}


def classify(file_bytes):
    """Executa o modelo e devolve as classes ordenadas pela probabilidade."""
    probs = model.predict(preprocess(file_bytes), verbose=0)[0]
    results = sorted(
        [
            {
                'class': cls,
                'label': CLASS_LABELS[cls],
                'color': CLASS_COLORS[cls],
                'probability': float(probs[i]),
                'percent': f'{probs[i] * 100:.1f}',
            }
            for i, cls in enumerate(CLASSES)
        ],
        key=lambda x: x['probability'],
        reverse=True,
    )
    return results


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'servico': 'vision', 'modelo': 'CNN ECG (4 classes)', 'classes': CLASSES})


@app.route('/api/predict', methods=['POST'])
def api_predict():
    """API JSON consumida pelo gateway e pelo app móvel (multipart, campo `image`)."""
    file = request.files.get('image')
    if file is None or file.filename == '':
        return jsonify({'error': 'Envie a imagem no campo multipart "image".'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Formato não suportado. Use PNG, JPG, BMP, TIFF ou WEBP.'}), 415
    file_bytes = file.read()
    inicio = time.perf_counter()
    try:
        results = classify(file_bytes)
    except Exception:
        return jsonify({'error': 'Não foi possível processar a imagem. Verifique o arquivo.'}), 422
    top = results[0]
    return jsonify({
        'classe': top['class'],
        'rotulo': top['label'],
        'confianca': top['probability'],
        'severidade': CLASS_SEVERITY[top['class']],
        'descricao': CLASS_DESCRIPTIONS[top['class']],
        'probabilidades': [
            {'classe': r['class'], 'rotulo': r['label'], 'probabilidade': r['probability'], 'cor': r['color']}
            for r in results
        ],
        'duracao_ms': int((time.perf_counter() - inicio) * 1000),
        'aviso': 'Resultado de modelo acadêmico de visão computacional. Não substitui laudo médico.',
    })


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return render_template('index.html', error='Nenhuma imagem enviada.')

    file = request.files['image']
    if file.filename == '':
        return render_template('index.html', error='Nenhum arquivo selecionado.')

    if not allowed_file(file.filename):
        return render_template('index.html', error='Formato não suportado. Use PNG, JPG, BMP ou TIFF.')

    file_bytes = file.read()

    try:
        results = classify(file_bytes)
    except Exception:
        return render_template('index.html', error='Não foi possível processar a imagem. Verifique o arquivo.')

    predicted_class = results[0]['class']

    mime = file.content_type or 'image/jpeg'
    image_data = f"data:{mime};base64,{base64.b64encode(file_bytes).decode()}"

    return render_template(
        'index.html',
        results=results,
        predicted_class=predicted_class,
        predicted_label=CLASS_LABELS[predicted_class],
        predicted_color=CLASS_COLORS[predicted_class],
        confidence=results[0]['percent'],
        image_data=image_data,
        filename=file.filename,
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
