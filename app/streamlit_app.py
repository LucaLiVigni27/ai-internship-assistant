import requests
import pandas as pd
import streamlit as st


API_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="AI Internship Assistant",
    page_icon="💼",
    layout="wide",
)


def get_applications():
    try:
        response = requests.get(f"{API_URL}/applications", timeout=10)
        response.raise_for_status()
        return response.json()
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


st.title("AI Internship Assistant")

st.write(
    "Track internship applications, analyze job descriptions, and match roles "
    "to your resume and projects."
)

tab1, tab2, tab3 = st.tabs(
    ["Application Tracker", "Job Description Analyzer", "Ask the Assistant"]
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
    st.write("Paste a job description to extract important skills, focus areas, and suggestions for what to highlight.")

    job_description_text = st.text_area(
        "Paste job description",
        height=300,
        placeholder="Paste an internship posting here...",

    )

    analyze_button = st.button("Analyze job description")

    if analyze_button:
        if not job_description_text.strip():
            st.warning("paste a job description first.")
        else:
            try:
                analysis = analyze_job_description(job_description_text)
                st.success("Job description analyzed.")

                metric_col1, metric_col2, metric_col3 = st.columns(3)
                metric_col1.metric(
                    "Characters analyzed",
                    f"{analysis['character_count']:,}",
                )
                metric_col2.metric(
                    "Matched skills",
                    len(analysis["matched_skills"]),
                )
                top_group = (
                    analysis["top_groups"][0]["group"]
                    if analysis["top_groups"]
                    else "None"
                )
                metric_col3.metric("Top focus area", top_group)

                st.subheader("Matched skills by category")

                if analysis["matched_skills_by_group"]:
                    for group, skills in analysis["matched_skills_by_group"].items():
                        st.markdown(f"**{group}**")
                        st.write(", ".join(skills))
                else:
                    st.info("No tracked skills were found.")

                st.subheader("Top focus areas")

                if analysis["top_groups"]:
                    st.dataframe(
                        pd.DataFrame(analysis["top_groups"]),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info("No focus area found.")

                st.subheader("What to highlight")

                for suggestion in analysis["suggested_focus"]:
                    st.write(f"- {suggestion}")

            except requests.exceptions.RequestException as error:
                st.error(f"Could not analyze job description: {error}")

with tab3:
    st.header("Ask the Assistant")
    st.write("This section will answer questions using SQL + vector search.")