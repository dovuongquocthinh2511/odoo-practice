#!/usr/bin/env python3
"""
Batch Annotation Helper Script

Guides you through annotating all screenshots that need work.
Uses the pixel inspector tool for each image sequentially.
Tracks progress and allows resume if interrupted.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def load_results():
    """Load analysis results from JSON"""
    results_file = Path("annotation_analysis_results.json")
    if not results_file.exists():
        print("\nError: annotation_analysis_results.json not found!")
        print("Please run: python analyze_annotations.py first\n")
        sys.exit(1)

    with open(results_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_progress():
    """Load progress from tracking file"""
    progress_file = Path("annotation_progress.json")
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "skipped": []}

def save_progress(progress):
    """Save progress to tracking file"""
    progress_file = Path("annotation_progress.json")
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)

def get_original_screenshot_path(annotated_path):
    """Convert annotated path to original screenshot path"""
    # annotated_path like: "02_admin\annotated\01_dashboard_annotated.png"
    # need to convert to: "vi/screenshots/02_admin/01_dashboard.png"

    parts = Path(annotated_path).parts
    directory = parts[0]  # e.g., "02_admin"
    filename = parts[2]   # e.g., "01_dashboard_annotated.png"

    # Remove "_annotated" suffix
    original_filename = filename.replace("_annotated", "")

    original_path = Path("vi/screenshots") / directory / original_filename
    return original_path

def main():
    print("\n" + "="*80)
    print("BATCH ANNOTATION HELPER")
    print("="*80 + "\n")

    # Load analysis results
    results_data = load_results()
    needs_work = [r for r in results_data["results"] if r["status"] == "NEEDS_WORK"]

    if not needs_work:
        print("No images need annotation! All images match the pattern.")
        return

    # Load progress
    progress = load_progress()
    completed = set(progress["completed"])
    skipped = set(progress["skipped"])

    # Filter out already completed/skipped
    remaining = [img for img in needs_work if img["relative_path"] not in completed and img["relative_path"] not in skipped]

    total = len(needs_work)
    done = len(completed)
    skip_count = len(skipped)
    todo = len(remaining)

    print(f"PROGRESS SUMMARY")
    print(f"{'='*80}\n")
    print(f"  Total images needing work: {total}")
    print(f"  Completed: {done}")
    print(f"  Skipped: {skip_count}")
    print(f"  Remaining: {todo}\n")

    if todo == 0:
        print("All images have been processed!")
        print("\nRun 'python analyze_annotations.py' to verify.\n")
        return

    print(f"{'='*80}")
    print(f"IMAGES TO ANNOTATE ({todo} remaining)")
    print(f"{'='*80}\n")

    for i, img_data in enumerate(remaining, 1):
        relative_path = img_data["relative_path"]
        original_path = get_original_screenshot_path(relative_path)

        print(f"\n[{i}/{todo}] {relative_path}")
        print(f"       Original: {original_path}")

        # Check if original exists
        if not original_path.exists():
            print(f"       [ERROR] Original screenshot not found!")
            print(f"       Skipping...")
            skipped.add(relative_path)
            save_progress(progress)
            continue

        # Ask user what to do
        print(f"\n       Options:")
        print(f"         [a] Annotate this image (launch pixel inspector)")
        print(f"         [s] Skip this image")
        print(f"         [q] Quit (progress will be saved)")

        choice = input(f"\n       Your choice [a/s/q]: ").strip().lower()

        if choice == 'q':
            print(f"\n       Progress saved. Run this script again to continue.\n")
            break

        elif choice == 's':
            print(f"       Skipped {relative_path}")
            skipped.add(relative_path)
            save_progress(progress)
            continue

        elif choice == 'a':
            print(f"\n       Launching pixel inspector for: {original_path}")
            print(f"       {'='*70}")
            print(f"       INSTRUCTIONS:")
            print(f"         1. Click and drag to draw boxes around UI elements")
            print(f"         2. Press number keys (1-9) to label each box")
            print(f"         3. Press 's' to save and exit")
            print(f"         4. Press 'q' to quit without saving")
            print(f"       {'='*70}\n")

            input(f"       Press ENTER to launch pixel inspector...")

            # Launch pixel inspector
            try:
                cmd = [sys.executable, "pixel_inspector_tkinter.py", str(original_path)]
                result = subprocess.run(cmd, cwd=Path.cwd())

                if result.returncode == 0:
                    print(f"\n       [SUCCESS] Annotation complete!")
                    completed.add(relative_path)
                    save_progress(progress)
                else:
                    print(f"\n       [WARNING] Pixel inspector exited with code {result.returncode}")
                    retry = input(f"       Mark as completed anyway? [y/n]: ").strip().lower()
                    if retry == 'y':
                        completed.add(relative_path)
                        save_progress(progress)

            except KeyboardInterrupt:
                print(f"\n\n       Interrupted by user. Progress saved.")
                break
            except Exception as e:
                print(f"\n       [ERROR] Failed to launch pixel inspector: {e}")
                continue

        else:
            print(f"       Invalid choice. Skipping this image.")
            continue

    # Final summary
    progress = load_progress()
    final_completed = len(progress["completed"])
    final_skipped = len(progress["skipped"])
    final_remaining = total - final_completed - final_skipped

    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}\n")
    print(f"  Total: {total}")
    print(f"  Completed: {final_completed}")
    print(f"  Skipped: {final_skipped}")
    print(f"  Remaining: {final_remaining}\n")

    if final_remaining == 0:
        print("All images processed!")
        print("\nRun 'python analyze_annotations.py' to verify all annotations.\n")
    else:
        print(f"Run this script again to continue with {final_remaining} remaining images.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved.")
        sys.exit(0)
