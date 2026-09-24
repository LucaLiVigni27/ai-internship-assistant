import os
import requests
import pandas as pd
import streamlit as st


API_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


st.set_page_config(
    page_title="AI Internship Assistant",
    page_icon="💼",
    layout="wide",
)


def get_applications():
    try:
        response = requests.get(f"{API_URL}/applications", timeout=10)
        response.raise_for_status()
        applications = response.json()
        for application in applications:
            posting = application.get("job_posting") or {}
            application["company"] = posting.get("company")
            application["role"] = posting.get("role")
            application["location"] = posting.get("location")
        return applications
    except requests.exceptions.RequestException:
        st.error(
            "Could not connect to the backend."
        )
        return []


def create_application(application_data):
    response = requests.post(
        f"{API_URL}/applications",
        json=application_data,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def delete_application(application_id):
    response = requests.delete(
        f"{API_URL}/applications/{application_id}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def empty_to_none(value):
    if value is None:
        return None

    value = str(value).strip()
    return value if value else None

def analyze_job_description(job_description_text):
    response = requests.post(
        f"{API_URL}/job-descriptions/analyze",
        json={"text": job_description_text},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_job_postings():
    try:
        response = requests.get(f"{API_URL}/job-postings", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        st.error("Could not connect to the backend.")
        return []


def get_documents():
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        st.error("Could not connect to the backend.")
        return []


def get_analyses():
    response = requests.get(f"{API_URL}/analyses", timeout=10)
    response.raise_for_status()
    return response.json()


def ask_assistant(query, source_type=None, top_k=5):
    payload = {"query": query, "top_k": top_k, "source_type": source_type}
    response = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def run_match(job_posting_id, document_ids):
    payload = {"document_ids": document_ids} if document_ids else {}
    response = requests.post(
        f"{API_URL}/job-postings/{job_posting_id}/match", json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()


def render_citations(citations):
    if not citations:
        st.caption("No citations returned.")
        return
    st.subheader("Citations")
    for citation in citations:
        with st.expander(citation["chunk_id"]):
            st.write(citation["quote"])


st.title("AI Internship Assistant")

st.write(
    "Track internship applications, analyze job descriptions, and match roles "
    "to your resume and projects."
)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Application Tracker",
        "Job Description Analyzer",
        "Ask the Assistant",
        "Match Resume to Posting",
        "Saved Analyses",
    ]
)


with tab1:
    st.header("Application Tracker")
    st.write("Save and manage structured internship applications.")

    with st.form("application_form", clear_on_submit=True):
        st.subheader("Add a new internship")

        col1, col2 = st.columns(2)

        with col1:
            company = st.text_input("Company")
            role = st.text_input("Role")
            location = st.text_input("Location")
            status = st.selectbox(
                "Status",
                ["Interested", "Applied", "Interviewing", "Rejected", "Offer"],
            )

        with col2:
            deadline = st.text_input("Deadline", placeholder="YYYY-MM-DD")
            date_applied = st.text_input("Date applied", placeholder="YYYY-MM-DD")
            link = st.text_input("Job link")
            skills = st.text_area("Skills", placeholder="Python, SQL, RAG, Docker")

        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save application")

        if submitted:
            if not company or not role:
                st.warning("Company and role are required.")
            else:
                application_data = {
                    "company": company,
                    "role": role,
                    "location": empty_to_none(location),
                    "status": status,
                    "deadline": empty_to_none(deadline),
                    "date_applied": empty_to_none(date_applied),
                    "link": empty_to_none(link),
                    "skills": empty_to_none(skills),
                    "notes": empty_to_none(notes),
                }

                try:
                    create_application(application_data)
                    st.success("Application saved.")
                except requests.exceptions.RequestException as error:
                    st.error(f"Could not save application: {error}")

    st.divider()

    st.subheader("Saved applications")

    applications = get_applications()

    if applications:
        applications_df = pd.DataFrame(applications)

        display_columns = [
            "id",
            "company",
            "role",
            "location",
            "status",
            "deadline",
            "date_applied",
            "skills",
            "notes",
            "link",
        ]

        existing_columns = [
            column for column in display_columns if column in applications_df.columns
        ]

        st.dataframe(
            applications_df[existing_columns],
            width="stretch",
            hide_index=True,
        )

        st.subheader("Delete an application")

        application_options = {
            f"{application['id']} — {application['company']} | {application['role']}": application["id"]
            for application in applications
        }

        selected_application = st.selectbox(
            "Choose an application to delete",
            list(application_options.keys()),
        )

        if st.button("Delete selected application"):
            try:
                delete_application(application_options[selected_application])
                st.success("Application deleted.")
                st.rerun()
            except requests.exceptions.RequestException as error:
                st.error(f"Could not delete application: {error}")
    else:
        st.info("No applications saved yet.")


with tab2:
    st.header("Job Description Analyzer")
    st.write(
        "Paste a job description to extract required/preferred skills, "
        "responsibilities, and other key details."
    )

    job_description_text = st.text_area(
        "Paste job description",
        height=300,
        placeholder="Paste an internship posting here...",
    )

    analyze_button = st.button("Analyze job description")

    if analyze_button:
        if not job_description_text.strip():
            st.warning("Paste a job description first.")
        else:
            try:
                analysis = analyze_job_description(job_description_text)
                st.success("Job description analyzed.")

                metric_col1, metric_col2, metric_col3 = st.columns(3)
                metric_col1.metric("Required skills", len(analysis["required_skills"]))
                metric_col2.metric("Preferred skills", len(analysis["preferred_skills"]))
                metric_col3.metric("Other mentions", len(analysis["mentioned_skills"]))

                def render_skill_list(title, skills):
                    st.subheader(title)
                    if not skills:
                        st.info("None found.")
                        return
                    for skill in skills:
                        st.markdown(f"**{skill['name']}**")
                        if skill.get("evidence"):
                            st.caption(skill["evidence"])

                render_skill_list("Required skills", analysis["required_skills"])
                render_skill_list("Preferred skills", analysis["preferred_skills"])
                render_skill_list("Other mentions", analysis["mentioned_skills"])

                if analysis.get("potential_untracked_skills"):
                    st.subheader("Potential untracked (soft) skills")
                    st.caption("Mentioned in the posting but not part of the tracked technical skill catalog.")
                    st.write(", ".join(analysis["potential_untracked_skills"]))

                if analysis.get("responsibilities"):
                    st.subheader("Responsibilities")
                    for item in analysis["responsibilities"]:
                        st.write(f"- {item['text']}")

                detail_fields = [
                    ("Min. experience", "min_experience"),
                    ("Education", "education"),
                    ("Location", "location"),
                    ("Work arrangement", "work_arrangement"),
                    ("Work authorization", "work_authorization"),
                    ("Salary", "salary"),
                    ("Deadline", "deadline"),
                    ("Employment type", "employment_type"),
                ]
                present_details = [
                    (label, analysis[key]) for label, key in detail_fields if analysis.get(key)
                ]
                if present_details:
                    st.subheader("Other details")
                    for label, field in present_details:
                        st.write(f"**{label}:** {field['value']}")

            except requests.exceptions.RequestException as error:
                st.error(f"Could not analyze job description: {error}")

with tab3:
    st.header("Ask the Assistant")
    st.write(
        "Ask a question grounded in your indexed job postings and resume/project "
        "documents. Every answer cites the exact chunks it's based on."
    )

    query = st.text_input(
        "Your question",
        placeholder="e.g. Which postings mention Docker or Kubernetes?",
    )
    scope_choice = st.selectbox(
        "Scope", ["Everything", "Job postings only", "My documents only"]
    )
    scope_map = {"Everything": None, "Job postings only": "job_posting", "My documents only": "document"}

    if st.button("Ask"):
        if not query.strip():
            st.warning("Type a question first.")
        else:
            try:
                with st.spinner("Thinking..."):
                    result = ask_assistant(query, source_type=scope_map[scope_choice])

                if not result["sufficient_context"]:
                    st.warning(
                        "⚠️ Insufficient context — the indexed postings/documents don't "
                        "contain enough information to answer this confidently."
                    )

                st.markdown(result["answer"])
                render_citations(result["citations"])

            except requests.exceptions.RequestException as error:
                st.error(f"Could not get an answer: {error}")

with tab4:
    st.header("Match Resume to a Job Posting")
    st.write(
        "Pick a job posting and see which of its required/preferred skills your "
        "resume and projects cover, plus a grounded explanation of the match."
    )

    postings = get_job_postings()
    documents = get_documents()

    if not postings:
        st.info("No job postings saved yet. Add one via POST /job-postings first.")
    elif not documents:
        st.info("No resume/project documents uploaded yet. Upload one via POST /documents/upload first.")
    else:
        posting_options = {
            f"{posting['id']} — {posting['company']} | {posting['role']}": posting["id"]
            for posting in postings
        }
        selected_posting_label = st.selectbox("Job posting", list(posting_options.keys()))
        selected_posting_id = posting_options[selected_posting_label]

        document_options = {
            f"{document['id']} — {document['title']} ({document['document_type']})": document["id"]
            for document in documents
        }
        selected_document_labels = st.multiselect(
            "Documents to match against (leave empty to use all of them)",
            list(document_options.keys()),
        )
        selected_document_ids = [document_options[label] for label in selected_document_labels]

        if st.button("Run match"):
            try:
                with st.spinner("Matching..."):
                    result = run_match(selected_posting_id, selected_document_ids)

                score = result["match_score"]
                score_display = f"{score:.0%}" if score is not None else "N/A"

                metric_col1, metric_col2, metric_col3 = st.columns(3)
                metric_col1.metric("Match score", score_display)
                metric_col2.metric(
                    "Matched required",
                    f"{len(result['matched_required_skills'])}/{result['total_required']}",
                )
                metric_col3.metric(
                    "Matched preferred",
                    f"{len(result['matched_preferred_skills'])}/{result['total_preferred']}",
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("✅ Matched required")
                    st.write(", ".join(result["matched_required_skills"]) or "None")
                    st.subheader("✅ Matched preferred")
                    st.write(", ".join(result["matched_preferred_skills"]) or "None")
                with col2:
                    st.subheader("❌ Missing required")
                    st.write(", ".join(result["missing_required_skills"]) or "None")
                    st.subheader("❌ Missing preferred")
                    st.write(", ".join(result["missing_preferred_skills"]) or "None")

                if not result["sufficient_context"]:
                    st.warning("⚠️ Insufficient context for a fully grounded explanation.")

                st.subheader("Explanation")
                st.markdown(result["answer"])
                render_citations(result["citations"])

            except requests.exceptions.RequestException as error:
                st.error(f"Could not run match: {error}")

with tab5:
    st.header("Saved Analyses")
    st.write("Every skill-extraction and match run that's been saved, most recent first.")

    try:
        analyses = get_analyses()
    except requests.exceptions.RequestException as error:
        st.error(f"Could not load analyses: {error}")
        analyses = []

    if not analyses:
        st.info("No analyses saved yet.")
    else:
        for run in analyses:
            posting = run["job_posting"]
            title = f"{posting['company']} — {posting['role']} | {run['extractor_type']} | {run['created_at']}"
            with st.expander(title):
                st.write(f"**Extractor:** {run['extractor_type']} (v{run['extractor_version']})")
                if run.get("model_name"):
                    st.write(f"**Model:** {run['model_name']}")
                if run.get("latency_ms") is not None:
                    st.write(f"**Latency:** {run['latency_ms']}ms")

                result = run["structured_result"]
                if run["extractor_type"] == "match":
                    score = result.get("match_score")
                    st.write(f"**Match score:** {f'{score:.0%}' if score is not None else 'N/A'}")
                    st.write(f"**Matched required:** {', '.join(result.get('matched_required_skills', [])) or 'None'}")
                    st.write(f"**Missing required:** {', '.join(result.get('missing_required_skills', [])) or 'None'}")
                else:
                    required = [s["name"] for s in result.get("required_skills", [])]
                    preferred = [s["name"] for s in result.get("preferred_skills", [])]
                    st.write(f"**Required skills:** {', '.join(required) or 'None'}")
                    st.write(f"**Preferred skills:** {', '.join(preferred) or 'None'}")
                    if result.get("potential_untracked_skills"):
                        st.write(f"**Potential untracked skills:** {', '.join(result['potential_untracked_skills'])}")
