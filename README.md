# CompTIA A+ Practice Exam Desktop App

This project creates a desktop practice exam for CompTIA A+ Core 1 (220-1201) and Core 2 (220-1202) using a modern CustomTkinter interface and a built-in JSON question bank.

## Features
- Exam selection for Core 1, Core 2, or combined practice
- Official exam-format weighting or domain-specific filtering
- Question count selection from 10 to 1,000 questions
- Timed practice options: untimed, 30 seconds per question, or 90-minute full exam mode
- Review palette, flagging, next/previous navigation, and auto-submit on timeout
- Results dashboard with pass/fail indicator and domain breakdowns
- Detailed review explanations for each question
- Interactive PBQs for ordering, one-to-one matching, and drag-and-drop classification, scored all-or-nothing

## Running the app

```bash
python app.py
```

## Building the Windows executable

On Windows:

```bat
build_exe.bat
```

The packaged executable is written to the `dist` folder.

## Data model

Questions are stored in `data/questions.json`. Existing questions without a `type` field remain multiple-choice questions. Multiple-choice questions use this schema:

```json
{
  "id": "1201-3.6-001",
  "exam": "220-1201",
  "domain": "Hardware",
  "objective": "3.6 Given a scenario, install the appropriate power supply.",
  "question": "...",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "answer": "B",
  "explanation": "..."
}
```

Ordering PBQs use a list of items and the correct item order:

```json
{
  "type": "ordering",
  "question": "Put these steps in order.",
  "items": ["Connect power", "Install the CPU", "Apply thermal paste"],
  "answer": ["Install the CPU", "Apply thermal paste", "Connect power"]
}
```

Matching PBQs use left/right item lists and an answer object mapping each left item to a unique right item:

```json
{
  "type": "matching",
  "question": "Match each technology to its role.",
  "left_items": ["WPA3", "AES"],
  "right_items": ["Wireless security", "Encryption"],
  "answer": {
    "WPA3": "Wireless security",
    "AES": "Encryption"
  }
}
```

Drag-and-drop PBQs use draggable `items`, labeled `targets`, and an answer object assigning every item to a target. Multiple items may go into the same target:

```json
{
  "type": "drag_drop",
  "question": "Drag each cable to its maximum Ethernet segment length.",
  "items": ["Cat 5e", "Fiber optic"],
  "targets": ["100 meters", "2 kilometers"],
  "answer": {
    "Cat 5e": "100 meters",
    "Fiber optic": "2 kilometers"
  }
}
```

PBQ answers are all-or-nothing: the full order, every match, or every item assignment must be correct. PBQs can be created in the question editor or imported from JSON/CSV. For CSV imports, list fields may use pipe-separated items; matching answers use one `left item => right item` pair per line, and drag-and-drop answers use one `item => target` pair per line.

## Notes

This project includes a compact seed question bank designed to be expanded toward a larger, structured pool. The app is intentionally self-contained and works from a local JSON data file.
