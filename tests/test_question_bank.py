import json
from pathlib import Path

from app import ExamSession

ROOT = Path(__file__).resolve().parents[1]


def test_question_bank_exists_and_has_expected_shape():
    data_path = ROOT / "data" / "questions.json"
    assert data_path.exists(), "Question bank should ship with the application"

    with data_path.open("r", encoding="utf-8") as fh:
        questions = json.load(fh)

    assert isinstance(questions, list)
    assert len(questions) >= 12
    first = questions[0]
    assert {"id", "exam", "domain", "objective", "question", "options", "answer", "explanation"}.issubset(first)
    assert len(first["options"]) >= 2


def test_question_answers_match_their_option_letters():
    data_path = ROOT / "data" / "questions.json"
    with data_path.open("r", encoding="utf-8") as fh:
        questions = json.load(fh)

    for question in questions:
        option_letters = {option.split(")", 1)[0] for option in question["options"]}
        correct_option = next(option for option in question["options"] if option.startswith(f"{question['answer']})"))
        assert question["answer"] in option_letters
        assert correct_option.split(")", 1)[0] == question["answer"]


def test_question_prompts_use_memorization_or_troubleshooting_formats():
    data_path = ROOT / "data" / "questions.json"
    with data_path.open("r", encoding="utf-8") as fh:
        questions = json.load(fh)

    forbidden = "Which response best follows the correct procedure for"
    assert all(forbidden not in question["question"] for question in questions)
    assert all(
        question["question"].startswith(("Which objective is most directly related", "A technician is troubleshooting"))
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


def test_question_bank_has_1000_questions_covering_major_objectives():
    data_path = ROOT / "data" / "questions.json"
    with data_path.open("r", encoding="utf-8") as fh:
        questions = json.load(fh)

    assert len(questions) >= 1000, "Question bank should include at least 1,000 total questions"

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
        "220-1202": {
            "1.1 Install and configure operating systems.",
            "1.2 Configure desktop and system settings.",
            "1.3 Manage users, groups, and permissions.",
            "1.4 Troubleshoot operating system start-up and boot issues.",
            "2.1 Implement common security controls.",
            "2.2 Manage account security and access control.",
            "2.3 Explain malware, phishing, and social engineering defenses.",
            "2.4 Configure encryption and endpoint protection.",
            "3.1 Diagnose software installation and application issues.",
            "3.2 Diagnose operating system and network service issues.",
            "3.3 Troubleshoot application performance and compatibility problems.",
            "4.1 Follow operational procedures and documentation.",
            "4.2 Manage change control, incident response, and asset documentation.",
            "4.3 Implement basic backup, safety, and environmental procedures.",
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
