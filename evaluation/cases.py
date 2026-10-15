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
    {
        "name": "software_engineering_weekly_table",
        "syllabus_text": """
Faculty of Computing
Software Engineering
Course outline for a fourteen-week teaching period

Course information
Credit hours: 3.
Prerequisite: successful completion of introductory programming.
Contact the instructor through the university learning portal.
Office hours are announced during the first teaching week.

Course purpose
Students examine how software is specified, designed, implemented,
tested, delivered, and maintained. Practical exercises use a small
team project to connect the weekly material.

Weekly teaching schedule

| Weeks | Main study unit | Supporting content |
| 1-2 | Software processes | Lifecycle models, iterative development, agile practices |
| 3-4 | Requirements engineering | Elicitation, specification, requirements validation |
| 5-6 | Software modeling | Use cases, class diagrams, sequence diagrams |
| 7-8 | Software architecture | Architectural patterns, responsibilities, interfaces |
| 9-10 | Software testing | Unit testing, integration testing, system testing |
| 11-12 | Software maintenance | Corrective changes, refactoring, change impact |
| 13-14 | Configuration management | Version control, baselines, release management |

The main study units are the table's unit headings. Supporting content
describes each unit rather than introducing additional units.

Assessment and administration
Assignments contribute 20 percent, the midterm contributes 30 percent,
and the final examination contributes 50 percent.
Submit project work through the learning portal before the deadline.
Late submissions follow the faculty policy.
Team members must document their individual contributions.
Academic integrity rules apply to code, diagrams, and written reports.
The final examination room will be published separately.
""",
        "expected_titles": [
            "Software processes",
            "Requirements engineering",
            "Software modeling",
            "Software architecture",
            "Software testing",
            "Software maintenance",
            "Configuration management",
        ],
    },
    {
        "name": "data_structures_numbered_subtopics",
        "syllabus_text": """
Data Structures and Algorithms
Detailed course content

General information
This course requires familiarity with functions, classes, and recursion.
Students should complete the assigned reading before laboratory sessions.
Laboratory attendance and submission requirements are published on
the learning portal.

The following numbered headings identify the main study units.
Decimal-numbered items provide supporting details within those units.

1. Algorithm analysis
   1.1 Input size and counting basic operations.
   1.2 Time and space complexity.
   1.3 Big-O notation and comparing growth rates.

2. Linear data structures
   2.1 Arrays and dynamic arrays.
   2.2 Singly and doubly linked lists.
   2.3 Stacks, queues, and their applications.

3. Trees
   3.1 Tree terminology and traversal.
   3.2 Binary search trees.
   3.3 Balanced-tree concepts.

4. Hashing
   4.1 Hash functions and table organization.
   4.2 Collisions and chaining.
   4.3 Open addressing and load factor.

5. Graphs
   5.1 Adjacency lists and adjacency matrices.
   5.2 Breadth-first and depth-first traversal.
   5.3 Shortest-path concepts.

6. Sorting and searching
   6.1 Insertion sort and merge sort.
   6.2 Quicksort and comparison of sorting approaches.
   6.3 Linear search and binary search.

Laboratory work
Exercises implement the structures covered in the units above.
Students compare outputs, explain complexity, and discuss suitable
structures for small application scenarios.

Administrative notes
Bring your own laptop when available.
Consult the instructor before changing laboratory sections.
Marks are awarded according to the published assessment rubric.
Missed assessments require documentation under university policy.
These administrative notes are not additional study units.
""",
        "expected_titles": [
            "Algorithm analysis",
            "Linear data structures",
            "Trees",
            "Hashing",
            "Graphs",
            "Sorting and searching",
        ],
    },
    {
        "name": "web_development_repeated_content",
        "syllabus_text": """
Web Application Development
Teaching and laboratory outline

Course description
Students build a small web application using browser technologies,
server-side request handling, persistent storage, and access control.
The course emphasizes explaining the behaviour of the complete
request-response flow.

Main study units, in teaching order:

- Semantic HTML: document structure, accessible forms, and meaningful elements.
- Responsive CSS: layouts, media queries, and adaptable page structure.
- JavaScript fundamentals: values, functions, events, and DOM updates.
- HTTP and REST: methods, status codes, resources, and JSON exchanges.
- Server-side development: routes, request validation, and error handling.
- Database integration: persistent records, relationships, and queries.
- Authentication and authorization: sessions, login, and permission checks.
- Web application security: input handling, CSRF, and protection of secrets.

Laboratory alignment
Laboratories revisit the same main units rather than adding new ones.
The Semantic HTML laboratory builds the project's labeled forms.
The Responsive CSS laboratory adapts those pages to narrow screens.
JavaScript fundamentals are practiced through browser events.
HTTP and REST are practiced through JSON requests and status codes.
Server-side development and Database integration are then combined.
Authentication and authorization protect the resulting application.
Web application security is reviewed across the completed workflow.

Revision checklist
Revisit HTTP and REST before the integration exercise.
Review Authentication and authorization before the final demonstration.
Repeated unit names refer to the existing units and should not be
listed twice.

Administration
Weekly submissions close at the time shown on the learning portal.
Students must not include passwords or API keys in submitted repositories.
A demonstration timetable will be published near the end of teaching.
The instructor will announce assessment rooms and office-hour changes.
Contact details, submission rules, and assessment arrangements are
administrative information rather than study units.
""",
        "expected_titles": [
            "Semantic HTML",
            "Responsive CSS",
            "JavaScript fundamentals",
            "HTTP and REST",
            "Server-side development",
            "Database integration",
            "Authentication and authorization",
            "Web application security",
        ],
    },
]