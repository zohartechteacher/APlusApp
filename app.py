import csv
import json
import os
import random
import re
import sys
import time
import ctypes
import webbrowser
from ctypes import wintypes
from pathlib import Path

import customtkinter as ctk


try:
    from tkinter import filedialog, messagebox
except ImportError:  # pragma: no cover
    filedialog = None
    messagebox = None


APP_TITLE = "Zohar's A+ Practice Prep"
CONTACT_EMAIL = "zohartechteacher@gmail.com"
LINKEDIN_URL = "https://www.linkedin.com/in/zohar-laor-202772/"


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def get_app_icon_path() -> Path | None:
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "Zfav.ico")
        candidates.append(Path(sys.executable).resolve().with_name("Zfav.ico"))
    candidates.append(Path(__file__).resolve().parent / "Zfav.ico")
    candidates.append(Path.cwd() / "Zfav.ico")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_question_bank(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("questions", "items", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def get_question_bank_write_path(base_dir: Path) -> Path:
    if getattr(sys, "frozen", False):
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local_app_data / "Zohar" / "APlusPracticePrep" / "questions.json"
    return base_dir / "data" / "questions.json"


def append_question_to_payload(payload, question):
    if isinstance(payload, list):
        payload.append(question)
        return
    if isinstance(payload, dict):
        for key in ("questions", "items", "data"):
            if isinstance(payload.get(key), list):
                payload[key].append(question)
                metadata = payload.get("metadata")
                if isinstance(metadata, dict) and "total_questions" in metadata:
                    metadata["total_questions"] = len(payload[key])
                return
    raise ValueError("Question bank must be a list or contain a question list.")


def replace_question_in_payload(payload, question_id, replacement):
    if isinstance(payload, list):
        questions = payload
    elif isinstance(payload, dict):
        questions = next(
            (payload[key] for key in ("questions", "items", "data") if isinstance(payload.get(key), list)),
            None,
        )
    else:
        questions = None
    if questions is None:
        raise ValueError("Question bank must be a list or contain a question list.")

    for index, question in enumerate(questions):
        if question.get("id") == question_id:
            questions[index] = replacement
            return
    raise ValueError(f"Question {question_id} was not found in the bank.")


def remove_question_from_payload(payload, question_id):
    if isinstance(payload, list):
        questions = payload
    elif isinstance(payload, dict):
        questions = next(
            (payload[key] for key in ("questions", "items", "data") if isinstance(payload.get(key), list)),
            None,
        )
    else:
        questions = None
    if questions is None:
        raise ValueError("Question bank must be a list or contain a question list.")

    for index, question in enumerate(questions):
        if question.get("id") == question_id:
            removed_question = questions.pop(index)
            metadata = payload.get("metadata") if isinstance(payload, dict) else None
            if isinstance(metadata, dict) and "total_questions" in metadata:
                metadata["total_questions"] = len(questions)
            return removed_question
    raise ValueError(f"Question {question_id} was not found in the bank.")


def save_question_payload(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary_path.replace(path)


def normalize_import_question(question, row_number: int) -> dict:
    if not isinstance(question, dict):
        raise ValueError(f"Row {row_number}: each question must be an object.")

    values = {
        str(key).strip().lower().replace(" ", "_"): value
        for key, value in question.items()
    }
    prompt = values.get("question", values.get("prompt", ""))
    exam = str(values.get("exam", "")).strip()
    domain = str(values.get("domain", "")).strip()
    objective = str(values.get("objective", "")).strip()
    if not all((exam, domain, objective, str(prompt).strip())):
        raise ValueError(
            f"Row {row_number}: exam, domain, objective, and question are required."
        )
    if exam not in {"220-1201", "220-1202"}:
        raise ValueError(f"Row {row_number}: unsupported exam '{exam}'.")

    options = values.get("options")
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except json.JSONDecodeError:
            options = [option.strip() for option in options.split("|") if option.strip()]
    if not isinstance(options, list) or not options:
        options = [
            (values.get(f"option_{letter.lower()}") or "")
            for letter in "ABCDEF"
            if (values.get(f"option_{letter.lower()}") or "").strip()
        ]
    if not 2 <= len(options) <= 26:
        raise ValueError(f"Row {row_number}: provide between 2 and 26 options.")

    label_map = {}
    normalized_options = []
    for index, option in enumerate(options):
        option_text = str(option).strip()
        if not option_text:
            raise ValueError(f"Row {row_number}: answer options cannot be empty.")
        match = re.match(r"^\s*([A-Z])\)\s*(.*)$", option_text)
        original_label = match.group(1) if match else chr(ord("A") + index)
        text = match.group(2).strip() if match else option_text
        if original_label in label_map or not text:
            raise ValueError(f"Row {row_number}: options need unique labels and text.")
        new_label = chr(ord("A") + index)
        label_map[original_label] = new_label
        normalized_options.append(f"{new_label}) {text}")

    answers = values.get("answer", values.get("correct_answer", ""))
    if isinstance(answers, str):
        answer_text = answers.strip()
        if answer_text.startswith("["):
            try:
                answers = json.loads(answer_text)
            except json.JSONDecodeError:
                answers = answer_text
        if isinstance(answers, str):
            answers = [part.strip() for part in re.split(r"[,;|]", answers) if part.strip()]
    elif not isinstance(answers, (list, tuple, set)):
        answers = [answers]

    normalized_answers = []
    for answer in answers:
        answer_label = str(answer).split(")", 1)[0].strip().upper()
        if answer_label not in label_map:
            raise ValueError(f"Row {row_number}: answer '{answer}' does not match an option.")
        mapped_label = label_map[answer_label]
        if mapped_label not in normalized_answers:
            normalized_answers.append(mapped_label)
    if not normalized_answers:
        raise ValueError(f"Row {row_number}: provide at least one correct answer.")

    multi_select_value = values.get("multi_select", False)
    multi_select = (
        multi_select_value is True
        or str(multi_select_value).strip().casefold() in {"1", "true", "yes", "y"}
        or len(normalized_answers) > 1
    )
    result = {
        "exam": exam,
        "domain": domain,
        "objective": objective,
        "question": str(prompt).strip(),
        "options": normalized_options,
        "answer": normalized_answers if multi_select else normalized_answers[0],
        "explanation": str(values.get("explanation", "") or "").strip(),
    }
    if values.get("id"):
        result["id"] = str(values["id"]).strip()
    if multi_select:
        result["multi_select"] = True
    return result


def read_question_import_file(path: Path) -> list[dict]:
    if path.suffix.casefold() == ".json":
        payload = load_json(path)
        questions = load_question_bank(payload)
        if not questions and isinstance(payload, dict) and "question" in payload:
            questions = [payload]
    elif path.suffix.casefold() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            questions = list(csv.DictReader(handle))
    else:
        raise ValueError("Choose a .json or .csv question file.")

    if not questions:
        raise ValueError("The selected file contains no questions.")
    return [normalize_import_question(question, index) for index, question in enumerate(questions, 1)]


def question_content_key(question):
    exam = str(question.get("exam", "")).strip().casefold()
    prompt = " ".join(str(question.get("question", "")).split()).casefold()
    return (exam, prompt) if exam and prompt else None


def find_duplicate_question(questions, candidate, exclude_question=None):
    candidate_key = question_content_key(candidate)
    if candidate_key is None:
        return None
    return next(
        (
            question
            for question in questions
            if question is not exclude_question
            and question_content_key(question) == candidate_key
        ),
        None,
    )


def prepare_questions_for_import(existing_questions, imported_questions):
    used_ids = {str(question.get("id", "")).strip() for question in existing_questions}
    seen_content = {
        key
        for question in existing_questions
        if (key := question_content_key(question)) is not None
    }
    questions_to_add = []
    duplicate_count = 0

    for imported_question in imported_questions:
        question = dict(imported_question)
        question_id = str(question.get("id", "") or "").strip()
        if not question_id:
            objective_match = re.match(r"^\s*(\d+(?:\.\d+)?)", question["objective"])
            objective_code = objective_match.group(1) if objective_match else "custom"
            prefix = f"{question['exam'][-4:]}-{objective_code}-"
            sequence = 1
            while f"{prefix}{sequence:03d}" in used_ids:
                sequence += 1
            question_id = f"{prefix}{sequence:03d}"
            question["id"] = question_id

        content_key = question_content_key(question)
        if question_id in used_ids or (content_key is not None and content_key in seen_content):
            duplicate_count += 1
            continue

        used_ids.add(question_id)
        if content_key is not None:
            seen_content.add(content_key)
        questions_to_add.append(question)

    return questions_to_add, duplicate_count


def normalize_domain_name(domain: str) -> str:
    if not isinstance(domain, str):
        return str(domain)

    candidate = domain.strip()
    if not candidate:
        return candidate

    if re.match(r"^\d+(?:\.\d+)?\s+", candidate):
        candidate = re.sub(r"^\d+(?:\.\d+)?\s+", "", candidate)
    return candidate.strip()


class ExamSession:
    def __init__(self, questions, timer_mode: str, study_mode: bool = False):
        self.questions = [self.shuffle_question_options(question) for question in questions]
        self.timer_mode = timer_mode
        self.study_mode = study_mode
        self.current_index = 0
        self.answers = {}
        self.flagged = set()
        self.started_at = time.time()
        self.time_limit = self._resolve_time_limit(timer_mode)
        self.remaining_seconds = self.time_limit

    @staticmethod
    def shuffle_question_options(question):
        shuffled_question = dict(question)
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            return shuffled_question

        parsed_options = []
        original_labels = set()
        for option in options:
            match = re.match(r"^\s*([A-Z])\)\s*(.*)$", str(option))
            if match is None or match.group(1) in original_labels:
                return shuffled_question
            original_labels.add(match.group(1))
            parsed_options.append((match.group(1), match.group(2)))

        if question.get("multi_select"):
            correct_labels = ExamSession.normalize_answer_set(question.get("answer"))
        else:
            answer = ExamSession.answer_letter(question.get("answer"))
            correct_labels = {answer} if answer else set()
        if not correct_labels or not correct_labels.issubset(original_labels):
            return shuffled_question

        random.shuffle(parsed_options)
        remapped_labels = {}
        shuffled_question["options"] = []
        for index, (original_label, option_text) in enumerate(parsed_options):
            new_label = chr(ord("A") + index)
            remapped_labels[original_label] = new_label
            shuffled_question["options"].append(f"{new_label}) {option_text}")

        if question.get("multi_select"):
            shuffled_question["answer"] = sorted(remapped_labels[label] for label in correct_labels)
        else:
            shuffled_question["answer"] = remapped_labels[next(iter(correct_labels))]
        return shuffled_question

    @staticmethod
    def _resolve_time_limit(timer_mode: str) -> int:
        mode_map = {
            "untimed": 0,
            "30s": 30,
            "90m": 90 * 60,
        }
        return mode_map.get(timer_mode, 0)

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    def current_question(self):
        if not self.questions:
            return None
        return self.questions[self.current_index]

    @staticmethod
    def answer_letter(answer):
        if answer is None:
            return ""
        if isinstance(answer, (list, tuple, set)):
            return "|".join(sorted(str(item).split(")", 1)[0].strip().upper() for item in answer if item))
        value = str(answer).strip()
        if not value:
            return ""
        return value.split(")", 1)[0].strip().upper()

    @staticmethod
    def normalize_answer_set(answer):
        if answer is None:
            return set()
        if isinstance(answer, str):
            if "," in answer:
                raw_values = [part.strip() for part in answer.split(",") if part.strip()]
            else:
                raw_values = [answer]
        elif isinstance(answer, (list, tuple, set)):
            raw_values = list(answer)
        else:
            raw_values = [answer]

        normalized = set()
        for value in raw_values:
            if value is None:
                continue
            letter = ExamSession.answer_letter(value)
            if letter:
                normalized.add(letter)
        return normalized

    def record_answer(self, answer):
        self.answers[str(self.current_index)] = answer

    def mark_flagged(self, value: bool):
        if value:
            self.flagged.add(self.current_index)
        else:
            self.flagged.discard(self.current_index)

    def is_answered(self, idx: int) -> bool:
        return str(idx) in self.answers

    def is_flagged(self, idx: int) -> bool:
        return idx in self.flagged

    def compute_results(self):
        correct = 0
        detail = []
        objective_scores = {}
        objective_results = {}
        total = len(self.questions)

        for index, question in enumerate(self.questions):
            chosen = self.answers.get(str(index), "")
            if question.get("multi_select"):
                correct_flag = self.normalize_answer_set(chosen) == self.normalize_answer_set(question["answer"])
            else:
                correct_flag = self.answer_letter(chosen) == self.answer_letter(question["answer"])
            if correct_flag:
                correct += 1

            domain = question["domain"]
            objective_scores.setdefault(domain, {"correct": 0, "total": 0})
            objective_scores[domain]["total"] += 1
            if correct_flag:
                objective_scores[domain]["correct"] += 1

            objective = question["objective"]
            objective_results.setdefault(objective, {"correct": 0, "total": 0})
            objective_results[objective]["total"] += 1
            if correct_flag:
                objective_results[objective]["correct"] += 1

            detail.append(
                {
                    "question": question,
                    "selected": chosen,
                    "correct": question["answer"],
                    "is_correct": correct_flag,
                }
            )

        raw_percent = (correct / total) * 100 if total else 0
        scaled_score = int(round(raw_percent * 9))
        return {
            "correct": correct,
            "total": total,
            "raw_percent": raw_percent,
            "scaled_score": scaled_score,
            "objective_scores": objective_scores,
            "objective_results": objective_results,
            "details": detail,
        }


class APlusPracticeApp(ctk.CTk):
    def __init__(self):
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "Zohar.APlusPracticePrep"
                )
            except Exception:
                pass
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title(APP_TITLE)
        self.geometry("1280x860")
        self.minsize(1100, 700)
        self.configure(fg_color="#0F172A")
        self.after_idle(self.set_taskbar_icon)

        self.base_dir = get_base_dir()
        self.data_dir = self.base_dir / "data"
        self.question_bank_write_path = get_question_bank_write_path(self.base_dir)
        question_bank_path = (
            self.question_bank_write_path
            if self.question_bank_write_path.exists()
            else self.data_dir / "questions.json"
        )
        self.question_data = load_json(question_bank_path)
        self.bank = load_question_bank(self.question_data)
        self.metadata = load_json(self.data_dir / "exam_metadata.json")

        self.current_session = None
        self.question_count_var = None
        self.exam_var = None
        self.objective_mode_var = None
        self.timer_var = None
        self.study_mode_var = None
        self.objective_checkboxes = []
        self.current_question_var = None
        self.option_var = None
        self.option_buttons = []
        self.palette_buttons = []
        self.timer_after_id = None
        self.feedback_label = None

        self.setup_frames()
        self.show_setup_screen()

    def set_taskbar_icon(self):
        icon_path = get_app_icon_path()
        if icon_path is None:
            return

        try:
            self.iconbitmap(str(icon_path))
        except Exception:
            pass

        if sys.platform != "win32":
            return

        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            load_image = user32.LoadImageW
            load_image.argtypes = (
                wintypes.HINSTANCE,
                wintypes.LPCWSTR,
                wintypes.UINT,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            )
            load_image.restype = wintypes.HANDLE
            icon_handle = load_image(
                None, str(icon_path), 1, 0, 0, 0x10 | 0x40
            )
            if not icon_handle:
                return

            send_message = user32.SendMessageW
            send_message.argtypes = (
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )
            send_message.restype = ctypes.c_ssize_t
            window_handle = self.winfo_id()
            send_message(window_handle, 0x0080, 0, icon_handle)
            send_message(window_handle, 0x0080, 1, icon_handle)
            self._taskbar_icon_handle = icon_handle
        except Exception:
            pass

    def setup_frames(self):
        self.root_container = ctk.CTkFrame(self, fg_color="transparent")
        self.root_container.pack(fill="both", expand=True, padx=18, pady=18)

        self.setup_frame = ctk.CTkFrame(self.root_container, corner_radius=18, border_width=1)
        self.exam_frame = ctk.CTkFrame(self.root_container, corner_radius=18, border_width=1)
        self.results_frame = ctk.CTkFrame(self.root_container, corner_radius=18, border_width=1)

        self.setup_frame.pack(fill="both", expand=True)
        self.exam_frame.pack(fill="both", expand=True)
        self.results_frame.pack(fill="both", expand=True)

        self.setup_frame.pack_forget()
        self.exam_frame.pack_forget()
        self.results_frame.pack_forget()

        self.build_setup_screen()
        self.build_exam_screen()
        self.build_results_screen()

    def build_setup_screen(self):
        brand_header = ctk.CTkFrame(self.setup_frame, fg_color="#111C31", corner_radius=18, border_width=1, border_color="#263B5C")
        brand_header.pack(fill="x", padx=20, pady=(20, 16))

        brand_copy = ctk.CTkFrame(brand_header, fg_color="transparent")
        brand_copy.pack(side="left", fill="both", expand=True, padx=22, pady=18)
        contact_row = ctk.CTkFrame(brand_copy, fg_color="transparent")
        contact_row.pack(anchor="w", pady=(0, 6))
        email_link = ctk.CTkLabel(
            contact_row,
            text=f"Email: {CONTACT_EMAIL}",
            text_color="#67E8F9",
            font=ctk.CTkFont(family="Aptos Display", size=11, weight="bold"),
            cursor="hand2",
        )
        email_link.pack(side="left")
        email_link.bind(
            "<Button-1>",
            lambda _event: webbrowser.open(f"mailto:{CONTACT_EMAIL}"),
        )
        email_link.bind(
            "<Enter>", lambda _event: email_link.configure(text_color="#A5F3FC")
        )
        email_link.bind(
            "<Leave>", lambda _event: email_link.configure(text_color="#67E8F9")
        )
        ctk.CTkLabel(
            contact_row,
            text=" | ",
            text_color="#AFC1D8",
            font=ctk.CTkFont(family="Aptos Display", size=11, weight="bold"),
        ).pack(side="left")
        linkedin_link = ctk.CTkLabel(
            contact_row,
            text="LinkedIn",
            text_color="#67E8F9",
            font=ctk.CTkFont(family="Aptos Display", size=11, weight="bold"),
            cursor="hand2",
        )
        linkedin_link.pack(side="left")
        linkedin_link.bind(
            "<Button-1>", lambda _event: webbrowser.open(LINKEDIN_URL)
        )
        linkedin_link.bind(
            "<Enter>", lambda _event: linkedin_link.configure(text_color="#A5F3FC")
        )
        linkedin_link.bind(
            "<Leave>", lambda _event: linkedin_link.configure(text_color="#67E8F9")
        )
        ctk.CTkLabel(
            brand_copy,
            text="Zohar's A+ Practice Prep",
            font=ctk.CTkFont(family="Aptos Display", size=30, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_copy,
            text="A focused practice room for building real exam confidence.",
            text_color="#AFC1D8",
            font=ctk.CTkFont(family="Aptos Display", size=14),
        ).pack(anchor="w", pady=(5, 0))

        brand_stats = ctk.CTkFrame(brand_header, fg_color="#0C1424", corner_radius=14)
        brand_stats.pack(side="right", padx=18, pady=14)
        self.bank_count_label = ctk.CTkLabel(brand_stats, text=f"{len(self.bank):,}", text_color="#FCD34D", font=ctk.CTkFont(family="Aptos Display", size=24, weight="bold"))
        self.bank_count_label.pack(padx=20, pady=(12, 0))
        ctk.CTkLabel(brand_stats, text="practice questions", text_color="#AFC1D8", font=ctk.CTkFont(size=11)).pack(padx=20, pady=(0, 6))
        ctk.CTkButton(brand_stats, text="Add question", command=self.open_question_editor, width=150, height=32, fg_color="#0E7490", hover_color="#155E75").pack(padx=12, pady=(0, 12))
        ctk.CTkButton(brand_stats, text="Edit questions", command=self.open_question_manager, width=150, height=32).pack(padx=12, pady=(0, 12))

        main = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        left = ctk.CTkFrame(main, corner_radius=18, border_width=1)
        left.pack(side="left", fill="y", padx=(0, 16), ipadx=14, ipady=8)
        right = ctk.CTkFrame(main, corner_radius=18, border_width=1)
        right.pack(side="left", fill="both", expand=True, ipadx=14, ipady=8)

        ctk.CTkLabel(left, text="Build your session", text_color="#67E8F9", font=ctk.CTkFont(family="Aptos Display", size=18, weight="bold")).pack(anchor="w", padx=16, pady=(16, 10))
        ctk.CTkLabel(left, text="Exam selection", text_color="#AFC1D8", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(0, 8))
        self.exam_var = ctk.StringVar(value="220-1201")
        ctk.CTkOptionMenu(
            left,
            values=["220-1201", "220-1202", "Combined / Practice Both"],
            variable=self.exam_var,
            width=220,
            height=36,
            font=ctk.CTkFont(size=14),
            command=lambda *_: self.on_exam_selection_changed(),
        ).pack(anchor="w", padx=16, pady=(0, 16))

        ctk.CTkLabel(left, text="Timer config", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=16, pady=(8, 8))
        self.timer_var = ctk.StringVar(value="90m")
        for label, value in (("No Timer", "untimed"), ("30 Seconds per Question", "30s"), ("90 Minutes", "90m")):
            ctk.CTkRadioButton(left, text=label, variable=self.timer_var, value=value, font=ctk.CTkFont(size=13)).pack(anchor="w", padx=18, pady=4)

        ctk.CTkLabel(left, text="Practice mode", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=16, pady=(14, 8))
        self.study_mode_var = ctk.StringVar(value="exam")
        ctk.CTkRadioButton(left, text="Exam Mode", variable=self.study_mode_var, value="exam", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=18, pady=4)
        ctk.CTkRadioButton(left, text="Study Mode (reveal answers)", variable=self.study_mode_var, value="study", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=18, pady=4)

        ctk.CTkLabel(right, text="Tune your focus", text_color="#67E8F9", font=ctk.CTkFont(family="Aptos Display", size=18, weight="bold")).pack(anchor="w", padx=16, pady=(16, 8))
        ctk.CTkLabel(right, text="Objective filter", text_color="#AFC1D8", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(0, 2))
        self.objective_mode_var = ctk.StringVar(value="official")
        ctk.CTkRadioButton(right, text="Official Exam Format", variable=self.objective_mode_var, value="official", command=self.populate_objective_options).pack(anchor="w", padx=18, pady=4)
        ctk.CTkRadioButton(right, text="Specific objectives only", variable=self.objective_mode_var, value="specific", command=self.populate_objective_options).pack(anchor="w", padx=18, pady=(4, 12))

        self.objective_options_frame = ctk.CTkScrollableFrame(right, width=560, height=340)
        self.objective_options_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        info = ctk.CTkFrame(right, corner_radius=12, fg_color="#1F2A3D")
        info.pack(fill="x", padx=16, pady=(0, 10))
        question_count_header = ctk.CTkFrame(info, fg_color="transparent")
        question_count_header.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(question_count_header, text="Question count", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(question_count_header, text="Begin practice  >", command=self.start_exam, width=190, height=36, fg_color="#0E7490", hover_color="#155E75", font=ctk.CTkFont(family="Aptos Display", size=14, weight="bold")).pack(side="right")

        self.question_count_var = ctk.IntVar(value=25)
        self.question_count_slider = ctk.CTkSlider(info, from_=10, to=1000, number_of_steps=990, variable=self.question_count_var, width=440)
        self.question_count_slider.pack(anchor="w", padx=16, pady=(0, 6))
        self.question_count_value = ctk.CTkLabel(info, text="25 questions", font=ctk.CTkFont(size=13))
        self.question_count_value.pack(anchor="w", padx=16, pady=(0, 6))
        self.pool_count_label = ctk.CTkLabel(info, text="Available in pool: 0 questions", font=ctk.CTkFont(size=12), text_color="#93C5FD")
        self.pool_count_label.pack(anchor="w", padx=16, pady=(0, 12))
        self.question_count_slider.configure(command=self.update_question_count_label)
        self.populate_objective_options()
        self.update_question_count_limits()
        self.update_question_count_label(self.question_count_var.get())

        ctk.CTkFrame(self.setup_frame, height=8, fg_color="transparent").pack(fill="x")

    def on_exam_selection_changed(self):
        self.populate_objective_options()
        self.update_question_count_limits()

    def import_questions_from_file(self, parent, refresh_callback):
        if filedialog is None:
            messagebox.showerror("Import unavailable", "The file picker is not available.", parent=parent)
            return

        selected_path = filedialog.askopenfilename(
            parent=parent,
            title="Import questions",
            filetypes=[("Question files", "*.json *.csv"), ("JSON files", "*.json"), ("CSV files", "*.csv")],
        )
        if not selected_path:
            return

        try:
            imported_questions = read_question_import_file(Path(selected_path))
        except (OSError, UnicodeError, csv.Error, json.JSONDecodeError, ValueError) as error:
            messagebox.showerror("Could not import questions", str(error), parent=parent)
            return

        questions_to_add, duplicate_count = prepare_questions_for_import(
            self.bank, imported_questions
        )

        if not questions_to_add:
            messagebox.showinfo(
                "No new questions",
                f"The file had no new questions. Skipped {duplicate_count} duplicate question(s).",
                parent=parent,
            )
            return

        confirmation = f"Import {len(questions_to_add)} question(s)?"
        if duplicate_count:
            confirmation += f"\n\n{duplicate_count} duplicate question(s) will be skipped."
        if not messagebox.askyesno("Confirm import", confirmation, parent=parent):
            return

        appended_ids = []
        try:
            for question in questions_to_add:
                append_question_to_payload(self.question_data, question)
                appended_ids.append(question["id"])
            save_question_payload(self.question_bank_write_path, self.question_data)
        except (OSError, TypeError, ValueError) as error:
            for question_id in reversed(appended_ids):
                try:
                    remove_question_from_payload(self.question_data, question_id)
                except ValueError:
                    pass
            messagebox.showerror("Could not save imported questions", str(error), parent=parent)
            return

        self.bank_count_label.configure(text=f"{len(self.bank):,}")
        self.populate_objective_options()
        refresh_callback()
        messagebox.showinfo(
            "Import complete",
            f"Imported {len(questions_to_add)} question(s)."
            + (f" Skipped {duplicate_count} duplicate question(s)." if duplicate_count else ""),
            parent=parent,
        )

    def show_question_import_format(self, parent):
        dialog = ctk.CTkToplevel(parent)
        dialog.title("Question import format")
        dialog.geometry("820x760")
        dialog.minsize(680, 600)
        dialog.transient(parent)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Question import format",
            font=ctk.CTkFont(family="Aptos Display", size=22, weight="bold"),
        ).pack(anchor="w", padx=22, pady=(18, 4))
        ctk.CTkLabel(
            dialog,
            text="Required fields: exam, domain, objective, question, options, and answer. IDs and explanations are optional.",
            text_color="#AFC1D8",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 12))

        examples = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        examples.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        csv_text = (
            "exam,domain,objective,question,option_a,option_b,option_c,answer,explanation\n"
            '220-1201,Hardware,3.2 Storage,Which is an SSD?,SSD,HDD,Printer,A,Flash storage\n'
        )
        json_text = json.dumps(
            {
                "questions": [
                    {
                        "exam": "220-1201",
                        "domain": "Hardware",
                        "objective": "3.2 Storage",
                        "question": "Which are storage devices?",
                        "options": ["A) SSD", "B) HDD", "C) Printer"],
                        "answer": ["A", "B"],
                        "multi_select": True,
                        "explanation": "SSDs and HDDs store data.",
                    }
                ]
            },
            indent=2,
        )

        def add_example(title, content, copy_label):
            ctk.CTkLabel(
                examples,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(anchor="w", padx=6, pady=(10, 4))
            code_box = ctk.CTkTextbox(examples, height=110 if title == "CSV" else 310, wrap="none")
            code_box.pack(fill="x", padx=6)
            code_box.insert("1.0", content)
            code_box.configure(state="disabled")

            def copy_example():
                dialog.clipboard_clear()
                dialog.clipboard_append(content)

            ctk.CTkButton(
                examples,
                text=copy_label,
                width=130,
                command=copy_example,
            ).pack(anchor="e", padx=6, pady=(5, 2))

        add_example("CSV", csv_text, "Copy CSV example")
        add_example("JSON", json_text, "Copy JSON example")
        ctk.CTkButton(dialog, text="Close", command=dialog.destroy, width=100).pack(
            anchor="e", padx=22, pady=(0, 18)
        )

    def open_question_manager(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit questions")
        dialog.geometry("900x720")
        dialog.minsize(680, 520)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Edit a question",
            font=ctk.CTkFont(family="Aptos Display", size=24, weight="bold"),
        ).pack(anchor="w", padx=22, pady=(18, 3))

        filters = ctk.CTkFrame(dialog, fg_color="transparent")
        filters.pack(fill="x", padx=22, pady=(8, 6))
        search_entry = ctk.CTkEntry(
            filters,
            placeholder_text="Search question, objective, domain, or ID",
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        exam_var = ctk.StringVar(value="All exams")
        ctk.CTkOptionMenu(
            filters,
            values=["All exams", "220-1201", "220-1202"],
            variable=exam_var,
            width=150,
            command=lambda *_: refresh_questions(),
        ).pack(side="right")
        ctk.CTkButton(
            filters,
            text="Import",
            width=100,
            command=lambda: self.import_questions_from_file(dialog, refresh_questions),
        ).pack(side="right", padx=(0, 8))
        format_link = ctk.CTkLabel(
            filters,
            text="Format",
            text_color="#67E8F9",
            font=ctk.CTkFont(family="Aptos Display", size=12, underline=True),
            cursor="hand2",
        )
        format_link.pack(side="right", padx=(0, 10))
        format_link.bind(
            "<Button-1>", lambda _event: self.show_question_import_format(dialog)
        )
        format_link.bind(
            "<Enter>", lambda _event: format_link.configure(text_color="#A5F3FC")
        )
        format_link.bind(
            "<Leave>", lambda _event: format_link.configure(text_color="#67E8F9")
        )

        result_count = ctk.CTkLabel(dialog, text_color="#AFC1D8")
        result_count.pack(anchor="w", padx=24, pady=(0, 6))
        results_frame = ctk.CTkScrollableFrame(dialog)
        results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        def select_question(question):
            dialog.withdraw()
            self.open_question_editor(
                question,
                return_to_manager=dialog,
                on_return=refresh_questions,
            )

        def delete_question(question):
            question_id = question.get("id", "No ID")
            prompt = question.get("question", "")[:220]
            confirmed = messagebox.askyesno(
                "Delete question",
                f"Delete {question_id}?\n\n{prompt}\n\nThis cannot be undone.",
                parent=dialog,
            )
            if not confirmed:
                return

            question_index = next(
                (index for index, entry in enumerate(self.bank) if entry.get("id") == question_id),
                None,
            )
            try:
                removed_question = remove_question_from_payload(self.question_data, question_id)
                save_question_payload(self.question_bank_write_path, self.question_data)
            except (OSError, ValueError, TypeError) as error:
                if question_index is not None and all(
                    entry.get("id") != question_id for entry in self.bank
                ):
                    self.bank.insert(question_index, question)
                    metadata = self.question_data.get("metadata") if isinstance(self.question_data, dict) else None
                    if isinstance(metadata, dict) and "total_questions" in metadata:
                        metadata["total_questions"] = len(self.bank)
                messagebox.showerror("Could not delete question", str(error), parent=dialog)
                refresh_questions()
                return

            self.bank_count_label.configure(text=f"{len(self.bank):,}")
            self.populate_objective_options()
            refresh_questions()
            messagebox.showinfo(
                "Question deleted",
                f"Question {removed_question.get('id', question_id)} was deleted.",
                parent=dialog,
            )

        def refresh_questions(*_):
            for child in results_frame.winfo_children():
                child.destroy()
            query = search_entry.get().strip().casefold()
            selected_exam = exam_var.get()
            matches = [
                question
                for question in reversed(self.bank)
                if (selected_exam == "All exams" or question.get("exam") == selected_exam)
                and (
                    not query
                    or query
                    in " ".join(
                        str(question.get(field, ""))
                        for field in ("id", "exam", "domain", "objective", "question")
                    ).casefold()
                )
            ]
            result_count.configure(
                text=f"{len(matches):,} matching questions"
                + ("; showing the first 100" if len(matches) > 100 else "")
            )
            for question in matches[:100]:
                row = ctk.CTkFrame(results_frame, corner_radius=8)
                row.pack(fill="x", padx=4, pady=3)
                ctk.CTkLabel(
                    row,
                    text=f"{question.get('id', 'No ID')}  ·  {question.get('exam', '')}  ·  {question.get('objective', '')}",
                    text_color="#93C5FD",
                    anchor="w",
                ).pack(fill="x", padx=12, pady=(8, 2))
                actions = ctk.CTkFrame(row, fg_color="transparent")
                actions.pack(fill="x", padx=6, pady=(0, 6))
                actions.grid_columnconfigure(0, weight=1)
                ctk.CTkButton(
                    actions,
                    text=question.get("question", "")[:180],
                    anchor="w",
                    height=38,
                    fg_color="transparent",
                    hover_color="#263B5C",
                    command=lambda selected=question: select_question(selected),
                ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
                ctk.CTkButton(
                    actions,
                    text="Delete",
                    width=76,
                    height=34,
                    fg_color="#7F1D1D",
                    hover_color="#991B1B",
                    command=lambda selected=question: delete_question(selected),
                ).grid(row=0, column=1, sticky="e")
            if not matches:
                ctk.CTkLabel(
                    results_frame,
                    text="No questions match those filters.",
                    text_color="#AFC1D8",
                ).pack(anchor="w", padx=12, pady=16)

        search_entry.bind("<KeyRelease>", refresh_questions)
        refresh_questions()
        ctk.CTkButton(dialog, text="Close", command=dialog.destroy, width=110).pack(
            anchor="e", padx=22, pady=(0, 18)
        )

    def open_question_editor(
        self, existing_question=None, return_to_manager=None, on_return=None
    ):
        is_editing = existing_question is not None
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit question" if is_editing else "Add a question")
        dialog.geometry("880x800")
        dialog.minsize(700, 620)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Edit a practice question" if is_editing else "Add a practice question",
            font=ctk.CTkFont(family="Aptos Display", size=24, weight="bold"),
        ).pack(anchor="w", padx=22, pady=(18, 2))
        ctk.CTkLabel(
            dialog,
            text="Questions are saved to your local question bank.",
            text_color="#AFC1D8",
        ).pack(anchor="w", padx=22, pady=(0, 12))

        form = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        def add_field_label(text):
            ctk.CTkLabel(
                form, text=text, font=ctk.CTkFont(size=13, weight="bold")
            ).pack(anchor="w", padx=6, pady=(10, 5))

        metadata_exams = [exam for exam in ("220-1201", "220-1202") if exam in self.metadata]
        if is_editing and existing_question.get("exam") not in metadata_exams:
            metadata_exams.append(existing_question.get("exam"))
        if not metadata_exams:
            metadata_exams = ["220-1201", "220-1202"]
        initial_exam = existing_question.get("exam") if is_editing else metadata_exams[0]
        exam_var = ctk.StringVar(value=initial_exam)

        def domains_for_exam(exam):
            return sorted(
                {
                    normalize_domain_name(domain)
                    for domain in self.metadata.get(exam, {}).get("objective_domains", [])
                }
            ) or ["Other"]

        domain_values = domains_for_exam(exam_var.get())
        initial_domain = existing_question.get("domain") if is_editing else domain_values[0]
        if initial_domain not in domain_values:
            domain_values.append(initial_domain)
        domain_var = ctk.StringVar(value=initial_domain)

        def update_domain_options(exam):
            values = domains_for_exam(exam)
            domain_menu.configure(values=values)
            if domain_var.get() not in values:
                domain_var.set(values[0])

        add_field_label("Exam")
        ctk.CTkOptionMenu(
            form,
            values=metadata_exams,
            variable=exam_var,
            width=220,
            command=update_domain_options,
        ).pack(anchor="w", padx=6)
        add_field_label("Domain")
        domain_menu = ctk.CTkOptionMenu(form, values=domain_values, variable=domain_var, width=360)
        domain_menu.pack(anchor="w", padx=6)

        add_field_label("Objective")
        objective_entry = ctk.CTkEntry(form, placeholder_text="For example: 3.2 Install and configure storage devices")
        objective_entry.pack(fill="x", padx=6)
        if is_editing:
            objective_entry.insert(0, existing_question.get("objective", ""))

        add_field_label("Question")
        question_box = ctk.CTkTextbox(form, height=105, wrap="word")
        question_box.pack(fill="x", padx=6)
        if is_editing:
            question_box.insert("1.0", existing_question.get("question", ""))

        add_field_label("Answer choices")
        existing_answer = existing_question.get("answer") if is_editing else None
        is_multi_select = bool(existing_question.get("multi_select")) if is_editing else False
        if is_editing and isinstance(existing_answer, (list, tuple, set)):
            is_multi_select = True
        correct_letters = (
            ExamSession.normalize_answer_set(existing_answer)
            if is_multi_select
            else {ExamSession.answer_letter(existing_answer)}
        )
        multiple_answers_var = ctk.BooleanVar(value=is_multi_select)
        ctk.CTkCheckBox(
            form,
            text="Allow multiple correct answers",
            variable=multiple_answers_var,
        ).pack(anchor="w", padx=6, pady=(0, 6))
        options_frame = ctk.CTkFrame(form, fg_color="transparent")
        options_frame.pack(fill="x", padx=2)
        option_rows = []

        existing_options = []
        if is_editing:
            for option in existing_question.get("options", []):
                match = re.match(r"^\s*([A-Z])\)\s*(.*)$", str(option))
                if match:
                    existing_options.append((match.group(1), match.group(2)))
        if not existing_options:
            existing_options = [(chr(ord("A") + index), "") for index in range(4)]
        option_limit = max(6, len(existing_options))

        def add_option(value="", is_correct=False):
            if len(option_rows) >= min(option_limit, 26):
                return
            index = len(option_rows)
            row = ctk.CTkFrame(options_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=f"{chr(ord('A') + index)})", width=28).pack(side="left")
            entry = ctk.CTkEntry(row, placeholder_text=f"Choice {chr(ord('A') + index)}")
            entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
            if value:
                entry.insert(0, value)
            correct_var = ctk.BooleanVar(value=is_correct)
            ctk.CTkCheckBox(row, text="Correct", variable=correct_var, width=90).pack(side="right")
            option_rows.append((row, entry, correct_var))

        def remove_option():
            if len(option_rows) <= 2:
                return
            row, _, _ = option_rows.pop()
            row.destroy()

        for letter, value in existing_options:
            add_option(value, letter in correct_letters)
        option_actions = ctk.CTkFrame(form, fg_color="transparent")
        option_actions.pack(anchor="w", padx=6, pady=(5, 0))
        ctk.CTkButton(option_actions, text="Add choice", width=110, command=add_option).pack(side="left")
        ctk.CTkButton(option_actions, text="Remove last", width=110, command=remove_option).pack(side="left", padx=8)

        add_field_label("Explanation (optional)")
        explanation_box = ctk.CTkTextbox(form, height=80, wrap="word")
        explanation_box.pack(fill="x", padx=6, pady=(0, 8))
        if is_editing:
            explanation_box.insert("1.0", existing_question.get("explanation", ""))

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.pack(fill="x", padx=22, pady=(2, 18))

        def close_editor():
            dialog.destroy()
            if return_to_manager is not None:
                return_to_manager.deiconify()
                return_to_manager.grab_set()
                if on_return is not None:
                    on_return()

        dialog.protocol("WM_DELETE_WINDOW", close_editor)

        def save_question():
            objective = objective_entry.get().strip()
            prompt = question_box.get("1.0", "end").strip()
            options = [entry.get().strip() for _, entry, _ in option_rows]
            correct_indexes = [
                index for index, (_, _, correct_var) in enumerate(option_rows) if correct_var.get()
            ]
            if not objective or not prompt:
                messagebox.showwarning("Question details needed", "Enter both an objective and a question.", parent=dialog)
                return
            if any(not option for option in options):
                messagebox.showwarning("Incomplete choices", "Fill in every answer choice before saving.", parent=dialog)
                return
            if not correct_indexes:
                messagebox.showwarning("Correct answer needed", "Mark at least one choice as correct.", parent=dialog)
                return
            if not multiple_answers_var.get() and len(correct_indexes) != 1:
                messagebox.showwarning("Choose one answer", "Mark exactly one correct choice, or enable multiple correct answers.", parent=dialog)
                return

            exam = exam_var.get()
            answer_letters = [chr(ord("A") + index) for index in correct_indexes]
            question = {
                "id": existing_question.get("id") if is_editing else "",
                "exam": exam,
                "domain": domain_var.get(),
                "objective": objective,
                "question": prompt,
                "options": [f"{chr(ord('A') + index)}) {option}" for index, option in enumerate(options)],
                "answer": answer_letters if multiple_answers_var.get() else answer_letters[0],
                "explanation": explanation_box.get("1.0", "end").strip(),
            }
            if multiple_answers_var.get():
                question["multi_select"] = True

            duplicate = find_duplicate_question(
                self.bank,
                question,
                exclude_question=existing_question if is_editing else None,
            )
            if duplicate is not None:
                duplicate_id = duplicate.get("id", "an existing question")
                messagebox.showwarning(
                    "Duplicate question",
                    f"This prompt already exists for {exam} (ID: {duplicate_id}).",
                    parent=dialog,
                )
                return

            try:
                if is_editing:
                    replace_question_in_payload(
                        self.question_data, existing_question.get("id"), question
                    )
                else:
                    objective_match = re.match(r"^\s*(\d+(?:\.\d+)?)", objective)
                    objective_code = objective_match.group(1) if objective_match else "custom"
                    identifier_prefix = f"{exam[-4:]}-{objective_code}-"
                    used_ids = {entry.get("id") for entry in self.bank}
                    sequence = 1
                    while f"{identifier_prefix}{sequence:03d}" in used_ids:
                        sequence += 1
                    question["id"] = f"{identifier_prefix}{sequence:03d}"
                    append_question_to_payload(self.question_data, question)
                save_question_payload(self.question_bank_write_path, self.question_data)
            except (OSError, ValueError, TypeError) as error:
                if is_editing:
                    try:
                        replace_question_in_payload(
                            self.question_data, existing_question.get("id"), existing_question
                        )
                    except ValueError:
                        pass
                elif self.bank and self.bank[-1] is question:
                    self.bank.pop()
                messagebox.showerror("Could not save question", str(error), parent=dialog)
                return

            close_editor()
            self.bank_count_label.configure(text=f"{len(self.bank):,}")
            self.populate_objective_options()
            status = "updated" if is_editing else "added"
            messagebox.showinfo(
                "Question updated" if is_editing else "Question added",
                f"Question {question['id']} {status}.",
                parent=return_to_manager or self,
            )

        ctk.CTkButton(footer, text="Cancel", command=close_editor, width=110).pack(side="right")
        ctk.CTkButton(
            footer,
            text="Save changes" if is_editing else "Save question",
            command=save_question,
            width=150,
            fg_color="#0E7490",
            hover_color="#155E75",
        ).pack(side="right", padx=(0, 10))

    def populate_objective_options(self):
        for child in self.objective_options_frame.winfo_children():
            child.destroy()

        self.objective_checkboxes = []

        if self.objective_mode_var.get() == "official":
            labels = []
            selected_exam = self.exam_var.get()
            if selected_exam == "Combined / Practice Both":
                exams = ["220-1201", "220-1202"]
            else:
                exams = [selected_exam]
            for exam in exams:
                for domain in self.metadata.get(exam, {}).get("objective_domains", []):
                    labels.append(f"{exam} • {normalize_domain_name(domain)}")
            if not labels:
                labels = ["No official domains available"]
            for label in labels:
                row = ctk.CTkCheckBox(self.objective_options_frame, text=label, variable=ctk.BooleanVar(value=True), onvalue=True, offvalue=False)
                row.pack(anchor="w", padx=14, pady=4)
                self.objective_checkboxes.append(row)
            self.update_question_count_limits()
            return

        available = []
        selected_exam = self.exam_var.get()
        exams = ["220-1201", "220-1202"] if selected_exam == "Combined / Practice Both" else [selected_exam]
        for exam in exams:
            seen = set()
            for question in self.bank:
                if question.get("exam") != exam:
                    continue
                objective = question.get("objective")
                domain = question.get("domain")
                if objective and objective not in seen:
                    available.append(f"{exam} • {domain} • {objective}")
                    seen.add(objective)
        if not available:
            available = ["No objectives available for this exam selection"]
        for label in available:
            row = ctk.CTkCheckBox(self.objective_options_frame, text=label, variable=ctk.BooleanVar(value=True), onvalue=True, offvalue=False)
            row.pack(anchor="w", padx=14, pady=4)
            self.objective_checkboxes.append(row)
        self.update_question_count_limits()

    def update_question_count_label(self, value):
        self.question_count_value.configure(text=f"{int(value)} questions")

    def update_question_count_limits(self):
        if not hasattr(self, "question_count_slider") or not hasattr(self, "question_count_var"):
            return

        pool_size = len(self.filtered_questions())
        max_questions = min(1000, max(10, pool_size)) if pool_size else 10
        self.question_count_slider.configure(from_=10, to=max_questions)
        current_value = int(self.question_count_var.get())
        if current_value > max_questions:
            self.question_count_var.set(max_questions)
        if pool_size > 0:
            self.pool_count_label.configure(text=f"Available in pool: {pool_size} questions")
        else:
            self.pool_count_label.configure(text="Available in pool: 0 questions")
        self.question_count_value.configure(text=f"{int(self.question_count_var.get())} questions")

    def get_selected_objectives(self):
        selected = []
        for checkbox in self.objective_checkboxes:
            if checkbox.get() == 1:
                selected.append(checkbox.cget("text"))
        return selected

    def filtered_questions(self):
        selected_exam = self.exam_var.get()
        exams = ["220-1201", "220-1202"] if selected_exam == "Combined / Practice Both" else [selected_exam]
        selected_filters = self.get_selected_objectives()

        if not selected_filters:
            return []

        filtered = []
        for question in self.bank:
            if question["exam"] not in exams:
                continue
            if self.objective_mode_var.get() == "official":
                normalized_domain = normalize_domain_name(question["domain"])
                label_matches = [entry for entry in selected_filters if f"{question['exam']} • {normalized_domain}" == entry]
                if label_matches:
                    filtered.append(question)
            else:
                label = f"{question['exam']} • {normalize_domain_name(question['domain'])} • {question['objective']}"
                if label in selected_filters:
                    filtered.append(question)
        return filtered

    def select_weighted_questions(self, candidates, requested):
        selected_filters = self.get_selected_objectives()
        if self.objective_mode_var.get() != "official" or not selected_filters:
            return list(candidates)[:requested]

        domain_buckets = {}
        for question in candidates:
            domain_label = f"{question['exam']} • {normalize_domain_name(question['domain'])}"
            if domain_label in selected_filters:
                domain_buckets.setdefault(domain_label, []).append(question)

        if not domain_buckets:
            return list(candidates)[:requested]

        weights = {}
        for label in selected_filters:
            for exam in ("220-1201", "220-1202"):
                if not label.startswith(f"{exam} • "):
                    continue
                domain = normalize_domain_name(label.split(" • ", 1)[1])
                weight = self.metadata.get(exam, {}).get("official_weights", {}).get(domain, 0)
                if weight:
                    weights[label] = weight

        if not weights:
            return list(candidates)[:requested]

        total_weight = sum(weights.values())
        allocations = {label: 0 for label in weights}
        remaining = requested
        for idx, label in enumerate(weights):
            if idx == len(weights) - 1:
                allocations[label] = remaining
            else:
                exact = (weights[label] / total_weight) * requested
                allocated = int(round(exact))
                allocations[label] = allocated
                remaining -= allocated

        chosen = []
        for label, count in allocations.items():
            pool = domain_buckets.get(label, [])
            if not pool:
                continue
            random.shuffle(pool)
            chosen.extend(pool[:max(0, min(count, len(pool)))])

        if len(chosen) < requested:
            extras = [q for q in candidates if q not in chosen]
            random.shuffle(extras)
            for question in extras:
                if len(chosen) >= requested:
                    break
                chosen.append(question)

        random.shuffle(chosen)
        return chosen[:requested]

    def start_exam(self):
        candidates = self.filtered_questions()
        if not candidates:
            messagebox.showwarning("No Questions", "No question pool matches the selected filters.")
            return

        requested = int(self.question_count_var.get())
        if requested > len(candidates):
            requested = len(candidates)
            self.question_count_var.set(requested)
            self.question_count_value.configure(text=f"{requested} questions")

        if self.objective_mode_var.get() == "official":
            chosen = self.select_weighted_questions(candidates, requested)
        else:
            chosen = list(candidates)
            random.shuffle(chosen)
            chosen = chosen[:requested]

        if len(chosen) < 10:
            messagebox.showwarning("Very Small Pool", "The current filters produced fewer than 10 questions. Consider selecting more exam objectives.")

        self.current_session = ExamSession(chosen, self.timer_var.get(), self.study_mode_var.get() == "study")
        self.show_exam_screen()
        self.render_question()

    def show_setup_screen(self):
        self.setup_frame.pack(fill="both", expand=True)
        self.exam_frame.pack_forget()
        self.results_frame.pack_forget()
        self.populate_objective_options()

    def show_exam_screen(self):
        self.setup_frame.pack_forget()
        self.exam_frame.pack(fill="both", expand=True)
        self.results_frame.pack_forget()
        self.schedule_timer()

    def show_results_screen(self):
        self.setup_frame.pack_forget()
        self.exam_frame.pack_forget()
        self.results_frame.pack(fill="both", expand=True)
        self.cancel_timer()
        self.render_results()

    def build_exam_screen(self):
        top_bar = ctk.CTkFrame(self.exam_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=18, pady=(18, 12))

        self.exam_title = ctk.CTkLabel(top_bar, text="Zohar's A+ Practice Prep  /  Practice Room", font=ctk.CTkFont(size=22, weight="bold"))
        self.exam_title.pack(side="left")

        self.timer_label = ctk.CTkLabel(top_bar, text="--:--", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FCD34D")
        self.timer_label.pack(side="right")

        content = ctk.CTkFrame(self.exam_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        palette_frame = ctk.CTkFrame(content, corner_radius=18, border_width=1, width=220)
        palette_frame.pack(side="left", fill="y", padx=(0, 14))
        palette_frame.pack_propagate(False)

        ctk.CTkLabel(palette_frame, text="Question Palette", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(14, 8))
        self.palette_container = ctk.CTkScrollableFrame(palette_frame, width=200, height=600)
        self.palette_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        main_card = ctk.CTkFrame(content, corner_radius=18, border_width=1)
        main_card.pack(side="left", fill="both", expand=True)

        self.progress_label = ctk.CTkLabel(main_card, text="Question 1 of 1", font=ctk.CTkFont(size=15, weight="bold"))
        self.progress_label.pack(anchor="w", padx=18, pady=(18, 10))

        self.domain_label = ctk.CTkLabel(main_card, text="Domain: ", font=ctk.CTkFont(size=14, weight="bold"), text_color="#93C5FD")
        self.domain_label.pack(anchor="w", padx=18, pady=(0, 12))

        self.question_label = ctk.CTkLabel(main_card, text="Question text…", justify="left", wraplength=700, font=ctk.CTkFont(size=18, weight="bold"))
        self.question_label.pack(anchor="w", padx=18, pady=(0, 20))

        self.options_frame = ctk.CTkFrame(main_card, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=18)

        self.feedback_label = ctk.CTkLabel(main_card, text="", justify="left", wraplength=760, font=ctk.CTkFont(size=14, weight="bold"))
        self.feedback_label.pack(anchor="w", padx=18, pady=(10, 0))

        bottom_bar = ctk.CTkFrame(main_card, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=18, pady=(18, 18))

        ctk.CTkButton(bottom_bar, text="Previous", command=self.previous_question, width=120).pack(side="left")
        self.flag_button = ctk.CTkButton(bottom_bar, text="Flag for Review", command=self.toggle_flag, width=160)
        self.flag_button.pack(side="left", padx=12)
        ctk.CTkButton(bottom_bar, text="Next", command=self.next_question, width=120).pack(side="right")
        ctk.CTkButton(bottom_bar, text="Submit Exam", command=self.submit_exam, width=140).pack(side="right", padx=(0, 12))

    def build_results_screen(self):
        title = ctk.CTkLabel(self.results_frame, text="Zohar's A+ Practice Prep  /  Progress Review", font=ctk.CTkFont(size=26, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(18, 8))

        summary = ctk.CTkFrame(self.results_frame, corner_radius=16, border_width=1)
        summary.pack(fill="x", padx=20, pady=(0, 14))

        self.summary_label = ctk.CTkLabel(summary, text="", font=ctk.CTkFont(size=20, weight="bold"))
        self.summary_label.pack(anchor="w", padx=18, pady=(18, 8))

        self.score_label = ctk.CTkLabel(summary, text="", font=ctk.CTkFont(size=16))
        self.score_label.pack(anchor="w", padx=18, pady=(0, 18))

        self.recommendation_label = ctk.CTkLabel(summary, text="", justify="left", wraplength=1080, font=ctk.CTkFont(size=14, weight="bold"))
        self.recommendation_label.pack(anchor="w", padx=18, pady=(0, 18))

        self.breakdown_panel = ctk.CTkScrollableFrame(self.results_frame, width=1180, height=430)
        self.breakdown_panel.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        actions = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(actions, text="Retake Exam", command=self.show_setup_screen, width=180).pack(side="right")

    def render_question(self):
        if self.current_session is None:
            return

        question = self.current_session.current_question()
        if question is None:
            return

        self.progress_label.configure(text=f"Question {self.current_session.current_index + 1} of {self.current_session.total_questions}")
        self.domain_label.configure(text=f"Domain: {question['domain']} • {question['objective']}")
        self.question_label.configure(text=question["question"], width=680)

        for child in self.options_frame.winfo_children():
            child.destroy()
        self.option_buttons = []
        selected_answer = self.current_session.answers.get(str(self.current_session.current_index), "")
        is_multi = bool(question.get("multi_select"))
        self.option_var = ctk.StringVar(value=selected_answer if not is_multi else "")

        if is_multi:
            selected_set = ExamSession.normalize_answer_set(selected_answer)
            for option in question["options"]:
                option_letter = ExamSession.answer_letter(option)
                variable = ctk.BooleanVar(value=option_letter in selected_set)
                checkbox = ctk.CTkCheckBox(
                    self.options_frame,
                    text=option,
                    variable=variable,
                    command=lambda selected_option=option: self.answer_current(self.get_selected_multi_answers()),
                    font=ctk.CTkFont(size=14),
                )
                checkbox.pack(anchor="w", pady=6, padx=4)
                self.option_buttons.append(checkbox)
        else:
            for option in question["options"]:
                radio = ctk.CTkRadioButton(
                    self.options_frame,
                    text=option,
                    variable=self.option_var,
                    value=option,
                    command=lambda selected=option: self.answer_current(selected),
                    font=ctk.CTkFont(size=14),
                )
                radio.pack(anchor="w", pady=6, padx=4)
                self.option_buttons.append(radio)

        if not is_multi and selected_answer:
            self.option_var.set(selected_answer)

        if self.current_session.study_mode and selected_answer:
            self.show_study_feedback(question, selected_answer)
        elif self.feedback_label is not None:
            self.feedback_label.configure(text="")

        self.flag_button.configure(text="Unflag" if self.current_session.is_flagged(self.current_session.current_index) else "Flag for Review")
        self.update_palette()
        self.update_timer_display()

    def get_selected_multi_answers(self):
        if self.current_session is None:
            return []
        question = self.current_session.current_question()
        if not question or not question.get("multi_select"):
            return []
        selected = []
        for button in self.option_buttons:
            if getattr(button, "get", lambda: 0)() == 1:
                selected.append(ExamSession.answer_letter(button.cget("text")))
        return selected

    def answer_current(self, value):
        if self.current_session is None:
            return
        question = self.current_session.current_question()
        if question and question.get("multi_select"):
            if value is None:
                value = self.get_selected_multi_answers()
            self.current_session.record_answer(value)
        else:
            self.current_session.record_answer(value)
        if self.current_session.study_mode:
            self.show_study_feedback(self.current_session.current_question(), self.current_session.answers.get(str(self.current_session.current_index), ""))
        self.update_palette()

    def show_study_feedback(self, question, selected):
        if question.get("multi_select"):
            correct_answers = ExamSession.normalize_answer_set(question["answer"])
            chosen_answers = ExamSession.normalize_answer_set(selected)
            is_correct = chosen_answers == correct_answers
            expected_label = ", ".join(sorted(correct_answers)) if correct_answers else "None"
            result = "Correct" if is_correct else f"Incorrect. Correct answer(s): {expected_label}"
        else:
            is_correct = ExamSession.answer_letter(selected) == ExamSession.answer_letter(question["answer"])
            result = "Correct" if is_correct else f"Incorrect. Correct answer: {question['answer']}"
        color = "#86EFAC" if is_correct else "#FCA5A5"
        self.feedback_label.configure(text=f"{result}\n{question['explanation']}", text_color=color)
        for button in self.option_buttons:
            button.configure(state="disabled")

    def toggle_flag(self):
        if self.current_session is None:
            return
        flagged = self.current_session.is_flagged(self.current_session.current_index)
        self.current_session.mark_flagged(not flagged)
        self.flag_button.configure(text="Unflag" if not flagged else "Flag for Review")
        self.update_palette()

    def next_question(self):
        if self.current_session is None:
            return
        if self.current_session.current_index < self.current_session.total_questions - 1:
            self.current_session.current_index += 1
            self.render_question()
        else:
            self.submit_exam()

    def previous_question(self):
        if self.current_session is None:
            return
        if self.current_session.current_index > 0:
            self.current_session.current_index -= 1
            self.render_question()

    def update_palette(self):
        for child in self.palette_container.winfo_children():
            child.destroy()

        if self.current_session is None:
            return

        self.palette_buttons = []
        for idx in range(self.current_session.total_questions):
            question = self.current_session.questions[idx]
            if self.current_session.is_flagged(idx):
                state = "Flagged"
                color = "#F59E0B"
            elif self.current_session.is_answered(idx):
                state = "Answered"
                color = "#10B981"
            else:
                state = "Unanswered"
                color = "#64748B"

            btn = ctk.CTkButton(
                self.palette_container,
                text=f"{idx + 1} {state}",
                width=165,
                height=26,
                fg_color=color,
                hover_color="#1E3A8A",
                command=lambda selected_index=idx: self.jump_to_question(selected_index),
            )
            btn.pack(fill="x", pady=4, padx=6)
            self.palette_buttons.append(btn)

    def jump_to_question(self, index):
        if self.current_session is None:
            return
        self.current_session.current_index = index
        self.render_question()

    def schedule_timer(self):
        self.cancel_timer()
        if self.current_session is None:
            return
        if self.current_session.timer_mode == "untimed":
            self.timer_label.configure(text="Untimed")
            return

        self.timer_after_id = self.after(1000, self.tick_timer)

    def cancel_timer(self):
        if self.timer_after_id is not None:
            try:
                self.after_cancel(self.timer_after_id)
            except Exception:
                pass
            self.timer_after_id = None

    def tick_timer(self):
        if self.current_session is None:
            return
        if self.current_session.timer_mode == "untimed":
            return

        self.current_session.remaining_seconds = max(0, self.current_session.remaining_seconds - 1)
        self.update_timer_display()

        if self.current_session.remaining_seconds <= 0:
            self.submit_exam()
            return

        self.timer_after_id = self.after(1000, self.tick_timer)

    def update_timer_display(self):
        if self.current_session is None:
            return
        if self.current_session.timer_mode == "untimed":
            self.timer_label.configure(text="Untimed")
            return

        remaining = self.current_session.remaining_seconds
        minutes, seconds = divmod(remaining, 60)
        formatted = f"{minutes:02d}:{seconds:02d}"
        self.timer_label.configure(text=formatted)
        if remaining <= 30:
            self.timer_label.configure(text_color="#F87171")
        else:
            self.timer_label.configure(text_color="#FCD34D")

    def submit_exam(self):
        if self.current_session is None:
            return

        results = self.current_session.compute_results()
        self.cancel_timer()
        self.last_results = results
        self.show_results_screen()

    def render_results(self):
        if not hasattr(self, "last_results"):
            return
        results = self.last_results
        exam_label = self.exam_var.get()
        threshold = 675 if exam_label in ("220-1201", "Combined / Practice Both") else 700
        passed = results["scaled_score"] >= threshold

        pass_text = "PASS" if passed else "FAIL"
        self.summary_label.configure(text=f"{pass_text} • {results['correct']} / {results['total']} correct")
        self.score_label.configure(text=f"Scaled score: {results['scaled_score']} | Percent correct: {results['raw_percent']:.1f}% | Exam: {exam_label} | Pass threshold: {threshold}")
        self.summary_label.configure(text_color="#86EFAC" if passed else "#FCA5A5")

        objective_results = results.get("objective_results", {})
        if objective_results:
            weakest_objective, weakest_stats = min(
                objective_results.items(),
                key=lambda item: (item[1]["correct"] / item[1]["total"], item[0]),
            )
            weakest_percent = (weakest_stats["correct"] / weakest_stats["total"]) * 100
            self.recommendation_label.configure(
                text=(
                    f"Recommended focus: {weakest_objective}\n"
                    f"You scored {weakest_stats['correct']} / {weakest_stats['total']} ({weakest_percent:.1f}%). "
                    "Review this objective and practice it again before your next exam."
                ),
                text_color="#FCD34D",
            )
        else:
            self.recommendation_label.configure(text="Recommended focus: No objective data available.", text_color="#FCD34D")

        for child in self.breakdown_panel.winfo_children():
            child.destroy()

        domain_rows = []
        for domain, stats in results["objective_scores"].items():
            total = stats["total"]
            percent = (stats["correct"] / total) * 100 if total else 0
            domain_rows.append((domain, percent, stats["correct"], total))

        if not domain_rows:
            domain_rows = [("No objective data", 0, 0, 0)]

        for domain, percent, correct, total in domain_rows:
            row = ctk.CTkFrame(self.breakdown_panel, corner_radius=12, border_width=1, fg_color="#111827")
            row.pack(fill="x", padx=10, pady=6)
            ctk.CTkLabel(row, text=f"{domain}", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=(10, 0))
            progress = ctk.CTkProgressBar(row, mode="determinate", width=420)
            progress.set(max(0.0, min(1.0, percent / 100)))
            progress.pack(anchor="w", padx=12, pady=(0, 8))
            ctk.CTkLabel(row, text=f"{correct} / {total} correct ({percent:.1f}%)", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=12, pady=(0, 10))

        review_frame = ctk.CTkFrame(self.breakdown_panel, corner_radius=12, border_width=1, fg_color="#111827")
        review_frame.pack(fill="x", padx=10, pady=14)
        ctk.CTkLabel(review_frame, text="Review Answers", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=12, pady=(10, 8))
        for index, item in enumerate(results["details"], start=1):
            q = item["question"]
            selected = item["selected"] or "No answer selected"
            correct = item["correct"]
            status = "Correct" if item["is_correct"] else "Incorrect"
            card = ctk.CTkFrame(review_frame, corner_radius=12, border_width=1, fg_color="#0F172A")
            card.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(
                card,
                text=f"Question {index}: {status}\n{q['question']}\n\nYour answer: {selected}\nCorrect answer: {correct}\n\nExplanation: {q['explanation']}",
                justify="left",
                wraplength=1000,
            ).pack(anchor="w", padx=12, pady=12)


def main():
    app = APlusPracticeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
