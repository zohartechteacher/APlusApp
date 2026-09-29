from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

OBJECTIVES = {
    "220-1201": {
        "Mobile Devices": [
            "1.1 Identify common mobile device components and features.",
            "1.2 Explain mobile device networking and configuration.",
            "1.3 Configure mobile device accessories and connectivity.",
            "1.4 Explain mobile device synchronization and app management.",
        ],
        "Networking": [
            "2.1 Given a scenario, install and configure wired and wireless networks.",
            "2.2 Explain common networking protocols and services.",
            "2.3 Explain common networking hardware and media.",
            "2.4 Troubleshoot common network connectivity issues.",
        ],
        "Hardware": [
            "3.1 Explain motherboard, processor, and memory installation.",
            "3.2 Given a scenario, install and configure storage devices.",
            "3.3 Given a scenario, install and configure display devices and adapters.",
            "3.4 Given a scenario, install and configure peripheral devices.",
            "3.5 Given a scenario, install the appropriate power supply.",
            "3.6 Explain cooling, ventilation, and thermal management.",
        ],
        "Virtualization and Cloud": [
            "4.1 Explain virtualization and cloud concepts.",
            "4.2 Explain cloud service models.",
            "4.3 Troubleshoot virtualization and cloud issues.",
        ],
        "Troubleshooting": [
            "5.1 Troubleshoot common hardware and network issues.",
            "5.2 Troubleshoot common mobile device and peripheral issues.",
            "5.3 Diagnose and resolve application, OS, and connectivity issues.",
        ],
    },
    "220-1202": {
        "Operating Systems": [
            "1.1 Install and configure operating systems.",
            "1.2 Configure desktop and system settings.",
            "1.3 Manage users, groups, and permissions.",
            "1.4 Troubleshoot operating system start-up and boot issues.",
        ],
        "Security": [
            "2.1 Implement common security controls.",
            "2.2 Manage account security and access control.",
            "2.3 Explain malware, phishing, and social engineering defenses.",
            "2.4 Configure encryption and endpoint protection.",
        ],
        "Software Troubleshooting": [
            "3.1 Diagnose software installation and application issues.",
            "3.2 Diagnose operating system and network service issues.",
            "3.3 Troubleshoot application performance and compatibility problems.",
        ],
        "Operational Procedures": [
            "4.1 Follow operational procedures and documentation.",
            "4.2 Manage change control, incident response, and asset documentation.",
            "4.3 Implement basic backup, safety, and environmental procedures.",
        ],
    },
}

QUESTION_STEMS = {
    "Mobile Devices": [
        "repair a damaged smartphone display",
        "configure a tablet for company Wi-Fi",
        "pair wireless earbuds to a mobile device",
        "troubleshoot a phone battery that drains quickly",
        "sync a device with a corporate cloud account",
        "deploy an MDM policy to a fleet of phones",
        "resolve a touchscreen failure on a mobile device",
        "diagnose poor cellular signal behavior",
        "manage app permissions for a BYOD device",
    ],
    "Networking": [
        "connect a workstation to a small office network",
        "configure a home router for secure Wi-Fi use",
        "troubleshoot a faulty Ethernet cable",
        "verify DHCP address assignment on a LAN",
        "connect a switch to a patch panel",
        "diagnose slow file transfers across the network",
        "set up a wireless access point",
        "review DNS and port configuration",
        "confirm a VPN client is connecting properly",
    ],
    "Hardware": [
        "upgrade a workstation memory configuration",
        "install a new SSD on a desktop PC",
        "replace a failing GPU in a gaming system",
        "repair a printer connection issue",
        "install a new power supply in a PC",
        "configure cooling for a high-heat CPU",
        "install a USB peripheral on a desktop",
        "troubleshoot a monitor that is not displaying",
        "replace a failing hard drive in a server",
    ],
    "Virtualization and Cloud": [
        "deploy a virtual machine in a private lab",
        "evaluate SaaS versus IaaS for a business",
        "configure shared responsibility in a cloud setup",
        "migrate an application to a cloud platform",
        "troubleshoot VM networking performance",
        "plan a PaaS solution for a development team",
        "review cloud backup retention requirements",
        "improve fault tolerance in a virtual environment",
    ],
    "Troubleshooting": [
        "resolve a no-POST boot issue on a workstation",
        "diagnose an intermittent printer failure",
        "repair a broken Wi-Fi connection in a laptop",
        "isolate a failing USB device",
        "resolve a slow application startup",
        "debug a device-driver conflict on Windows",
        "test connectivity between client and server",
        "diagnose a battery-charge reporting error",
        "repair a damaged keyboard and mouse setup",
    ],
    "Operating Systems": [
        "install Windows on a new workstation",
        "configure a user profile in Windows",
        "manage local accounts and permissions",
        "troubleshoot a system that will not boot",
        "repair a login problem after an update",
        "configure startup services in msconfig",
        "diagnose a broken device driver installation",
        "restore a corrupted system restore point",
        "secure a workstation login against unauthorized access",
    ],
    "Security": [
        "secure a Windows laptop against malware",
        "configure file encryption on a corporate device",
        "respond to a simulated phishing email",
        "review account privilege assignments",
        "implement multifactor authentication",
        "deploy endpoint protection on a user device",
        "respond to suspicious browser redirects",
        "lock down a user account with proper access controls",
        "troubleshoot an infected workstation",
    ],
    "Software Troubleshooting": [
        "install a legacy application on a modern OS",
        "repair an application update that fails",
        "diagnose a software compatibility problem",
        "review application logs for errors",
        "recover a missing runtime dependency",
        "repair a crashing desktop application",
        "diagnose a service that fails to start",
        "resolve poor Windows performance after an update",
        "troubleshoot a network service outage",
    ],
    "Operational Procedures": [
        "document a workstation change request",
        "review a ticket for incident response",
        "prepare a backup and restoration plan",
        "secure a staging area for equipment",
        "audit endpoint inventory for a rollout",
        "check compliance documentation for a workstation",
        "document a user support escalation",
        "handle a hardware disposal process",
        "document a maintenance checklist for a system",
    ],
}

