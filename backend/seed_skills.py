"""
Seed script for the Skill catalog.
Safe to rerun (editing an existing skill's group here and rerunning will sync the database to match)
"""

from sqlalchemy import func, select
from backend.database import SessionLocal
from backend.models import Skill

SKILL_CATALOG = [
    # Programming & CS   (SKILL_GROUPS["Programming & CS"])
    {"canonical_name": "Python", "aliases": ["Python"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "C++", "aliases": ["C++", "CPP", "Cpp"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "C", "aliases": ["C"], "group": "Programming & CS", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "Java", "aliases": ["Java"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "JavaScript", "aliases": ["JavaScript", "JS", "ECMAScript"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "SQL", "aliases": ["SQL"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Go", "aliases": ["Go", "Golang"], "group": "Programming & CS", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "Node.js", "aliases": ["Node.js", "NodeJS", "Node"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "React", "aliases": ["React", "React.js", "ReactJS"], "group": "Programming & CS", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "Vue", "aliases": ["Vue", "Vue.js", "VueJS"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Object-Oriented Programming", "aliases": ["Object-Oriented Programming", "Object Oriented Programming", "OOP"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Data Structures", "aliases": ["Data Structures"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Algorithms", "aliases": ["Algorithms"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Debugging", "aliases": ["Debugging"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Software Testing", "aliases": ["Software Testing"], "group": "Programming & CS", "is_ambiguous": False, "requires_case_sensitive": False},

    # Data & ML 
    {"canonical_name": "Machine Learning", "aliases": ["Machine Learning", "ML"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Deep Learning", "aliases": ["Deep Learning", "DL"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Neural Networks", "aliases": ["Neural Networks", "Neural Network", "NN"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "PyTorch", "aliases": ["PyTorch"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "TensorFlow", "aliases": ["TensorFlow"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Keras", "aliases": ["Keras"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "scikit-learn", "aliases": ["scikit-learn", "scikit learn", "sklearn"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Model Evaluation", "aliases": ["Model Evaluation"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Feature Engineering", "aliases": ["Feature Engineering"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "MLflow", "aliases": ["MLflow"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "MLOps", "aliases": ["MLOps"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "RAG", "aliases": ["RAG", "Retrieval-Augmented Generation", "Retrieval Augmented Generation"], "group": "Data & ML", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "Embeddings", "aliases": ["Embeddings", "Embedding"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Vector Database", "aliases": ["Vector Database", "Vector DB", "VectorDB"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "LangChain", "aliases": ["LangChain"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "LlamaIndex", "aliases": ["LlamaIndex", "Llama Index"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False}, 
    {"canonical_name": "Pandas", "aliases": ["Pandas"], "group": "Data & ML", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "NumPy", "aliases": ["NumPy"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "SciPy", "aliases": ["SciPy"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Spark", "aliases": ["Spark", "Apache Spark"], "group": "Data & ML", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "PySpark", "aliases": ["PySpark"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "PostgreSQL", "aliases": ["PostgreSQL", "Postgres"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "SQLite", "aliases": ["SQLite"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Relational Databases", "aliases": ["Relational Databases", "Relational Database", "RDBMS"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Data Preprocessing", "aliases": ["Data Preprocessing", "Data Pre-processing"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "R", "aliases": ["R"], "group": "Data & ML", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "Excel", "aliases": ["Excel", "Microsoft Excel", "MS Excel"], "group": "Data & ML", "is_ambiguous": True, "requires_case_sensitive": True},
    {"canonical_name": "Tableau", "aliases": ["Tableau"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Power BI", "aliases": ["Power BI", "PowerBI"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Statistics", "aliases": ["Statistics", "Stats"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Probability", "aliases": ["Probability"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Regression", "aliases": ["Regression"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Statistical Modeling", "aliases": ["Statistical Modeling", "Statistical Modelling"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "A/B Testing", "aliases": ["A/B Testing", "AB Testing", "A/B Test"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Experimentation", "aliases": ["Experimentation"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Data Cleaning", "aliases": ["Data Cleaning"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Exploratory Data Analysis", "aliases": ["Exploratory Data Analysis", "EDA"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Data Analysis", "aliases": ["Data Analysis", "Data Analytics"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Data Visualization", "aliases": ["Data Visualization", "Data Visualisation", "Data Viz"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Dashboarding", "aliases": ["Dashboarding", "Dashboards", "Dashboard"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Business Intelligence", "aliases": ["Business Intelligence"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Forecasting", "aliases": ["Forecasting"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Linear Algebra", "aliases": ["Linear Algebra"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Numerical Methods", "aliases": ["Numerical Methods"], "group": "Data & ML", "is_ambiguous": False, "requires_case_sensitive": False},

    # Infra & Tools
    {"canonical_name": "Docker", "aliases": ["Docker"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Kubernetes", "aliases": ["Kubernetes", "k8s"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Microservices", "aliases": ["Microservices", "Micro-services", "Microservice"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "FastAPI", "aliases": ["FastAPI"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "REST API", "aliases": ["REST API", "RESTful API", "REST", "RESTful"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "AWS", "aliases": ["AWS", "Amazon Web Services"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "GCP", "aliases": ["GCP", "Google Cloud Platform", "Google Cloud"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Azure", "aliases": ["Azure", "Microsoft Azure"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Linux", "aliases": ["Linux"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Unix", "aliases": ["Unix", "UNIX"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Shell Scripting", "aliases": ["Shell Scripting", "Bash Scripting"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Git", "aliases": ["Git"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "GitHub Actions", "aliases": ["GitHub Actions"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "CI/CD", "aliases": ["CI/CD", "CICD", "Continuous Integration", "Continuous Delivery", "Continuous Deployment"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Jenkins", "aliases": ["Jenkins"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Perforce", "aliases": ["Perforce", "P4"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Ansible", "aliases": ["Ansible"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Automation", "aliases": ["Automation"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Automation/Scripting", "aliases": ["Automation/Scripting", "Scripting"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Distributed Systems", "aliases": ["Distributed Systems"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Virtualization", "aliases": ["Virtualization", "Virtualisation"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Hardware Virtualization", "aliases": ["Hardware Virtualization", "Hardware Virtualisation"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Containers", "aliases": ["Containers", "Containerization", "Containerisation"], "group": "Infra & Tools", "is_ambiguous": False, "requires_case_sensitive": False},

    # Systems, GPU & Performance
    {"canonical_name": "CUDA", "aliases": ["CUDA"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "GPU", "aliases": ["GPU", "GPUs"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "GPU Computing", "aliases": ["GPU Computing"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Accelerated Computing", "aliases": ["Accelerated Computing"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Parallel Programming", "aliases": ["Parallel Programming", "Parallel Computing"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "HPC", "aliases": ["HPC", "High Performance Computing", "High-Performance Computing"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "OpenMP", "aliases": ["OpenMP"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "MPI", "aliases": ["MPI", "Message Passing Interface"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "SLURM", "aliases": ["SLURM", "Slurm"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "LSF", "aliases": ["LSF"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Schedulers", "aliases": ["Schedulers", "Scheduler"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Performance Modeling", "aliases": ["Performance Modeling", "Performance Modelling"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Profiling", "aliases": ["Profiling"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Optimization", "aliases": ["Optimization", "Optimisation"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Performance Tuning", "aliases": ["Performance Tuning"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Operating Systems", "aliases": ["Operating Systems"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Scheduling", "aliases": ["Scheduling"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Memory Management", "aliases": ["Memory Management"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Process Control", "aliases": ["Process Control"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "cuBLAS", "aliases": ["cuBLAS"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "cuDNN", "aliases": ["cuDNN"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "NCCL", "aliases": ["NCCL"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "TensorRT", "aliases": ["TensorRT"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
    {"canonical_name": "Real-Time Inference", "aliases": ["Real-Time Inference", "Real Time Inference", "Realtime Inference"], "group": "Systems, GPU & Performance", "is_ambiguous": False, "requires_case_sensitive": False},
]


def seed(session) -> tuple[int, int]:
    """Upsert every catalog entry by ``canonical_name``. Returns (created, updated)."""
    created = 0
    updated = 0

    for entry in SKILL_CATALOG:
        skill = session.scalar(
            select(Skill).where(Skill.canonical_name == entry["canonical_name"])
        )

        if skill is None:
            session.add(Skill(**entry))
            created += 1
        else:
            skill.aliases = entry["aliases"]
            skill.group = entry["group"]
            skill.is_ambiguous = entry["is_ambiguous"]
            skill.requires_case_sensitive = entry["requires_case_sensitive"]
            updated += 1

    session.commit()
    return created, updated


def main() -> None:
    catalog_names = [entry["canonical_name"] for entry in SKILL_CATALOG]
    duplicates = {name for name in catalog_names if catalog_names.count(name) > 1}
    if duplicates:
        raise SystemExit(f"Duplicate canonical_name(s) in SKILL_CATALOG: {sorted(duplicates)}")

    with SessionLocal() as session:
        created, updated = seed(session)
        total = session.scalar(select(func.count()).select_from(Skill))

    print(f"Catalog entries : {len(SKILL_CATALOG)}")
    print(f"Skills created  : {created}")
    print(f"Skills updated  : {updated}")
    print(f"SELECT COUNT(*) FROM skills; -> {total}")


if __name__ == "__main__":
    main()
