import os
from dataclasses import dataclass
import random
from typing import List, Tuple, Dict
import argparse
import tomllib as toml
import openai
from PIL import Image, ImageDraw, ImageFont
from pdf import create_crossword_pdf


@dataclass
class PlacedWord:
    """Represents a word placed on the crossword grid."""
    word: str
    row: int
    col: int
    direction: str


class CrosswordGenerator:
    """Generator for crossword puzzles from a list of words."""

    def __init__(self, words: List[str]):
        """Initialize the crossword generator with a list of words."""
        self.words: List[str] = list(set(words))  # Remove duplicates
        self.grid: Dict[Tuple[int, int], str] = {}  # (row, col): char
        self.placed_words: List[PlacedWord] = []
        self.clue_ids: Dict[str, Dict[int, str]] = {'across': {}, 'down': {}}
        self.clues: Dict[str, Dict[int, str]] = {'across': {}, 'down': {}}
        self.overlap_count: int = 0

    def can_place(self, word: str, row: int, col: int, direction: str) -> bool:
        """Check if a word can be placed at the specified position and direction."""
        overlap = False
        is_horizontal = direction == 'horizontal'

        # Check before the word starts and after it ends
        if is_horizontal:
            if (row, col-1) in self.grid or (row, col+len(word)) in self.grid:
                return False
        else:  # vertical
            if (row-1, col) in self.grid or (row+len(word), col) in self.grid:
                return False

        for i, letter in enumerate(word):
            r = row + (i if not is_horizontal else 0)
            c = col + (i if is_horizontal else 0)

            if (r, c) in self.grid:
                if self.grid[(r, c)] != letter:
                    return False
                overlap = True
            else:
                # Check adjacent cells in perpendicular direction to avoid adjacency
                if is_horizontal:
                    if (r-1, c) in self.grid or (r+1, c) in self.grid:
                        return False
                else:
                    if (r, c-1) in self.grid or (r, c+1) in self.grid:
                        return False

        return overlap

    def place_word(self, word: str, row: int, col: int, direction: str) -> None:
        """Place a word on the grid at the specified position and direction."""
        overlaps = 0
        is_horizontal = direction == 'horizontal'

        for i, letter in enumerate(word):
            r = row + (i if not is_horizontal else 0)
            c = col + (i if is_horizontal else 0)

            if (r, c) in self.grid:
                overlaps += 1
            self.grid[(r, c)] = letter

        self.overlap_count += overlaps
        self.placed_words.append(PlacedWord(word, row, col, direction))

    def _try_place_word(self, word: str) -> bool:
        """Try to place a single word in the existing grid."""
        random.shuffle(self.placed_words)

        for placed_word in self.placed_words:
            pw_row = placed_word.row
            pw_col = placed_word.col
            pw_dir = placed_word.direction
            pw_word = placed_word.word

            target_dir = 'vertical' if pw_dir == 'horizontal' else 'horizontal'

            for idx_placed, char in enumerate(pw_word):
                if char not in word:
                    continue

                for idx_new, c in enumerate(word):
                    if c != char:
                        continue

                    # Calculate new position
                    if target_dir == 'vertical':
                        new_row = pw_row - idx_new if pw_dir == 'horizontal' else pw_row + (idx_placed - idx_new)
                        new_col = pw_col + idx_placed if pw_dir == 'horizontal' else pw_col
                    else:
                        new_row = pw_row + idx_placed if pw_dir == 'vertical' else pw_row
                        new_col = pw_col - idx_new if pw_dir == 'vertical' else pw_col + (idx_placed - idx_new)

                    if self.can_place(word, new_row, new_col, target_dir):
                        self.place_word(word, new_row, new_col, target_dir)
                        return True

        return False

    def generate_grid(self, max_attempts: int = 50) -> bool:
        """Generate a crossword grid by trying multiple layouts."""
        best_grid = None
        best_placed_words = None
        best_overlap_count = -1
        best_clues = None

        for attempt in range(max_attempts):
            self.grid = {}
            self.placed_words = []
            self.overlap_count = 0
            self.clue_ids = {'across': {}, 'down': {}}

            # Sort words by length (longest first) with some randomization
            sorted_words = sorted(self.words, key=lambda x: (-len(x), random.random()))

            if not sorted_words:
                return False

            # Place the first word horizontally in the center
            first_word = sorted_words[0]
            start_col = -len(first_word) // 2
            self.place_word(first_word, 0, start_col, 'horizontal')

            # Try to place remaining words
            all_placed = True
            for word in sorted_words[1:]:
                if not self._try_place_word(word):
                    all_placed = False
                    break

            if all_placed:
                self._assign_clue_numbers()
                if self.overlap_count > best_overlap_count:
                    best_grid = dict(self.grid)
                    best_placed_words = list(self.placed_words)
                    best_overlap_count = self.overlap_count
                    best_clues = dict(self.clue_ids)

            print(f"Attempt {attempt + 1} of {max_attempts}: {self.overlap_count} overlaps")

        # Use the best grid found
        if best_grid is not None:
            self.grid = best_grid
            self.placed_words = best_placed_words
            self.overlap_count = best_overlap_count
            self.clue_ids = best_clues
            print(f"Best number of overlaps: {self.overlap_count}")
            return True

        return False

    def _assign_clue_numbers(self) -> None:
        """Assign sequential numbers to each word's starting position."""
        start_positions = []

        for pw in self.placed_words:
            row, col = pw.row, pw.col
            if pw.direction == 'horizontal':
                if (row, col - 1) not in self.grid:
                    start_positions.append((row, col))
            else:
                if (row - 1, col) not in self.grid:
                    start_positions.append((row, col))

        # Sort positions by row then column
        start_positions.sort(key=lambda x: (x[0], x[1]))

        # Assign numbers uniquely
        position_to_number = {}
        number = 1
        for pos in start_positions:
            if pos not in position_to_number:
                position_to_number[pos] = number
                number += 1

        # Assign clues with numbers
        for pw in self.placed_words:
            row, col = pw.row, pw.col
            if (row, col) in position_to_number:
                number = position_to_number[(row, col)]
                direction = 'across' if pw.direction == 'horizontal' else 'down'
                self.clue_ids[direction][number] = pw.word

    def generate_clues(self, base_url: str, api_key: str, model_id: str) -> None:
        """Generate clues for the crossword using an AI API."""
        openai.api_key = api_key
        openai.base_url = base_url

        for direction in ['across', 'down']:
            for number, word in list(self.clue_ids[direction].items()):
                try:
                    response = openai.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "Generate a concise 1-line crossword clue for children. Avoid mentioning the word directly. No need to mention the word length. Start with verb., n., adj., etc. Your response should be in this format 'n. <Description>.'"},
                            {"role": "user", "content": f"Word: {word}"}
                        ]
                    )
                    clue = response.choices[0].message.content.strip()
                    print(f"Generated clue for {word}: {clue}")
                    self.clues[direction][number] = clue
                except (openai.APIError, openai.APIConnectionError, openai.RateLimitError) as e:
                    print(f"Error generating clue for {word}: {str(e)}")
                    self.clues[direction][number] = f"Clue not generated: {str(e)}"
                    
    def save_clues_text(self, output_dir: str = 'output') -> None:
        """Save the crossword clues to a text file in the format '1: <clue text>'."""
        if not self.clues:
            print("No clues generated.")
            return

        os.makedirs(output_dir, exist_ok=True)
        
        with open(f'{output_dir}/crossword_clues.txt', 'w', encoding='utf-8') as f:
            f.write("ACROSS:\n")
            for number in sorted(self.clues['across'].keys()):
                f.write(f"{number}: {self.clues['across'][number]} ({len(self.clue_ids['across'][number])})\n")
            
            f.write("\nDOWN:\n")
            for number in sorted(self.clues['down'].keys()):
                f.write(f"{number}: {self.clues['down'][number]} ({len(self.clue_ids['down'][number])})\n")
        
        print(f"Clues saved to '{output_dir}/crossword_clues.txt'")

    def get_grid_bounds(self) -> Tuple[int, int, int, int]:
        """Get the minimum and maximum row and column values of the grid."""
        if not self.grid:
            return 0, 0, 0, 0
            
        rows = [r for r, _ in self.grid.keys()]
        cols = [c for _, c in self.grid.keys()]
        return min(rows), max(rows), min(cols), max(cols)

    def display_grid(self) -> None:
        """Display the grid in text form to the console."""
        if not self.grid:
            print("No grid generated.")
            return

        min_row, max_row, min_col, max_col = self.get_grid_bounds()

        for r in range(min_row, max_row + 1):
            row_str = []
            for c in range(min_col, max_col + 1):
                if (r, c) in self.grid:
                    row_str.append(self.grid[(r, c)])
                else:
                    row_str.append(' ')
            print(' '.join(row_str))
    
    def draw_grid(self, answer: bool = False, output_dir: str = 'output') -> None:
        """Draw the crossword grid as an image with clue numbers."""
        min_row, max_row, min_col, max_col = self.get_grid_bounds()
        
        # Create a mapping of starting positions to clue numbers
        clue_positions = {}
        for pw in self.placed_words:
            row, col = pw.row, pw.col
            direction = pw.direction
            
            for direction_key in ['across', 'down']:
                for number, word in self.clue_ids[direction_key].items():
                    if word == pw.word and (
                        (direction == 'horizontal' and direction_key == 'across') or
                        (direction == 'vertical' and direction_key == 'down')
                    ):
                        clue_positions[(row, col)] = number
                        break
        
        # Image settings
        cell_size = 40
        padding = 20
        font_size = 20
        number_size = 10
        
        # Calculate image dimensions
        grid_width = max_col - min_col + 1
        grid_height = max_row - min_row + 1
        img_width = grid_width * cell_size + 2 * padding
        img_height = grid_height * cell_size + 2 * padding
        
        # Create image
        img = Image.new('RGB', (img_width, img_height), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            main_font = ImageFont.truetype("Arial", font_size)
            number_font = ImageFont.truetype("Arial", number_size)
        except IOError:
            main_font = ImageFont.load_default()
            number_font = ImageFont.load_default()
        
        # Draw the grid cells
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                x = padding + (c - min_col) * cell_size
                y = padding + (r - min_row) * cell_size
                
                if (r, c) in self.grid:
                    # Draw cell rectangle
                    draw.rectangle([x, y, x + cell_size, y + cell_size], outline='black', width=1)
                    
                    # Draw letter if answer grid
                    letter = ' '
                    if answer:
                        letter = self.grid[(r, c)].upper()
                    draw.text(
                        (x + cell_size//2, y + cell_size//2),
                        letter,
                        fill='black',
                        font=main_font,
                        anchor="mm"
                    )
                    
                    # Draw clue number if this is a starting position
                    if (r, c) in clue_positions:
                        draw.text(
                            (x + 2, y + 2),
                            str(clue_positions[(r, c)]),
                            fill='black',
                            font=number_font
                        )
        
        os.makedirs(output_dir, exist_ok=True)
        filename = f'{output_dir}/crossword_puzzle_{"answer" if answer else "question"}.png'
        img.save(filename)
        print(f"Crossword image saved as '{filename}'")


def main():
    """Main function to run the crossword generator."""
    parser = argparse.ArgumentParser(description="Generate a crossword puzzle.")
    parser.add_argument("words", nargs="+", help="List of words to include in the crossword.")
    parser.add_argument("--max-attempts", type=int, default=30, help="Maximum number of attempts to generate a grid")
    parser.add_argument("--output-dir", default="output", help="Directory to save output files")
    parser.add_argument("--config", default="config.toml", help="Path to configuration file")
    args = parser.parse_args()

    # Read configuration
    api_address = api_secret = model_id = None
    try:
        with open(args.config, "rb") as config_file:
            config = toml.load(config_file)
        api_address = config.get("api", {}).get("address")
        api_secret = config.get("api", {}).get("secret")
        model_id = config.get("api", {}).get("model_id")
    except (toml.TOMLDecodeError, OSError) as e:
        print(f"Error reading config file: {e}")

    # Generate the crossword
    generator = CrosswordGenerator(args.words)
    if generator.generate_grid(max_attempts=args.max_attempts):
        print("Grid generated successfully!\nGrid Preview:")
        generator.display_grid()

        # Generate clues if API credentials are available
        if api_address and api_secret:
            generator.generate_clues(api_address, api_secret, model_id)
            generator.save_clues_text(args.output_dir)
        else:
            print("API credentials not available. Skipping clue generation.")

        # Save as images
        generator.draw_grid(answer=False, output_dir=args.output_dir)
        generator.draw_grid(answer=True, output_dir=args.output_dir)
        
        # Create PDF
        create_crossword_pdf(
            image_path=f"{args.output_dir}/crossword_puzzle_question.png",
            clues_path=f"{args.output_dir}/crossword_clues.txt",
            output_pdf_path=f"{args.output_dir}/crossword_puzzle.pdf"
        )
        create_crossword_pdf(
            image_path=f"{args.output_dir}/crossword_puzzle_answer.png",
            clues_path=f"{args.output_dir}/crossword_clues.txt",
            output_pdf_path=f"{args.output_dir}/crossword_puzzle_answer.pdf"
        )
    else:
        print("Failed to generate grid with all words.")


if __name__ == "__main__":
    main()
