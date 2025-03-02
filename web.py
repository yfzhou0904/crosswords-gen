import os
from flask import Flask, request, render_template, jsonify, send_file
from typing import Dict
import base64
import tomllib as toml
from generator import CrosswordGenerator

app = Flask(__name__)

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

# Ensure output directory exists
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/generate_grid', methods=['POST'])
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


@app.route('/generate_clues', methods=['POST'])
def generate_clues():
    """Generate clues for the crossword using AI."""
    data = request.json
    client_id = data['clientId']

    if client_id not in generators:
        return jsonify({
            'success': False,
            'message': 'No grid found. Please generate a grid first.'
        })

    generator = generators[client_id]

    # Generate clues using API
    api_address = config.get("api", {}).get("address")
    api_secret = config.get("api", {}).get("secret")
    model_id = config.get("api", {}).get("model_id")

    if not api_address or not api_secret or not model_id:
        return jsonify({
            'success': False,
            'message': 'API credentials not available. Check your config.toml file.'
        })

    generator.generate_clues(api_address, api_secret, model_id)

    # Format clues for response
    clues_data = {
        'across': {},
        'down': {}
    }

    for direction in ['across', 'down']:
        for number, word in generator.clue_ids[direction].items():
            clue = generator.clues[direction].get(
                number, f"({len(word)}) Enter clue for {word}")
            clues_data[direction][number] = {
                'word': word,
                'clue': clue
            }

    # Save clues to text file
    temp_output_dir = os.path.join(OUTPUT_DIR, client_id)
    os.makedirs(temp_output_dir, exist_ok=True)
    generator.save_clues_text(temp_output_dir)

    return jsonify({
        'success': True,
        'clues': clues_data
    })


@app.route('/update_clues', methods=['POST'])
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


@app.route('/export_pdf', methods=['POST'])
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
        'questionPdfUrl': f'/download_pdf/{client_id}/question',
        'answerPdfUrl': f'/download_pdf/{client_id}/answer'
    })


@app.route('/download_pdf/<client_id>/<pdf_type>', methods=['GET'])
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


