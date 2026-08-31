import re

SKILL_GROUPS = {
    "Programming & CS": [
        "Python",
        "C++",
        "C",
        "Java",
        "JavaScript",
        "SQL",
        "Go",
        "Node.js",
        "Node",
        "React",
        "Vue",
        "OOP",
        "Data Structures",
        "Algorithms",
        "Debugging",
        "Software Testing",
    ],
    "Machine Learning & AI": [
        "Maching Learning",
        "Deep Learning",
        "Neural Networks",
        "PyTorch",
        "TensorFlow",
        "Keras",
        "scikit-learn",
        "Model Evaluation",
        "Feature Engineering",
        "MLflow",
        "MLOps",
        "RAG",
        "Embeddings",
        "Vector Database",
        "LangChain",
        "LlamaIndex",
    ],
    "Data & Databases": [
        "Pandas",
        "NumPy",
        "SciPy",
        "Spark",
        "PySpark",
        "PostgreSQL",
        "SQLite",
        "Relational Databases",
        "Data Preprocessing",
    ],
    "Data Science & Analytics": [
        "R",
        "Excel",
        "Tableau",
        "Power BI",
        "Statistics",
        "Probability",
        "Regression",
        "Statistical Modeling",
        "A/B Testing",
        "Experimentation",
        "Data Cleaning",
        "EDA",
        "Exploratory Data Analysis",
        "Data Analysis",
        "Data Visualization",
        "Dashboarding",
        "Business Intelligence",
        "Forecasting",
        "Linear Algebra",
        "Numerical Methods",
    ],
    "Cloud & Infrastructure": [
        "Docker",
        "Kubernetes",
        "Microservices",
        "FastAPI",
        "REST API",
        "AWS",
        "GCP",
        "Azure",
        "Linux",
        "Unix",
        "Shell Scripting",
        "Git",
        "GitHub Actions",
        "CI/CD",
        "Jenkins",
        "Perforce",
        "Ansible",
        "Automation",
        "Automation/Scripting",
        "Distributed Systems",
        "Virutalization",
        "Hardware Virtualization",
        "Containers",
    ],
    "Systems, GPU & Performance": [
        "CUDA",
        "GPU",
        "GPU Computing",
        "Accelerated Computing",
        "Parallel Programming",
        "HPC",
        "OpenMP",
        "MPI",
        "SLURM",
        "LSF",
        "Schedulers",
        "Performance Modeling",
        "Profiling",
        "Optimization",
        "Performance Tuning",
        "Operating Systems",
        "Scheduling",
        "Memory Management",
        "Process Control",
        "cuBLAS",
        "cuDNN",
        "NCCL",
        "TensorRT",
        "Real-Time Inference",
    ],
}

def contains_skill(text: str, skill: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9]){re.escape(skill.lower())}(?![A-Za-z0-9])"
    return re.search(pattern, text.lower()) is not None

def extract_potential_untracked_skills(text: str, known_skills: set[str]) -> list[str]:
    """
    Extract possible skills/tools that are not already in the tracked skill list.
    """
    patterns = [
        r"(?:skills include|technologies include|tools include|required skills:?|programming skills and technologies:)\s+([^.\n]+)",
        r"(?:experience with|knowledge of)\s+([^.\n]+)",
    ]

    candidates = []

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)

        for match in matches:
            cleaned_match = re.sub(r"\([^)]*\)", "", match)

            pieces = re.split(r",|/|;|\band\b|\bor\b", cleaned_match)

            for piece in pieces:
                cleaned = piece.strip(" .:()[]{}")
                cleaned = re.sub(r"\s+", " ", cleaned)

                if 2 <= len(cleaned) <= 35:
                    candidates.append(cleaned)

    known_lower = {skill.lower() for skill in known_skills}

    ignore_words = {
        "experience",
        "knowledge",
        "internship",
        "coursework",
        "required",
        "preferred",
        "related field",
        "full duration",
        "the following",
        "in our hiring",
        "religion",
        "color",
        "national origin",
        "gender",
        "gender expression",
        "sexual orientation",
        "age",
        "martial status",
        "veteran status",
        "disability status",
    }

    filtered = []
    seen = set()

    for candidate in candidates:
        candidate_lower = candidate.lower()

        if candidate_lower in known_lower:
            continue
        if candidate_lower in ignore_words:
            continue
        if "including" in candidate_lower:
            continue
        if "protected by law" in candidate_lower:
            continue
        if "basis of" in candidate_lower:
            continue
        if candidate_lower not in seen:
            seen.add(candidate_lower)
            filtered.append(candidate)

    return filtered[:15]

def analyze_job_description(text: str):
    matched_skills_by_group = {}

    for group, skills in SKILL_GROUPS.items():
        matched = [skill for skill in skills if contains_skill(text, skill)]

        if matched:
            matched_skills_by_group[group] = matched

    matched_skills = sorted(
        {
            skill
            for skills in matched_skills_by_group.values()
            for skill in skills
        }
    )

    known_skills = {
        skill
        for skills in matched_skills_by_group.values()
        for skill in skills
    }

    potential_untracked_skills = extract_potential_untracked_skills(
        text,
        known_skills,

    )

    top_groups = sorted(
        [   
            {"group": group, "match_count": len(skills)}
            for group, skills in matched_skills_by_group.items()
        ],
        key=lambda item: item["match_count"],
        reverse=True,
    )

    suggested_focus = []

    if matched_skills_by_group.get("Programming & CS"):
        suggested_focus.append(
            "Highlight programming experience, data structures and algorithms, debugging, and software development projects."
        )
    if matched_skills_by_group.get("Machine Learning & AI"):
        suggested_focus.append(
            "Highlight machine learning projects, model evaluation, neural networks, and applied AI experience"
        )

    if matched_skills_by_group.get("Data & Databases"):
        suggested_focus.append(
            "Highlight SQL, database experience, data preprocessing, Spark/PySpark, and working with structured datasets."
        )

    if matched_skills_by_group.get("Data Science & Analytics"):
        suggested_focus.append(
            "Highlight statistics, data cleaning, visualization, dashboards, experimentation, and business-focused analysis."
        )

    if matched_skills_by_group.get("Cloud & Infrastructure"):
        suggested_focus.append(
            "Highlight backend tools, APIs, Docker, Linux, Git, and deployment or infrastructure experience."
        )

    if matched_skills_by_group.get("Systems, GPU & Performance"):
        suggested_focus.append(
            "Highlight C/C++, operating systems, GPU/deep learning, performance analysis, and optimization experience where relevant."
        )

    if not suggested_focus:
        suggested_focus.append(
            "Focus on the role's core responsibilities, required tools, and any projects that show similar work."
        )

    return {
        "character_count": len(text),
        "matched_skills": matched_skills,
        "matched_skills_by_group": matched_skills_by_group,
        "top_groups": top_groups,
        "suggested_focus": suggested_focus,
        "potential_untracked_skills": potential_untracked_skills
    }
 