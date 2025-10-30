#!/usr/bin/env python3
"""
Pixel Inspector Tool - Interactive Screenshot Annotation

Creates accurate annotations by allowing you to click-and-drag boxes around UI elements.
Press number keys to label each box, then save to generate both annotated image and coordinate code.

Controls:
- Click and drag: Draw box
- 1-9: Number the last box
- d: Delete last box
- c: Clear all boxes
- s: Save and export
- q: Quit
"""

import sys
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
from pathlib import Path

class PixelInspector:
    def __init__(self, master, image_path):
        self.master = master
        self.image_path = Path(image_path)
        self.master.title(f"Pixel Inspector - {self.image_path.name}")

        # Load image
        self.original_image = Image.open(self.image_path)
        self.image_width, self.image_height = self.original_image.size

        # Scale image if too large for screen
        max_width, max_height = 1400, 800
        self.scale = 1.0

        if self.original_image.width > max_width or self.original_image.height > max_height:
            self.scale = min(max_width / self.original_image.width, max_height / self.original_image.height)
            new_size = (int(self.original_image.width * self.scale), int(self.original_image.height * self.scale))
            self.display_image = self.original_image.resize(new_size, Image.Resampling.LANCZOS)
        else:
            self.display_image = self.original_image.copy()

        print(f"\n{'='*70}")
        print(f"PIXEL INSPECTOR TOOL")
        print(f"{'='*70}\n")
        print(f"Image: {self.image_path.name}")
        print(f"Size: {self.image_width}x{self.image_height}")
        print(f"Scale: {self.scale:.2f}x\n")
        print(f"CONTROLS:")
        print(f"  - Click and drag to draw a box")
        print(f"  - Press 1-9 to number the last box")
        print(f"  - Press 'd' to delete last box")
        print(f"  - Press 'c' to clear all boxes")
        print(f"  - Press 's' to save and export code")
        print(f"  - Press 'q' or close window to quit\n")
        print(f"Start annotating...")

        # Create canvas
        self.canvas = tk.Canvas(
            master,
            width=self.display_image.width,
            height=self.display_image.height,
            cursor="cross"
        )
        self.canvas.pack()

        # Display image
        self.photo = ImageTk.PhotoImage(self.display_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # State variables
        self.boxes = []  # List of {start: (x,y), end: (x,y), number: int}
        self.current_box_start = None
        self.drawing = False
        self.current_rect = None

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        master.bind("<Key>", self.on_key_press)

        # Instructions label
        self.info_label = tk.Label(
            master,
            text="Click and drag to draw boxes | Press 1-9 to number | 'd' delete | 'c' clear | 's' save | 'q' quit",
            bg="lightgray",
            pady=5
        )
        self.info_label.pack(fill=tk.X)

        # Status label
        self.status_label = tk.Label(master, text=f"Boxes: 0 | Last action: Ready", pady=3)
        self.status_label.pack(fill=tk.X)

    def on_mouse_down(self, event):
        """Start drawing a box"""
        # Convert display coordinates to original image coordinates
        orig_x = int(event.x / self.scale)
        orig_y = int(event.y / self.scale)
        self.current_box_start = (orig_x, orig_y)
        self.drawing = True

    def on_mouse_drag(self, event):
        """Update box preview while dragging"""
        if not self.drawing:
            return

        # Remove previous preview
        if self.current_rect:
            self.canvas.delete(self.current_rect)

        # Draw preview rectangle (on display coordinates)
        dx1 = self.current_box_start[0] * self.scale
        dy1 = self.current_box_start[1] * self.scale
        dx2 = event.x
        dy2 = event.y

        # Ensure x1,y1 is top-left
        x1, x2 = min(dx1, dx2), max(dx1, dx2)
        y1, y2 = min(dy1, dy2), max(dy1, dy2)

        self.current_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="green",
            width=2,
            dash=(4, 4)
        )

    def on_mouse_up(self, event):
        """Finish drawing a box"""
        if not self.drawing:
            return

        # Remove preview
        if self.current_rect:
            self.canvas.delete(self.current_rect)
            self.current_rect = None

        # Convert to original coordinates
        orig_x = int(event.x / self.scale)
        orig_y = int(event.y / self.scale)

        # Ensure start is top-left, end is bottom-right
        x1 = min(self.current_box_start[0], orig_x)
        y1 = min(self.current_box_start[1], orig_y)
        x2 = max(self.current_box_start[0], orig_x)
        y2 = max(self.current_box_start[1], orig_y)

        # Add box (without number yet)
        box = {
            'start': (x1, y1),
            'end': (x2, y2),
            'number': None
        }
        self.boxes.append(box)

        width = x2 - x1
        height = y2 - y1
        print(f"Box {len(self.boxes)} added: {(x1, y1)} to ({(x2, y2)}) - size: {width}x{height}")
        print(f"Press a number key (1-9) to assign a number to this box")

        self.drawing = False
        self.redraw()
        self.update_status(f"Box added: ({x1},{y1}) to ({x2},{y2}) - Press 1-9 to number")

    def on_key_press(self, event):
        """Handle keyboard input"""
        key = event.char

        # Number keys (1-9)
        if key in '123456789':
            # Find last unnumbered box
            for box in reversed(self.boxes):
                if box['number'] is None:
                    box['number'] = int(key)
                    print(f"Box {len(self.boxes)} assigned number: {key}")
                    self.redraw()
                    self.update_status(f"Assigned number {key} to last box")
                    return
            print("No unnumbered box to assign number to")
            self.update_status("No unnumbered box to number")

        # Delete last box
        elif key == 'd' or event.keysym == 'd':
            if self.boxes:
                deleted = self.boxes.pop()
                print(f"Deleted box {len(self.boxes) + 1}")
                self.redraw()
                self.update_status("Deleted last box")
            else:
                self.update_status("No boxes to delete")

        # Clear all
        elif key == 'c' or event.keysym == 'c':
            self.boxes = []
            print("Cleared all boxes")
            self.redraw()
            self.update_status("Cleared all boxes")

        # Save
        elif key == 's' or event.keysym == 's':
            self.save_and_export()

        # Quit
        elif key == 'q' or event.keysym == 'q':
            self.master.quit()

    def redraw(self):
        """Redraw all boxes on canvas"""
        # Clear canvas
        self.canvas.delete("all")

        # Redraw image
        img_copy = self.display_image.copy()
        draw = ImageDraw.Draw(img_copy)

        # Draw boxes with numbers
        for box in self.boxes:
            x1, y1 = box['start']
            x2, y2 = box['end']
            number = box['number']

            # Scale coordinates for display
            dx1 = int(x1 * self.scale)
            dy1 = int(y1 * self.scale)
            dx2 = int(x2 * self.scale)
            dy2 = int(y2 * self.scale)

            # Draw red box
            draw.rectangle([(dx1, dy1), (dx2, dy2)], outline=(255, 0, 0), width=3)

            # Draw number (white text with red outline, no background)
            if number is not None:
                # Position to RIGHT of box
                text_x = dx2 + 25  # Slightly right of box
                text_y = dy1 + (dy2 - dy1) // 2  # Vertically centered

                # White text with red outline (for better AI recognition)
                try:
                    font = ImageFont.truetype("arial.ttf", 24)
                except:
                    font = ImageFont.load_default()

                # Draw number
                text = str(number)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                final_x = text_x - text_width // 2
                final_y = text_y - text_height // 2 - 2

                # White text with red stroke
                draw.text(
                    (final_x, final_y),
                    text,
                    fill=(255, 255, 255),      # White text
                    font=font,
                    stroke_width=2,            # 2px red outline
                    stroke_fill=(255, 0, 0)    # Red outline
                )

        # Update canvas
        self.photo = ImageTk.PhotoImage(img_copy)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=f"Boxes: {len(self.boxes)} | Last action: {message}")

    def save_and_export(self):
        """Save annotated image and export Python coordinates"""
        if not self.boxes:
            print("No boxes to save!")
            self.update_status("ERROR: No boxes to save")
            return

        # Create output directory
        output_dir = self.image_path.parent / "annotated"
        output_dir.mkdir(exist_ok=True)

        # Filenames
        filename = self.image_path.stem
        annotated_path = output_dir / f"{filename}_annotated.png"
        code_path = output_dir / f"{filename}_coordinates.py"

        # Create annotated image on ORIGINAL resolution
        img_annotated = self.original_image.copy()
        draw = ImageDraw.Draw(img_annotated)

        # Draw boxes and numbers at original scale
        for box in self.boxes:
            x1, y1 = box['start']
            x2, y2 = box['end']
            number = box['number']

            # Draw red box
            draw.rectangle([(x1, y1), (x2, y2)], outline=(255, 0, 0), width=3)

            # Draw number (white text with red outline, no background)
            if number is not None:
                # Position to RIGHT of box
                text_x = x2 + 25  # Slightly right of box
                text_y = y1 + (y2 - y1) // 2  # Vertically centered

                # White text with red outline (for better AI recognition)
                try:
                    font = ImageFont.truetype("arial.ttf", 24)
                except:
                    font = ImageFont.load_default()

                # Draw number
                text = str(number)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                final_x = text_x - text_width // 2
                final_y = text_y - text_height // 2 - 2

                # White text with red stroke
                draw.text(
                    (final_x, final_y),
                    text,
                    fill=(255, 255, 255),      # White text
                    font=font,
                    stroke_width=2,            # 2px red outline
                    stroke_fill=(255, 0, 0)    # Red outline
                )

        # Save annotated image
        img_annotated.save(annotated_path)

        # Export Python code
        with open(code_path, 'w') as f:
            f.write(f"# Coordinates for {filename}.png\n")
            f.write(f"# Image size: {self.image_width}x{self.image_height}\n\n")

            # Sort by number (unnumbered last)
            sorted_boxes = sorted(self.boxes, key=lambda b: b['number'] if b['number'] else 999)

            for box in sorted_boxes:
                x1, y1 = box['start']
                x2, y2 = box['end']
                width = x2 - x1
                height = y2 - y1
                number = box['number'] if box['number'] else 0

                f.write(f"# Field {number}\n")
                f.write(f"draw_box_with_number(draw, {x1}, {y1}, {width}, {height}, {number})\n\n")

        # Print confirmation
        print(f"\n{'='*70}")
        print(f"SAVED!")
        print(f"{'='*70}\n")
        print(f"Annotated image: {annotated_path.relative_to(self.image_path.parents[2])}")
        print(f"Python code: {code_path.relative_to(self.image_path.parents[2])}\n")
        print(f"Coordinates:")
        for box in sorted(self.boxes, key=lambda b: b['number'] if b['number'] else 999):
            x1, y1 = box['start']
            x2, y2 = box['end']
            width = x2 - x1
            height = y2 - y1
            number = box['number'] if box['number'] else 0
            print(f"  Field {number}: x={x1}, y={y1}, width={width}, height={height}")

        self.update_status(f"SAVED: {len(self.boxes)} boxes exported")

def main():
    # Get image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        root = tk.Tk()
        root.withdraw()
        image_path = filedialog.askopenfilename(
            title="Select Screenshot to Annotate",
            filetypes=[("PNG images", "*.png"), ("All files", "*.*")]
        )
        root.destroy()

        if not image_path:
            print("No image selected. Exiting.")
            return

    # Create main window
    root = tk.Tk()
    app = PixelInspector(root, image_path)
    root.mainloop()

if __name__ == "__main__":
    main()
