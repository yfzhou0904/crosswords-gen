import os
import random
from typing import List, Tuple
import argparse
import tomllib as toml
import openai
from matplotlib import pyplot as plt


class CrosswordGenerator:
    """Generator for crossword puzzles from a list of words."""

    def __init__(self, words: List[str]):
        """Initialize the crossword generator with a list of words."""
        self.words = list(set(words))  # Remove duplicates
        self.grid = {}  # (row, col): char
        self.placed_words = []  # List of placed words and their metadata
        self.clues = {'across': {}, 'down': {}}
        self.overlap_count = 0  # Track overlaps

    def can_place(self, word: str, row: int, col: int, direction: str) -> bool:
        """Check if a word can be placed at the specified position and direction."""
        overlap = False
        is_horizontal = direction == 'horizontal'

        # Check before the word starts
        if is_horizontal:
            if (row, col-1) in self.grid:  # Check cell before word starts
                return False
            if (row, col+len(word)) in self.grid:  # Check cell after word ends
                return False
        else:  # vertical
            if (row-1, col) in self.grid:  # Check cell before word starts
                return False
            if (row+len(word), col) in self.grid:  # Check cell after word ends
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

            if (r, c) in self.grid:  # If there's already a letter here, it's an overlap
                overlaps += 1
            self.grid[(r, c)] = letter

        self.overlap_count += overlaps
        self.placed_words.append({
            'word': word,
            'row': row,
            'col': col,
            'direction': direction
        })

    def _try_place_word(self, word: str) -> bool:
        """Try to place a single word in the existing grid."""
        random.shuffle(self.placed_words)

        for placed_word in self.placed_words:
            pw_row = placed_word['row']
            pw_col = placed_word['col']
            pw_dir = placed_word['direction']
            pw_word = placed_word['word']

            target_dir = 'vertical' if pw_dir == 'horizontal' else 'horizontal'

            for idx_placed, char in enumerate(pw_word):
                if char not in word:
                    continue

                for idx_new, c in enumerate(word):
                    if c != char:
                        continue

                    # Calculate new position
                    if target_dir == 'vertical':
                        new_row = pw_row - idx_new if pw_dir == 'horizontal' else pw_row + \
                            (idx_placed - idx_new)
                        new_col = pw_col + idx_placed if pw_dir == 'horizontal' else pw_col
                    else:
                        new_row = pw_row + idx_placed if pw_dir == 'vertical' else pw_row
                        new_col = pw_col - idx_new if pw_dir == 'vertical' else pw_col + \
                            (idx_placed - idx_new)

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
            print(f"Attempt {attempt + 1} of {max_attempts}")
            self.grid = {}
            self.placed_words = []
            self.overlap_count = 0
            self.clues = {'across': {}, 'down': {}}

            # Sort words by length (longest first) with some randomization
            sorted_words = sorted(
                self.words, key=lambda x: (-len(x), random.random()))

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
                # All words placed successfully
                self._assign_clue_numbers()
                if self.overlap_count > best_overlap_count:
                    best_grid = dict(self.grid)
                    best_placed_words = list(self.placed_words)
                    best_overlap_count = self.overlap_count
                    best_clues = dict(self.clues)

            print(
                f"Attempt {attempt + 1} of {max_attempts}: {self.overlap_count} overlaps")

        # Use the best grid found
        if best_grid is not None:
            self.grid = best_grid
            self.placed_words = best_placed_words
            self.overlap_count = best_overlap_count
            self.clues = best_clues
            print(f"Best number of overlaps: {self.overlap_count}")
            return True

        return False

    def _assign_clue_numbers(self) -> None:
        """Assign sequential numbers to each word's starting position."""
        start_positions = []

        for pw in self.placed_words:
            row, col = pw['row'], pw['col']
            if pw['direction'] == 'horizontal':
                if (row, col - 1) not in self.grid:
                    start_positions.append((row, col))
            else:
                if (row - 1, col) not in self.grid:
                    start_positions.append((row, col))

        # Sort positions by row then column
        start_positions.sort(key=lambda x: (x[0], x[1]))

        # Assign numbers uniquely
        seen = {}
        number = 1
        for pos in start_positions:
            if pos not in seen:
                seen[pos] = number
                number += 1

        # Assign clues with numbers
        for pw in self.placed_words:
            row, col = pw['row'], pw['col']
            if (row, col) in seen:
                number = seen[(row, col)]
                direction = 'across' if pw['direction'] == 'horizontal' else 'down'
                self.clues[direction][number] = pw['word']

    def generate_clues(self, base_url: str, api_key: str, model_id: str) -> None:
        """Generate clues for the crossword using an AI API."""
        openai.api_key = api_key
        openai.base_url = base_url

        for direction in ['across', 'down']:
            for number, word in list(self.clues[direction].items()):
                try:
                    response = openai.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "Generate a concise crossword clue for children. Avoid mentioning the word directly. No need to mention the word length. Start with verb., n., adj., etc."},
                            {"role": "user", "content": f"Word: {word}"}
                        ]
                    )
                    clue = response.choices[0].message.content.strip()
                    print(f"Generated clue for {word}: {clue}")
                    self.clues[direction][number] = clue
                except (openai.APIError, openai.APIConnectionError, openai.RateLimitError) as e:
                    print(f"Error generating clue for {word}: {str(e)}")
                    self.clues[direction][number] = f"Clue not generated: {str(e)}"

    def get_grid_bounds(self) -> Tuple[int, int, int, int]:
        """Get the minimum and maximum row and column values of the grid."""
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

    def plot_grid(self, output_dir: str = 'output') -> None:
        """Plot the grid as images (answer and question)."""
        if not self.grid:
            return

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        min_row, max_row, min_col, max_col = self.get_grid_bounds()

        # Generate and save answer grid
        self._create_grid_plot(min_row, max_row, min_col, max_col,
                               show_letters=True,
                               filename=f'{output_dir}/answer.png')

        # Generate and save question grid
        self._create_grid_plot(min_row, max_row, min_col, max_col,
                               show_letters=False,
                               filename=f'{output_dir}/question.png')

    def _create_grid_plot(self, min_row: int, max_row: int, min_col: int, max_col: int,
                          show_letters: bool, filename: str) -> None:
        """Create and save a single grid plot."""
        _, ax = plt.subplots(figsize=(10, 10))
        ax.set_xlim(min_col - 1, max_col + 1)
        ax.set_ylim(min_row - 1, max_row + 1)
        ax.set_aspect('equal')
        ax.axis('off')

        for (r, c), letter in self.grid.items():
            rect = plt.Rectangle(
                (c - 0.5, r - 0.5),
                1, 1,
                fill=None,
                edgecolor='black',
                linewidth=1
            )
            ax.add_patch(rect)

            if show_letters:
                ax.text(c, r, letter.upper(), va='center',
                        ha='center', fontsize=12)

        plt.gca().invert_yaxis()
        plt.savefig(filename, bbox_inches='tight')
        plt.close()

    def get_overlap_count(self) -> int:
        """Returns the total number of overlapping letters in the crossword."""
        return self.overlap_count


