import os
import json
import re

def clean_entry(entry):
    entry = entry.strip().replace('\n', ' ').replace('\\n', ' ')
    return entry

def parse_question_block(block):
    question = clean_entry(block[0])
    options_raw = clean_entry(block[1])
    option_lines = re.findall(r'\([A-D]\)\s*[^()\n]+', options_raw)  # Improved regex
    options = [opt.split(")", 1)[1].strip() for opt in option_lines]

    correct_line = clean_entry(block[2])
    match = re.search(r"Correct Answer:\s*\(([A-D])\)", correct_line)
    correct_letter = match.group(1) if match else None # Handle missing answers

    option_dict = {chr(65 + i): opt for i, opt in enumerate(options)}
    answer = option_dict.get(correct_letter)  # Don't set default "Unknown"

    return {
        "question": question,
        "options": options,
        "answer": answer if answer is not None else "Error: Could not parse answer" # Explicit error message in JSON
    }


def fix_file(path):
    with open(path, "r") as f:
        raw_text = f.read()

    # More robust block extraction using regex
    raw_text = raw_text.replace("python\n[", "").replace("]", "")
    question_blocks = re.findall(r'"(.*?)",\s*"(.*?)",\s*"(.*?)",?', raw_text, re.DOTALL)

    fixed_questions = []
    for block in question_blocks:
        cleaned_block = [clean_entry(item) for item in block]
        try:
            parsed = parse_question_block(cleaned_block)
            fixed_questions.append(parsed)
        except IndexError as e: # Add error handling
            print(f"Error processing block: {block}, Error: {e}")

    with open(path, "w") as f:
        json.dump(fixed_questions, f, indent=2)


def fix_all_batches():
    folder = "question_batches"  # Make sure this folder exists
    for file in os.listdir(folder):
        if file.endswith(".json"):
            print(f"🔧 Fixing {file}...")
            fix_file(os.path.join(folder, file))
    print("✅ All question files fixed.")

fix_all_batches()