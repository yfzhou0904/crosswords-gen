import random
import openai
from matplotlib import pyplot as plt
import numpy as np


class CrosswordGenerator:
    def __init__(self, words):
        self.words = list(set(words))  # Remove duplicates
        self.grid = {}  # (row, col): char
        self.placed_words = []  # List of placed words and their metadata
        self.clues = {'across': {}, 'down': {}}

    def can_place(self, word, row, col, direction):
        overlap = False
        for i in range(len(word)):
            r = row + (i if direction == 'vertical' else 0)
            c = col + (i if direction == 'horizontal' else 0)
            if (r, c) in self.grid:
                if self.grid[(r, c)] != word[i]:
                    return False
                overlap = True
            else:
                # Check adjacent cells in perpendicular direction to avoid adjacency
                if direction == 'horizontal':
                    if (r-1, c) in self.grid or (r+1, c) in self.grid:
                        return False
                else:
                    if (r, c-1) in self.grid or (r, c+1) in self.grid:
                        return False
        return overlap

    def place_word(self, word, row, col, direction):
        for i in range(len(word)):
            r = row + (i if direction == 'vertical' else 0)
            c = col + (i if direction == 'horizontal' else 0)
            self.grid[(r, c)] = word[i]
        self.placed_words.append(
            {'word': word, 'row': row, 'col': col, 'direction': direction})

    def generate_grid(self, max_attempts=50):
        sorted_words = sorted(
            self.words, key=lambda x: (-len(x), random.random()))
        for _ in range(max_attempts):
            self.grid = {}
            self.placed_words = []
            if not sorted_words:
                return False
            # Place the first word horizontally in the center
            first_word = sorted_words[0]
            start_col = -len(first_word) // 2
            self.place_word(first_word, 0, start_col, 'horizontal')

            for word in sorted_words[1:]:
                placed = False
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
                        # Check all positions in new word where char appears
                        for idx_new, c in enumerate(word):
                            if c == char:
                                # Calculate new word's start position based on overlap
                                if target_dir == 'vertical':
                                    new_row = pw_row - idx_new if pw_dir == 'horizontal' else pw_row + \
                                        (idx_placed - idx_new)
                                    new_col = pw_col + idx_placed if pw_dir == 'horizontal' else pw_col
                                else:
                                    new_row = pw_row + idx_placed if pw_dir == 'vertical' else pw_row
                                    new_col = pw_col - idx_new if pw_dir == 'vertical' else pw_col + \
                                        (idx_placed - idx_new)

                                if self.can_place(word, new_row, new_col, target_dir):
                                    self.place_word(
                                        word, new_row, new_col, target_dir)
                                    placed = True
                                    break
                            if placed:
                                break
                        if placed:
                            break
                    if placed:
                        break
                if not placed:
                    break
                placed = False
            else:
                # All words placed successfully
                self._assign_clue_numbers()
                return True
        return False

    def _assign_clue_numbers(self):
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

    def generate_clues(self, base_url, api_key):
        openai.api_key = api_key
        openai.base_url = base_url
        for direction in ['across', 'down']:
            for number, word in self.clues[direction].items():
                try:
                    response = openai.chat.completions.create(
                        model="fireworks.accounts/fireworks/models/deepseek-v3",
                        messages=[
                            {"role": "system", "content": "Generate a concise crossword clue. Avoid mentioning the word directly. No need to mention the word length."},
                            {"role": "user", "content": f"Word: {word}"}
                        ]
                    )
                    clue = response.choices[0].message.content.strip()
                    print(f"Generated clue for {word}: {clue}")
                    self.clues[direction][number] = clue
                except Exception as e:
                    self.clues[direction][number] = f"Clue not generated: {str(e)}"

    def display_grid(self):
        if not self.grid:
            print("No grid generated.")
            return
        rows = [r for r, _ in self.grid.keys()]
        cols = [c for _, c in self.grid.keys()]
        min_row, max_row = min(rows), max(rows)
        min_col, max_col = min(cols), max(cols)

        for r in range(min_row, max_row + 1):
            row_str = []
            for c in range(min_col, max_col + 1):
                if (r, c) in self.grid:
                    row_str.append(self.grid[(r, c)])
                else:
                    row_str.append(' ')
            print(' '.join(row_str))

    def plot_grid(self, filename='output/crossword.png'):
        if not self.grid:
            return
        rows = [r for r, _ in self.grid.keys()]
        cols = [c for _, c in self.grid.keys()]
        min_row, max_row = min(rows), max(rows)
        min_col, max_col = min(cols), max(cols)

        cell_size = 30
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_xlim(min_col - 1, max_col + 1)
        ax.set_ylim(min_row - 1, max_row + 1)
        ax.set_aspect('equal')
        ax.axis('off')

        # Draw grid lines and letters
        for (r, c), letter in self.grid.items():
            rect = plt.Rectangle((c - 0.5, r - 0.5), 1, 1,
                                 fill=None, edgecolor='black', linewidth=1)
            ax.add_patch(rect)
            ax.text(c, r, letter.upper(), va='center',
                    ha='center', fontsize=12)

        plt.gca().invert_yaxis()
        plt.savefig(filename, bbox_inches='tight')
        plt.close()


# Example usage:
if __name__ == "__main__":
    words = ["PYTHON", "MONTH", "PROGRAM", "LANGUAGE", "CLUE", "WORD"]
    generator = CrosswordGenerator(words)
    if generator.generate_grid():
        print("Grid generated successfully!\nGrid Preview:")
        generator.display_grid()
        print(generator.clues)

        # Uncomment below to generate clues (requires OpenAI API key)
        generator.generate_clues(
            "https://owu.yfzhou.fyi/api/", "sk-9b25f5917dcd4210b655d65e8c2ca11c")

        # To save as image
        generator.plot_grid()
        print("Crossword image saved as 'output/crossword.png'.")
        print('Final clues:')
        print(generator.clues)
    else:
        print("Failed to generate grid with all words.")
