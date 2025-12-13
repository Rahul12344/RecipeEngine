import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import List, Dict, Optional
import json
import os
from dataclasses import dataclass
from enum import Enum

class WordType(Enum):
    FOOD = "food"
    QUANTITY = "quantity"
    NEITHER = "neither"

@dataclass
class WordClassification:
    word: str
    type: WordType
    line_number: int

class WordClassifierGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Recipe Word Classifier")
        self.root.geometry("800x600")

        # Data structures
        self.lines: List[str] = []
        self.current_line_index: int = 0
        self.current_word_index: int = 0
        self.classifications: List[WordClassification] = []

        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create widgets
        self._create_widgets()

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)

    def _create_widgets(self):
        # Text input area
        ttk.Label(self.main_frame, text="Enter or paste recipe text:").grid(row=0, column=0, sticky=tk.W)
        self.text_input = scrolledtext.ScrolledText(self.main_frame, height=10)
        self.text_input.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Start button
        self.start_button = ttk.Button(self.main_frame, text="Start Classification", command=self.start_classification)
        self.start_button.grid(row=2, column=0, pady=10)

        # Progress frame
        self.progress_frame = ttk.LabelFrame(self.main_frame, text="Classification Progress", padding="5")
        self.progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)

        # Current line display
        self.current_line_label = ttk.Label(self.progress_frame, text="")
        self.current_line_label.grid(row=0, column=0, sticky=tk.W)

        # Current word display
        self.current_word_label = ttk.Label(self.progress_frame, text="")
        self.current_word_label.grid(row=1, column=0, sticky=tk.W)

        # Classification buttons
        self.button_frame = ttk.Frame(self.progress_frame)
        self.button_frame.grid(row=2, column=0, pady=5)

        self.food_button = ttk.Button(self.button_frame, text="Food", command=lambda: self.classify_word(WordType.FOOD))
        self.food_button.grid(row=0, column=0, padx=5)

        self.quantity_button = ttk.Button(self.button_frame, text="Quantity", command=lambda: self.classify_word(WordType.QUANTITY))
        self.quantity_button.grid(row=0, column=1, padx=5)

        self.neither_button = ttk.Button(self.button_frame, text="Neither", command=lambda: self.classify_word(WordType.NEITHER))
        self.neither_button.grid(row=0, column=2, padx=5)

        # Save button
        self.save_button = ttk.Button(self.main_frame, text="Save Classifications", command=self.save_classifications)
        self.save_button.grid(row=4, column=0, pady=10)

        # Initially disable progress-related widgets
        self._toggle_progress_widgets(False)

    def _toggle_progress_widgets(self, enabled: bool):
        """Enable or disable widgets related to the classification process"""
        state = "normal" if enabled else "disabled"
        self.current_line_label.configure(state=state)
        self.current_word_label.configure(state=state)
        self.food_button.configure(state=state)
        self.quantity_button.configure(state=state)
        self.neither_button.configure(state=state)
        self.save_button.configure(state=state)
        self.text_input.configure(state="disabled" if enabled else "normal")
        self.start_button.configure(state="disabled" if enabled else "normal")

    def start_classification(self):
        """Start the classification process"""
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            return

        self.lines = [line.strip() for line in text.split('\n') if line.strip()]
        self.current_line_index = 0
        self.current_word_index = 0
        self.classifications = []

        self._toggle_progress_widgets(True)
        self._update_display()

    def _update_display(self):
        """Update the display with current line and word"""
        if self.current_line_index >= len(self.lines):
            self._toggle_progress_widgets(False)
            return

        current_line = self.lines[self.current_line_index]
        words = current_line.split()

        if self.current_word_index >= len(words):
            self.current_line_index += 1
            self.current_word_index = 0
            if self.current_line_index >= len(self.lines):
                self._toggle_progress_widgets(False)
                return
            self._update_display()
            return

        self.current_line_label.configure(text=f"Current line: {current_line}")
        self.current_word_label.configure(text=f"Current word: {words[self.current_word_index]}")

    def classify_word(self, word_type: WordType):
        """Classify the current word and move to the next"""
        if self.current_line_index >= len(self.lines):
            return

        current_line = self.lines[self.current_line_index]
        words = current_line.split()

        if self.current_word_index >= len(words):
            return

        word = words[self.current_word_index]
        classification = WordClassification(
            word=word,
            type=word_type,
            line_number=self.current_line_index + 1
        )
        self.classifications.append(classification)

        self.current_word_index += 1
        self._update_display()

    def save_classifications(self):
        """Save the classifications to a JSON file"""
        if not self.classifications:
            return

        # Create data directory if it doesn't exist
        os.makedirs("data/classifications", exist_ok=True)

        # Convert classifications to dictionary format
        classifications_dict = [
            {
                "word": c.word,
                "type": c.type.value,
                "line_number": c.line_number
            }
            for c in self.classifications
        ]

        # Save to file
        with open("data/classifications/word_classifications.json", "w") as f:
            json.dump(classifications_dict, f, indent=2)

def main():
    root = tk.Tk()
    app = WordClassifierGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()