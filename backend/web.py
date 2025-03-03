import os
from flask import Flask, request, render_template, jsonify, send_file, Response
from typing import Dict
import base64
import tomllib as toml
from generator import CrosswordGenerator
import json

app = Flask(__name__, static_folder='../frontend/build')

# Store generators by UUID
generators: Dict[str, CrosswordGenerator] = {}

# Load default configuration
CONFIG_PATH = "config.toml"
config = {}
try:
    with open(CONFIG_PATH, "rb") as config_file:
        config = toml.load(config_file)
except (toml.TOMLDecodeError, OSError) as e:
    print(f"Error reading config file: {e}")

# Verify secret keys are configured
if not config.get("web", {}).get("secret", ""):
    print("Warning: No secret keys configured in config.toml")
    config["web"]["secret"] = []


def require_secret_key(f):
    """Decorator to verify X-Secret-Key header."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        secret_key = request.headers.get('X-Secret-Key')
        if not secret_key or secret_key not in config["web"]["secret"]:
            print(
                f"received secret {secret_key}, acceptable: {config["web"]["secret"]}")
            return jsonify({
                'success': False,
                'message': 'Invalid or missing X-Secret-Key header'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


# Ensure output directory exists
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route('/api/generate_grid', methods=['POST'])
@require_secret_key
def generate_grid():
    """Generate a crossword grid from the provided words."""
    data = request.json
    words = [word.strip()
             for word in data['words'].split('\n') if word.strip()]
    client_id = data['clientId']

    # Create or get the generator for this client
    if client_id not in generators:
        generators[client_id] = CrosswordGenerator(words)
    else:
        # Update words for existing generator
        generators[client_id].words = list(set(words))
        generators[client_id].grid = {}
        generators[client_id].placed_words = []
        generators[client_id].overlap_count = 0
        generators[client_id].clue_ids = {'across': {}, 'down': {}}
        generators[client_id].clues = {'across': {}, 'down': {}}

    generator = generators[client_id]

    # Generate the grid
    max_attempts = int(data.get('maxAttempts', 30))
    success = generator.generate_grid(max_attempts=max_attempts)

    if not success:
        return jsonify({
            'success': False,
            'message': 'Failed to generate grid with all words.'
        })

    # Generate images
    temp_output_dir = os.path.join(OUTPUT_DIR, client_id)
    os.makedirs(temp_output_dir, exist_ok=True)

    generator.draw_grid(answer=False, output_dir=temp_output_dir)
    generator.draw_grid(answer=True, output_dir=temp_output_dir)

    # Read the image file and convert to base64
    with open(f'{temp_output_dir}/crossword_puzzle_question.png', 'rb') as img_file:
        question_img_data = base64.b64encode(img_file.read()).decode('utf-8')

    with open(f'{temp_output_dir}/crossword_puzzle_answer.png', 'rb') as img_file:
        answer_img_data = base64.b64encode(img_file.read()).decode('utf-8')

    # Generate clue structure without actual clues
    clues_structure = {
        'across': {},
        'down': {}
    }

    for direction in ['across', 'down']:
        for number, word in generator.clue_ids[direction].items():
            clues_structure[direction][number] = {
                'word': word,
                'clue': f"({len(word)}) Enter clue for {word}"
            }

    return jsonify({
        'success': True,
        'questionImage': question_img_data,
        'answerImage': answer_img_data,
        'cluesStructure': clues_structure
    })



@app.route('/api/stream_clues', methods=['GET'])
def stream_clues():
    """Stream clue generation progress using SSE."""
    client_id = request.args.get('clientId')
    secret_key = request.args.get('secret')

    # Verify secret key
    if not secret_key or secret_key not in config["web"]["secret"]:
        def error_stream_secret():
            yield 'data: ' + json.dumps({
                'error': 'Invalid or missing secret key'
            }) + '\n\n'
        return Response(error_stream_secret(), mimetype='text/event-stream')

    # verify requisite files (puzzle and answer image) were generated
    temp_output_dir = os.path.join(OUTPUT_DIR, client_id)
    if not os.path.exists(f"{temp_output_dir}/crossword_puzzle_question.png") or not os.path.exists(f"{temp_output_dir}/crossword_puzzle_answer.png"):
        def error_stream_clientid():
            yield 'data: ' + json.dumps({
                'error': 'No grid found. Please generate a grid first.'
            }) + '\n\n'
        return Response(error_stream_clientid(), mimetype='text/event-stream')

    generator = generators[client_id]
    api_address = config.get("api", {}).get("address")
    api_secret = config.get("api", {}).get("secret")
    model_id = config.get("api", {}).get("model_id")

    def generate():
        try:
            total_words = len(
                generator.clue_ids['across']) + len(generator.clue_ids['down'])
            current_word = 0

            # Initialize clues dictionaries
            generator.clues = {'across': {}, 'down': {}}

            # Generate clues with progress updates
            for direction in ['across', 'down']:
                for number, word in generator.clue_ids[direction].items():
                    current_word += 1
                    progress = (current_word / total_words) * 100

                    # Generate clue for current word
                    clue = generator.generate_single_clue(
                        word, api_address, api_secret, model_id)
                    generator.clues[direction][number] = clue

                    # Send progress update
                    yield 'data: ' + json.dumps({
                        'progress': progress,
                        'currentWord': word,
                        'direction': direction,
                        'number': number,
                        'clue': clue
                    }) + '\n\n'

            # Save clues to text file
            temp_output_dir = os.path.join(OUTPUT_DIR, client_id)
            os.makedirs(temp_output_dir, exist_ok=True)
            generator.save_clues_text(temp_output_dir)

            # Send completion message
            yield 'data: ' + json.dumps({
                'complete': True,
                'clues': {
                    'across': {str(k): {'word': generator.clue_ids['across'][k], 'clue': v}
                               for k, v in generator.clues['across'].items()},
                    'down': {str(k): {'word': generator.clue_ids['down'][k], 'clue': v}
                             for k, v in generator.clues['down'].items()}
                }
            }) + '\n\n'

        except (ConnectionError, TimeoutError, ValueError, KeyError) as e:
            yield 'data: ' + json.dumps({
                'error': str(e)
            }) + '\n\n'

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/update_clues', methods=['POST'])
@require_secret_key
def update_clues():
    """Update clues with user-edited versions."""
    data = request.json
    client_id = data['clientId']
    clues_data = data['clues']

    if client_id not in generators:
        return jsonify({
            'success': False,
            'message': 'No grid found. Please generate a grid first.'
        })

    generator = generators[client_id]

    # Update clues in the generator
    for direction in ['across', 'down']:
        for number_str, clue_info in clues_data[direction].items():
            number = int(number_str)
            generator.clues[direction][number] = clue_info['clue']

    # Save updated clues
    temp_output_dir = os.path.join(OUTPUT_DIR, client_id)
    os.makedirs(temp_output_dir, exist_ok=True)
    generator.save_clues_text(temp_output_dir)

    return jsonify({
        'success': True,
        'message': 'Clues updated successfully'
    })


@app.route('/api/export_pdf', methods=['POST'])
@require_secret_key
def export_pdf():
    """Create and return PDF files for the crossword."""
    data = request.json
    client_id = data['clientId']
    temp_output_dir = os.path.join(OUTPUT_DIR, client_id)

    # check prerequisite files exist
    if not os.path.exists(f"{temp_output_dir}/crossword_puzzle_question.png"):
        return jsonify({
            'success': False,
            'message': 'Question image not found. Please generate a grid first.'
        })
    if not os.path.exists(f"{temp_output_dir}/crossword_puzzle_answer.png"):
        return jsonify({
            'success': False,
            'message': 'Answer image not found. Please generate a grid first.'
        })
    if not os.path.exists(f"{temp_output_dir}/crossword_clues.txt"):
        return jsonify({
            'success': False,
            'message': 'Clues file not found. Please generate clues first.'
        })

    # Create PDFs
    from generator import create_crossword_pdf

    create_crossword_pdf(
        image_path=f"{temp_output_dir}/crossword_puzzle_question.png",
        clues_path=f"{temp_output_dir}/crossword_clues.txt",
        output_pdf_path=f"{temp_output_dir}/crossword_puzzle.pdf"
    )

    create_crossword_pdf(
        image_path=f"{temp_output_dir}/crossword_puzzle_answer.png",
        clues_path=f"{temp_output_dir}/crossword_clues.txt",
        output_pdf_path=f"{temp_output_dir}/crossword_puzzle_answer.pdf"
    )

    return jsonify({
        'success': True,
        'message': 'PDFs created successfully',
        'questionPdfUrl': f'/api/download_pdf/{client_id}/question',
        'answerPdfUrl': f'/api/download_pdf/{client_id}/answer'
    })


@app.route('/api/download_pdf/<client_id>/<pdf_type>', methods=['GET'])
def download_pdf(client_id, pdf_type):
    """Download the generated PDF files."""
    temp_output_dir = os.path.join(OUTPUT_DIR, client_id)

    if pdf_type == 'question':
        pdf_path = f"{temp_output_dir}/crossword_puzzle.pdf"
        filename = "crossword_puzzle.pdf"
    elif pdf_type == 'answer':
        pdf_path = f"{temp_output_dir}/crossword_puzzle_answer.pdf"
        filename = "crossword_puzzle_answer.pdf"
    else:
        return "Invalid PDF type", 400

    if not os.path.exists(pdf_path):
        return "PDF not found", 404

    return send_file(pdf_path, as_attachment=True, download_name=filename)


@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """Clean up resources for a client session."""
    data = request.json
    client_id = data['clientId']

    if client_id in generators:
        del generators[client_id]

    temp_output_dir = os.path.join(OUTPUT_DIR, client_id)
    if os.path.exists(temp_output_dir):
        for file in os.listdir(temp_output_dir):
            os.remove(os.path.join(temp_output_dir, file))
        os.rmdir(temp_output_dir)

    return jsonify({
        'success': True,
        'message': 'Cleanup completed'
    })
    
# @app.route('/')
# def index():
#     """Render the main page."""
#     return render_template('index.html')

# Serve Svelte frontend (catch-all route)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path and (path.startswith('api') or '.' in path):
        # Let Flask handle API routes and static files
        return app.send_static_file(path)
    else:
        # For all other routes, serve index.html (SPA approach)
        return app.send_static_file('index.html')

if __name__ == '__main__':
    listen_addr = config.get("web", {}).get("listen_address", "127.0.0.1:80")
    host, port = listen_addr.split(":")
    port = int(port)
    app.run(host=host, port=port, debug=False)
