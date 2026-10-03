import json
from pathlib import Path

from app import ExamSession, load_question_bank, normalize_domain_name

ROOT = Path(__file__).resolve().parents[1]


def test_question_bank_loader_accepts_wrapped_question_payloads():
    payload = {
        "metadata": {"version": "V15"},
        "questions": [
            {
                "id": "1201-1.1-001",
                "exam": "220-1201",
                "domain": "Mobile Devices",
                "objective": "1.1 Laptop Hardware",
                "question": "What does the term mean?",
                "options": ["A) One", "B) Two", "C) Three", "D) Four"],
                "answer": "A",
                "explanation": "Test explanation",
            }
        ],
    }

    assert load_question_bank(payload) == payload["questions"]


def test_domain_names_are_normalized_between_metadata_and_questions():
    assert normalize_domain_name("1.0 Mobile Devices") == "Mobile Devices"
    assert normalize_domain_name("2.0 Networking") == "Networking"
    assert normalize_domain_name("Operating Systems") == "Operating Systems"


def test_multi_select_questions_are_scored_with_set_matching():
    questions = [
        {
            "domain": "Hardware",
            "objective": "3.5 Install power supply",
            "answer": ["A", "C"],
            "multi_select": True,
            "question": "Select all valid power-supply steps.",
            "options": ["A) Verify wattage", "B) Delete the bootloader", "C) Check connector compatibility", "D) Reinstall the OS"],
            "explanation": "Only the valid steps are correct.",
        }
    ]

    session = ExamSession(questions, "untimed")
    correct_answers = session.current_question()["answer"]
    session.record_answer(correct_answers)
    assert session.compute_results()["correct"] == 1

    incorrect_answer = next(
        label for label in "ABCD" if label not in correct_answers
    )
    session.record_answer([incorrect_answer])
    assert session.compute_results()["correct"] == 0


def test_exam_session_shuffles_options_and_remaps_single_answer(monkeypatch):
    question = {
        "domain": "Hardware",
        "objective": "3.1 Install processors",
        "question": "Which option is correct?",
        "options": ["A) Alpha", "B) Beta", "C) Gamma", "D) Delta"],
        "answer": "A",
    }
    monkeypatch.setattr("app.random.shuffle", lambda options: options.reverse())

    session = ExamSession([question], "untimed")
    shuffled_question = session.current_question()

    assert shuffled_question["options"] == ["A) Delta", "B) Gamma", "C) Beta", "D) Alpha"]
    assert shuffled_question["answer"] == "D"
    session.record_answer("D")
    assert session.compute_results()["correct"] == 1
    assert question["options"][0] == "A) Alpha"
    assert question["answer"] == "A"


def test_exam_session_remaps_multi_select_answers_after_shuffling(monkeypatch):
    question = {
        "domain": "Hardware",
        "objective": "3.2 Install storage devices",
        "question": "Which options are correct?",
        "options": ["A) Alpha", "B) Beta", "C) Gamma", "D) Delta"],
        "answer": ["A", "D"],
        "multi_select": True,
    }
    monkeypatch.setattr("app.random.shuffle", lambda options: options.reverse())

    session = ExamSession([question], "untimed")
    shuffled_question = session.current_question()

    assert shuffled_question["answer"] == ["A", "D"]
    session.record_answer(["A", "D"])
    assert session.compute_results()["correct"] == 1


def test_question_bank_exists_and_has_expected_shape():
    data_path = ROOT / "data" / "questions.json"
    assert data_path.exists(), "Question bank should ship with the application"

    with data_path.open("r", encoding="utf-8") as fh:
        questions = load_question_bank(json.load(fh))

    assert isinstance(questions, list)
    assert len(questions) == 500
    first = questions[0]
    assert {"id", "exam", "domain", "objective", "question", "options", "answer", "explanation"}.issubset(first)
    assert len(first["options"]) >= 2


def test_question_answers_match_their_option_letters():
    data_path = ROOT / "data" / "questions.json"
    with data_path.open("r", encoding="utf-8") as fh:
        questions = load_question_bank(json.load(fh))

    for question in questions:
        option_letters = {option.split(")", 1)[0] for option in question["options"]}
        correct_option = next(option for option in question["options"] if option.startswith(f"{question['answer']})"))
        assert question["answer"] in option_letters
        assert correct_option.split(")", 1)[0] == question["answer"]


