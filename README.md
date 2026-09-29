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

Questions are stored in `data/questions.json` using this schema:

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

## Notes

This project includes a compact seed question bank designed to be expanded toward a larger, structured pool. The app is intentionally self-contained and works from a local JSON data file.