@app.route('/cleanup', methods=['POST'])
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


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    # Create the HTML template
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crossword Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        .input-section {
            flex: 1;
            min-width: 300px;
        }
        .output-section {
            flex: 2;
            min-width: 500px;
        }
        textarea {
            width: 100%;
            min-height: 200px;
            margin-bottom: 10px;
            padding: 8px;
        }
        button {
            padding: 10px 15px;
            margin-right: 10px;
            margin-bottom: 10px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .image-container {
            margin-top: 20px;
            text-align: center;
        }
        .image-container img {
            max-width: 100%;
            border: 1px solid #ddd;
        }
        .clues-container {
            margin-top: 20px;
        }
        .clues-editor {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        .clue-column {
            flex: 1;
            min-width: 300px;
        }
        .clue-item {
            margin-bottom: 10px;
        }
        .clue-input {
            width: 100%;
            padding: 8px;
        }
        .tabs {
            display: flex;
            margin-bottom: 10px;
        }
        .tab {
            padding: 10px 15px;
            cursor: pointer;
            background-color: #f1f1f1;
            border: 1px solid #ddd;
            border-bottom: none;
        }
        .tab.active {
            background-color: white;
            border-bottom: 1px solid white;
        }
        .tab-content {
            display: none;
            padding: 15px;
            border: 1px solid #ddd;
        }
        .tab-content.active {
            display: block;
        }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <h1>Crossword Generator</h1>

    <div class="container">
        <div class="input-section">
            <h2>Input Words</h2>
            <p>Enter one word per line:</p>
            <textarea id="wordsInput" placeholder="Enter words here, one per line..."></textarea>

            <button id="generateGridBtn">Generate Grid</button>
            <button id="generateCluesBtn" disabled>Generate Clues</button>
            <button id="exportPdfBtn" disabled>Export PDF</button>
        </div>

        <div class="output-section">
            <div class="tabs">
                <div class="tab active" data-tab="grid">Puzzle</div>
                <div class="tab" data-tab="answer">Answer</div>
                <div class="tab" data-tab="clues">Clues</div>
            </div>

            <div class="tab-content active" id="gridTab">
                <div class="image-container">
                    <img id="gridImage" src="" alt="Crossword grid will appear here" style="display: none;">
                    <p id="gridMessage">Generate a grid to see the crossword puzzle.</p>
                </div>
            </div>

            <div class="tab-content" id="cluesTab">
                <div class="clues-container">
                    <div class="clues-editor">
                        <div class="clue-column">
                            <h3>Across</h3>
                            <div id="acrossClues"></div>
                        </div>
                        <div class="clue-column">
                            <h3>Down</h3>
                            <div id="downClues"></div>
                        </div>
                    </div>
                    <button id="updateCluesBtn" style="display: none;">Update Clues</button>
                </div>
            </div>

            <div class="tab-content" id="answerTab">
                <div class="image-container">
                    <img id="answerImage" src="" alt="Answer grid will appear here" style="display: none;">
                    <p id="answerMessage">Generate a grid to see the answer.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Generate a UUID for this session
        function generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        const clientId = generateUUID();
        let cluesData = null;

        // Tab functionality
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

                tab.classList.add('active');
                document.getElementById(tab.dataset.tab + 'Tab').classList.add('active');
            });
        });

        // Generate Grid
        document.getElementById('generateGridBtn').addEventListener('click', async function() {
            const wordsInput = document.getElementById('wordsInput').value.trim();

            if (!wordsInput) {
                alert('Please enter at least one word.');
                return;
            }

            // Show loading state
            const originalText = this.textContent;
            this.innerHTML = '<span class="spinner"></span> Generating...';
            this.disabled = true;

            try {
                const response = await fetch('/generate_grid', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        words: wordsInput,
                        clientId: clientId,
                        maxAttempts: 30
                    }),
                });

                const data = await response.json();

                if (data.success) {
                    // Update grid image
                    const gridImage = document.getElementById('gridImage');
                    gridImage.src = 'data:image/png;base64,' + data.questionImage;
                    gridImage.style.display = 'block';
                    document.getElementById('gridMessage').style.display = 'none';

                    // Update answer image
                    const answerImage = document.getElementById('answerImage');
                    answerImage.src = 'data:image/png;base64,' + data.answerImage;
                    answerImage.style.display = 'block';
                    document.getElementById('answerMessage').style.display = 'none';

                    // Enable generate clues button
                    document.getElementById('generateCluesBtn').disabled = false;

                    // Store clues structure
                    cluesData = data.cluesStructure;

                    // Populate clues with placeholders
                    populateCluesEditor(cluesData);
                    document.getElementById('updateCluesBtn').style.display = 'block';
                } else {
                    alert(data.message || 'Failed to generate grid.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            } finally {
                // Restore button state
                this.innerHTML = originalText;
                this.disabled = false;
            }
        });

        // Generate Clues
        document.getElementById('generateCluesBtn').addEventListener('click', async function() {
            // Show loading state
            const originalText = this.textContent;
            this.innerHTML = '<span class="spinner"></span> Generating...';
            this.disabled = true;

            try {
                const response = await fetch('/generate_clues', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        clientId: clientId
                    }),
                });

                const data = await response.json();

                if (data.success) {
                    // Update clues
                    cluesData = data.clues;
                    populateCluesEditor(cluesData);
                    document.getElementById('updateCluesBtn').style.display = 'block';

                    // Enable export button
                    document.getElementById('exportPdfBtn').disabled = false;

                    // Switch to clues tab
                    document.querySelector('.tab[data-tab="clues"]').click();
                } else {
                    alert(data.message || 'Failed to generate clues.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            } finally {
                // Restore button state
                this.innerHTML = originalText;
                this.disabled = false;
            }
        });

        // Update Clues
        document.getElementById('updateCluesBtn').addEventListener('click', async function() {
            // Collect all clues from the editor
            const updatedClues = {
                across: {},
                down: {}
            };

            document.querySelectorAll('#acrossClues .clue-item').forEach(item => {
                const number = item.dataset.number;
                const word = item.dataset.word;
                const clue = item.querySelector('input').value;
                updatedClues.across[number] = { word, clue };
            });

            document.querySelectorAll('#downClues .clue-item').forEach(item => {
                const number = item.dataset.number;
                const word = item.dataset.word;
                const clue = item.querySelector('input').value;
                updatedClues.down[number] = { word, clue };
            });

            // Show loading state
            const originalText = this.textContent;
            this.innerHTML = '<span class="spinner"></span> Updating...';
            this.disabled = true;

            try {
                const response = await fetch('/update_clues', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        clientId: clientId,
                        clues: updatedClues
                    }),
                });

                const data = await response.json();

                if (data.success) {
                    alert('Clues updated successfully.');

                    // Enable export button
                    document.getElementById('exportPdfBtn').disabled = false;
                } else {
                    alert(data.message || 'Failed to update clues.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            } finally {
                // Restore button state
                this.innerHTML = originalText;
                this.disabled = false;
            }
        });

        // Export PDF
        document.getElementById('exportPdfBtn').addEventListener('click', async function() {
            // Show loading state
            const originalText = this.textContent;
            this.innerHTML = '<span class="spinner"></span> Exporting...';
            this.disabled = true;

            try {
                const response = await fetch('/export_pdf', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        clientId: clientId
                    }),
                });

                const data = await response.json();

                if (data.success) {
                    // Download the PDFs
                    window.open(data.questionPdfUrl, '_blank');
                    window.open(data.answerPdfUrl, '_blank');
                } else {
                    alert(data.message || 'Failed to export PDFs.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            } finally {
                // Restore button state
                this.innerHTML = originalText;
                this.disabled = false;
            }
        });

        // Helper function to populate clues editor
        function populateCluesEditor(clues) {
            const acrossContainer = document.getElementById('acrossClues');
            const downContainer = document.getElementById('downClues');

            acrossContainer.innerHTML = '';
            downContainer.innerHTML = '';

            // Sort numbers numerically
            const sortedAcross = Object.keys(clues.across).sort((a, b) => parseInt(a) - parseInt(b));
            const sortedDown = Object.keys(clues.down).sort((a, b) => parseInt(a) - parseInt(b));

            // Populate across clues
            sortedAcross.forEach(number => {
                const word = clues.across[number].word;
                const clue = clues.across[number].clue;

                const clueItem = document.createElement('div');
                clueItem.className = 'clue-item';
                clueItem.dataset.number = number;
                clueItem.dataset.word = word;

                clueItem.innerHTML = `
                    <label>${number}. (${word.length}) ${word}</label>
                    <input type="text" class="clue-input" value="${clue}">
                `;

                acrossContainer.appendChild(clueItem);
            });

            // Populate down clues
            sortedDown.forEach(number => {
                const word = clues.down[number].word;
                const clue = clues.down[number].clue;

                const clueItem = document.createElement('div');
                clueItem.className = 'clue-item';
                clueItem.dataset.number = number;
                clueItem.dataset.word = word;

                clueItem.innerHTML = `
                    <label>${number}. (${word.length}) ${word}</label>
                    <input type="text" class="clue-input" value="${clue}">
                `;

                downContainer.appendChild(clueItem);
            });
        }

        // Clean up resources when the page is closed or refreshed
        window.addEventListener('beforeunload', async () => {
            try {
                await fetch('/cleanup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        clientId: clientId
                    }),
                    keepalive: true
                });
            } catch (error) {
                console.error('Error during cleanup:', error);
            }
        });
    </script>
</body>
</html>
        ''')

    app.run(host='0.0.0.0', port=81, debug=False)
