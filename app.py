import json
import random
import re
import sys
import time
from pathlib import Path

import customtkinter as ctk


try:
    from tkinter import messagebox
except ImportError:  # pragma: no cover
    messagebox = None


APP_TITLE = "Zohar's A+ Practice Prep"


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
        self.questions = questions
        self.timer_mode = timer_mode
        self.study_mode = study_mode
        self.current_index = 0
        self.answers = {}
        self.flagged = set()
        self.started_at = time.time()
        self.time_limit = self._resolve_time_limit(timer_mode)
        self.remaining_seconds = self.time_limit

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
    def answer_letter(answer: str) -> str:
        if not answer:
            return ""
        return answer.split(")", 1)[0].strip().upper()

    def record_answer(self, answer: str):
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
        super().__init__()
        icon_path = get_app_icon_path()
        if icon_path is not None:
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title(APP_TITLE)
        self.geometry("1280x860")
        self.minsize(1100, 700)
        self.configure(fg_color="#0F172A")

        self.base_dir = get_base_dir()
        self.data_dir = self.base_dir / "data"
        self.bank = load_question_bank(load_json(self.data_dir / "questions.json"))
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
        ctk.CTkLabel(
            brand_copy,
            text="ZOHAR'S  /  CERTIFICATION STUDIO",
            text_color="#67E8F9",
            font=ctk.CTkFont(family="Aptos Display", size=11, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))
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
        ctk.CTkLabel(brand_stats, text="1,020", text_color="#FCD34D", font=ctk.CTkFont(family="Aptos Display", size=24, weight="bold")).pack(padx=20, pady=(12, 0))
        ctk.CTkLabel(brand_stats, text="practice questions", text_color="#AFC1D8", font=ctk.CTkFont(size=11)).pack(padx=20, pady=(0, 12))

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
        self.option_var = ctk.StringVar(value=selected_answer)

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

        if selected_answer:
            self.option_var.set(selected_answer)

        if self.current_session.study_mode and selected_answer:
            self.show_study_feedback(question, selected_answer)
        elif self.feedback_label is not None:
            self.feedback_label.configure(text="")

        self.flag_button.configure(text="Unflag" if self.current_session.is_flagged(self.current_session.current_index) else "Flag for Review")
        self.update_palette()
        self.update_timer_display()

    def answer_current(self, value):
        self.current_session.record_answer(value)
        if self.current_session.study_mode:
            self.show_study_feedback(self.current_session.current_question(), value)
        self.update_palette()

    def show_study_feedback(self, question, selected):
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