QUESTIONS_PER_OBJECTIVE = 30
LETTERS = ["A", "B", "C", "D"]


def build_options(correct_text: str, distractors: list[str], answer_index: int) -> tuple[list[str], str]:
    choices = [correct_text] + distractors[:3]
    ordered = [choices[(idx - answer_index) % 4] for idx in range(4)]
    options = [f"{letter}) {text}" for letter, text in zip(LETTERS, ordered)]
    return options, LETTERS[answer_index]


def make_question(exam: str, domain: str, objective: str, q_num: int) -> dict:
    stem = QUESTION_STEMS[domain][q_num % len(QUESTION_STEMS[domain])]
    answer_index = q_num % 4
    if q_num % 2 == 0:
        question = f"Which objective is most directly related to this task: {stem}?"
        correct_text = objective
        all_objectives = [item for items in OBJECTIVES[exam].values() for item in items]
        distractors = [item for item in all_objectives if item != objective]
        explanation = f"This task is most closely associated with {objective}."
    else:
        question = f"A technician is troubleshooting {stem}. What should be done first?"
        correct_text = "Confirm the symptoms, scope, and recent changes before selecting a targeted fix."
        distractors = [
            "Replace components immediately without confirming the failure.",
            "Change several unrelated settings at once and compare the results later.",
            "Disable security controls before collecting any diagnostic evidence.",
        ]
        explanation = "Troubleshooting should begin by confirming the symptoms, scope, and recent changes so the next test is targeted and measurable."

    options, answer = build_options(correct_text, distractors, answer_index)
    target_id = f"{exam.replace('-', '')}-{domain[:3].upper()}-{objective.split('.')[0].replace('.', '')}-{q_num + 1:03d}"
    return {
        "id": target_id,
        "exam": exam,
        "domain": domain,
        "objective": objective,
        "question": question,
        "options": options,
        "answer": answer,
        "explanation": explanation,
    }


def main() -> None:
    questions = []
    seen = set()
    for exam, domains in OBJECTIVES.items():
        for domain, objectives in domains.items():
            for objective in objectives:
                for q_num in range(QUESTIONS_PER_OBJECTIVE):
                    item = make_question(exam, domain, objective, q_num)
                    while item["id"] in seen:
                        item["id"] = f"{item['id'][:-3]}{int(item['id'][-3:]) + 1:03d}"
                    seen.add(item["id"])
                    questions.append(item)

    assert len(questions) >= 1000, f"Expected at least 1000 questions, got {len(questions)}"
    DATA_DIR.mkdir(exist_ok=True)
    output_path = DATA_DIR / "questions.json"
    output_path.write_text(json.dumps(questions, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(questions)} questions in {output_path}")


if __name__ == "__main__":
    main()