def main():
    """Main function to run the crossword generator."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate a crossword puzzle.")
    parser.add_argument("words", nargs="+",
                        help="List of words to include in the crossword.")
    parser.add_argument("--max-attempts", type=int, default=30,
                        help="Maximum number of attempts to generate a grid")
    parser.add_argument("--output-dir", default="output",
                        help="Directory to save output files")
    parser.add_argument("--config", default="config.toml",
                        help="Path to configuration file")
    args = parser.parse_args()

    # Read configuration
    try:
        with open(args.config, "rb") as config_file:
            config = toml.load(config_file)
        api_address = config.get("api", {}).get("address")
        api_secret = config.get("api", {}).get("secret")
        model_id = config.get("api", {}).get("model_id")
    except (toml.TOMLDecodeError, OSError) as e:
        print(f"Error reading config file: {e}")
        api_address = api_secret = None

    # Generate the crossword
    generator = CrosswordGenerator(args.words)
    if generator.generate_grid(max_attempts=args.max_attempts):
        print("Grid generated successfully!\nGrid Preview:")
        generator.display_grid()

        # Generate clues if API credentials are available
        if api_address and api_secret:
            generator.generate_clues(api_address, api_secret, model_id)
        else:
            print("API credentials not available. Skipping clue generation.")

        # Save as images
        generator.plot_grid(args.output_dir)
        print(f"Crossword images saved in '{args.output_dir}'.")
        print('Final clues:')
        print(generator.clues)
    else:
        print("Failed to generate grid with all words.")


if __name__ == "__main__":
    main()
