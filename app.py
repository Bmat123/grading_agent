import time
import streamlit as st
from tools import extract_text_from_file
from agent import grade_essay

st.set_page_config(page_title="Essay Grading Agent", layout="wide")

st.title("Essay Grading Agent")
st.markdown("Upload your grading criteria and a student essay to receive detailed, rigorous feedback.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Grading Criteria")
    criteria_mode = st.radio(
        "How would you like to provide the grading criteria?",
        ["Paste text", "Upload file"],
        horizontal=True,
        key="criteria_mode",
    )
    criteria_text_input = None
    criteria_file = None
    if criteria_mode == "Paste text":
        criteria_text_input = st.text_area(
            "Paste your grading criteria below",
            height=300,
            placeholder="e.g.\n1. Thesis clarity (20 pts): ...\n2. Use of evidence (20 pts): ...",
        )
    else:
        criteria_file = st.file_uploader(
            "Upload criteria document (PDF or TXT)",
            type=["pdf", "txt"],
            key="criteria",
        )

with col2:
    st.subheader("Student Essay")
    essay_file = st.file_uploader(
        "Upload student essay (PDF)",
        type=["pdf", "txt"],
        key="essay",
    )

has_criteria = (criteria_text_input and criteria_text_input.strip()) or criteria_file
if has_criteria and essay_file:
    if st.button("Grade Essay", type="primary", use_container_width=True):
        with st.spinner("Grading in progress — the agent is reading, evaluating, and verifying bibliography. This may take a few minutes..."):
            start_time = time.time()

            if criteria_text_input and criteria_text_input.strip():
                criteria_text = criteria_text_input.strip()
            else:
                criteria_text = extract_text_from_file(criteria_file)
            essay_text = extract_text_from_file(essay_file)

            if not criteria_text.strip():
                st.error("Could not extract text from the criteria. Please check your input.")
                st.stop()
            if not essay_text.strip():
                st.error("Could not extract text from the essay file. Please check the file.")
                st.stop()

            result = grade_essay(criteria_text, essay_text)
            elapsed = time.time() - start_time

        minutes, seconds = divmod(int(elapsed), 60)
        if minutes > 0:
            st.caption(f"Grading completed in {minutes}m {seconds}s")
        else:
            st.caption(f"Grading completed in {seconds}s")

        if result.get("parse_error"):
            st.warning("The agent returned a non-structured response. Showing raw output:")
            st.markdown(result.get("raw_response", "No response"))
            st.stop()

        # --- Display results ---

        # Overall score
        total = result.get("total_score", "N/A")
        max_total = result.get("max_total_score", "N/A")
        st.header(f"Overall Score: {total} / {max_total}")

        # Overall feedback
        st.markdown("### Overall Feedback")
        st.info(result.get("overall_feedback", ""))

        # Priority improvements
        improvements = result.get("priority_improvements", [])
        if improvements:
            st.markdown("### Top Priority Improvements")
            for i, imp in enumerate(improvements, 1):
                st.markdown(f"**{i}.** {imp}")

        st.divider()

        # Per-criterion results
        st.markdown("## Criterion-by-Criterion Feedback")
        for item in result.get("criteria_results", []):
            name = item.get("criterion_name", "Unknown Criterion")
            score = item.get("score", "?")
            max_score = item.get("max_score", "?")

            with st.expander(f"{name} — {score}/{max_score}", expanded=True):
                st.markdown("**Feedback:**")
                st.markdown(item.get("feedback", ""))
                suggestions = item.get("suggestions", "")
                if suggestions:
                    st.markdown("**Suggestions for improvement:**")
                    st.markdown(suggestions)

        st.divider()

        # Bibliography verification
        bib = result.get("bibliography", [])
        if bib:
            st.markdown("## Bibliography Verification")
            for ref in bib:
                verified = ref.get("verified", False)
                icon = "✅" if verified else "❌"
                with st.expander(f"{icon} {ref.get('reference', 'Unknown reference')[:100]}"):
                    st.markdown(f"**Verified:** {'Yes' if verified else 'No'}")
                    st.markdown(f"**Notes:** {ref.get('notes', 'No details')}")
        else:
            st.markdown("## Bibliography")
            st.warning("No bibliography references were found or extracted from the essay.")
else:
    st.info("Please provide grading criteria (paste or upload) and upload a student essay to begin.")
