"""Synthetic syllabus cases with predefined reference topic titles."""


TOPIC_EXTRACTION_CASES = [
    {
        "name": "database_baseline",
        "syllabus_text": """
Database Systems Syllabus

Study topics:
1. Introduction to databases
2. Relational models
3. SQL queries
4. Database normalization
5. Transactions and concurrency
6. Indexes
""",
        "expected_titles": [
            "Introduction to databases",
            "Relational models",
            "SQL queries",
            "Database normalization",
            "Transactions and concurrency",
            "Indexes",
        ],
    },
    {
        "name": "operating_systems_with_admin_text",
        "syllabus_text": """
Operating Systems

Office hours: Wednesday, 2 PM.
Assessment: quizzes 20%, midterm 30%, final exam 50%.
Students must submit assignments through the course portal.

Course content:
- Processes and threads: process states and thread management.
- CPU scheduling: FCFS, SJF, and round-robin algorithms.
- Synchronization: critical sections, mutexes, and semaphores.
- Deadlocks: prevention, avoidance, and detection.
- Memory management: paging and virtual memory.
- File systems: directories, allocation, and access permissions.

Attendance policy: attend at least 75% of lectures.
""",
        "expected_titles": [
            "Processes and threads",
            "CPU scheduling",
            "Synchronization",
            "Deadlocks",
            "Memory management",
            "File systems",
        ],
    },
    {
        "name": "networks_with_repeated_topic",
        "syllabus_text": """
Computer Networks

Learning units:
1. Network models
2. Ethernet and switching
3. IPv4 and subnetting
4. Routing
5. TCP and UDP
6. DNS and HTTP

Revision checklist:
Review IPv4 and subnetting again.
The repeated checklist item belongs to the same learning unit.

Final assessment date: December 10.
Bring your student identification card to the exam.
""",
        "expected_titles": [
            "Network models",
            "Ethernet and switching",
            "IPv4 and subnetting",
            "Routing",
            "TCP and UDP",
            "DNS and HTTP",
        ],
    },
]