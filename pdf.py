from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from PIL import Image
from typing import List, Tuple

def create_crossword_pdf(image_path: str, clues_path: str, output_pdf_path: str) -> None:
    # Load clues
    with open(clues_path, 'r', encoding='utf-8') as f:
        clues_text = f.read()

    across_clues, down_clues = parse_clues(clues_text)

    # Create PDF
    width, height = A4
    c = canvas.Canvas(output_pdf_path, pagesize=A4)

    # Estimate space needed for clues
    clues_height = estimate_clues_height(c, across_clues, down_clues, (width - 30*mm) / 2)

    # Calculate image height based on available space
    img = Image.open(image_path)
    img_width, img_height = img.size

    # Adjust image size to fit everything on one page
    scale_factor = min(width / img_width, (height - clues_height - 20*mm) / img_height)
    new_img_width = img_width * scale_factor
    new_img_height = img_height * scale_factor

    # Draw the crossword grid
    c.drawImage(image_path, (width - new_img_width) / 2, height - new_img_height,
                width=new_img_width, height=new_img_height)

    # Draw horizontal separator
    separator_y = height - new_img_height - 5*mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(10*mm, separator_y, width - 10*mm, separator_y)

    # Create side-by-side clues layout
    clues_y = separator_y - 10*mm
    column_width = (width - 30*mm) / 2

    # Draw clues
    draw_clues_section(c, "Across", across_clues, 10*mm, clues_y, column_width)
    draw_clues_section(c, "Down", down_clues, 20*mm + column_width, clues_y, column_width)

    c.save()
    print(f"PDF created successfully at {output_pdf_path}")

def parse_clues(clues_text: str) -> Tuple[List[str], List[str]]:
    sections = clues_text.split("\n\n")
    across_clues: List[str] = []
    down_clues: List[str] = []

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split("\n")
        if not lines:
            continue

        if "across" in lines[0].lower():
            across_clues = lines[1:] if len(lines) > 1 else []
        elif "down" in lines[0].lower():
            down_clues = lines[1:] if len(lines) > 1 else []

    return across_clues, down_clues

def estimate_clues_height(c: canvas.Canvas, across_clues: List[str],
                          down_clues: List[str], column_width: float) -> float:
    font_size = 11
    line_height = font_size * 1.2
    title_height = 20  # Space for title and padding

    # Estimate height for across clues
    across_height = title_height
    for clue in across_clues:
        words = clue.split()
        current_line = ""
        line_count = 1

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if c.stringWidth(test_line, "Helvetica", font_size) < column_width:
                current_line = test_line
            else:
                line_count += 1
                current_line = word

        across_height += line_count * line_height + 3  # 3 points padding between clues

    # Estimate height for down clues
    down_height = title_height
    for clue in down_clues:
        words = clue.split()
        current_line = ""
        line_count = 1

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if c.stringWidth(test_line, "Helvetica", font_size) < column_width:
                current_line = test_line
            else:
                line_count += 1
                current_line = word

        down_height += line_count * line_height + 3  # 3 points padding between clues

    return max(across_height, down_height)

def draw_clues_section(c: canvas.Canvas, title: str, clues: List[str],
                       x: float, y: float, width: float) -> None:
    text_object = c.beginText(x, y)
    text_object.setFont("Helvetica-Bold", 12)
    text_object.textLine(title)
    text_object.setFont("Helvetica", 11)
    text_object.moveCursor(0, 5)

    for line in clues:
        words = line.split()
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if c.stringWidth(test_line, "Helvetica", 11) < width:
                current_line = test_line
            else:
                text_object.textLine(current_line)
                current_line = word

        if current_line:
            text_object.textLine(current_line)

        text_object.moveCursor(0, 3)

    c.drawText(text_object)

if __name__ == "__main__":
    default_image_path = "output/crossword_puzzle_question.png"
    default_clues_path = "output/crossword_clues.txt"
    default_output_pdf_path = "output/puzzle.pdf"
    create_crossword_pdf(default_image_path, default_clues_path, default_output_pdf_path)