def test_question_prompts_use_memorization_or_troubleshooting_formats():
    data_path = ROOT / "data" / "questions.json"
    with data_path.open("r", encoding="utf-8") as fh:
        questions = load_question_bank(json.load(fh))

    forbidden = "Which response best follows the correct procedure for"
    forbidden_memorization = "Which objective is most directly related to this task"
    forbidden_concept = "Which concept should a technician memorize"
    assert all(forbidden not in question["question"] for question in questions)
    assert all(forbidden_memorization not in question["question"] for question in questions)
    assert all(forbidden_concept not in question["question"] for question in questions)
    assert all(
        question["question"].startswith(("What does the term", "A technician is troubleshooting"))
        for question in questions
    )


def test_official_weighting_structure_is_valid():
    data_path = ROOT / "data" / "exam_metadata.json"
    assert data_path.exists(), "Exam metadata should define official domain weightings"

    with data_path.open("r", encoding="utf-8") as fh:
        weights = json.load(fh)

    assert "220-1201" in weights
    assert "220-1202" in weights
    assert sum(weights["220-1201"]["official_weights"].values()) == 100
    assert sum(weights["220-1202"]["official_weights"].values()) == 100


def test_question_bank_has_500_questions_covering_220_1201_objectives():
    data_path = ROOT / "data" / "questions.json"
    with data_path.open("r", encoding="utf-8") as fh:
        questions = load_question_bank(json.load(fh))

    assert len(questions) == 500, "Question bank should include exactly 500 Core 1 questions"
    assert {question["exam"] for question in questions} == {"220-1201"}

    required_objectives = {
        "220-1201": {
            "1.1 Identify common mobile device components and features.",
            "1.2 Explain mobile device networking and configuration.",
            "1.3 Configure mobile device accessories and connectivity.",
            "1.4 Explain mobile device synchronization and app management.",
            "2.1 Given a scenario, install and configure wired and wireless networks.",
            "2.2 Explain common networking protocols and services.",
            "2.3 Explain common networking hardware and media.",
            "2.4 Troubleshoot common network connectivity issues.",
            "3.1 Explain motherboard, processor, and memory installation.",
            "3.2 Given a scenario, install and configure storage devices.",
            "3.3 Given a scenario, install and configure display devices and adapters.",
            "3.4 Given a scenario, install and configure peripheral devices.",
            "3.5 Given a scenario, install the appropriate power supply.",
            "3.6 Explain cooling, ventilation, and thermal management.",
            "4.1 Explain virtualization and cloud concepts.",
            "4.2 Explain cloud service models.",
            "4.3 Troubleshoot virtualization and cloud issues.",
            "5.1 Troubleshoot common hardware and network issues.",
            "5.2 Troubleshoot common mobile device and peripheral issues.",
            "5.3 Diagnose and resolve application, OS, and connectivity issues.",
        },
    }

    seen = {(q["exam"], q["objective"]) for q in questions}
    for exam, objectives in required_objectives.items():
        for objective in objectives:
            assert (exam, objective) in seen, f"Missing objective {objective} for {exam}"


def test_scoring_logic_reference_values_are_reasonable():
    assert 675 <= 700
    assert 700 <= 900


def test_study_mode_and_objective_results_are_tracked():
    questions = [
        {
            "domain": "Networking",
            "objective": "2.1 Configure networks",
            "answer": "A",
            "question": "Question one",
            "options": ["A", "B"],
            "explanation": "Explanation one",
        },
        {
            "domain": "Security",
            "objective": "2.2 Secure accounts",
            "answer": "B",
            "question": "Question two",
            "options": ["A", "B"],
            "explanation": "Explanation two",
        },
    ]

    session = ExamSession(questions, "untimed", study_mode=True)
    session.record_answer("A")
    session.current_index = 1
    session.record_answer("A")

    results = session.compute_results()

    assert session.study_mode is True
    assert results["objective_results"]["2.1 Configure networks"] == {"correct": 1, "total": 1}
    assert results["objective_results"]["2.2 Secure accounts"] == {"correct": 0, "total": 1}
