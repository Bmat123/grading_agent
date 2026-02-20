"""Standalone bibliography verification module.

Can be tested independently without running the full grading agent.

Usage:
    python bibliography.py "Smith, J. (2020). Deep Learning. Nature, 521, 436-444."
    python bibliography.py --essay path/to/essay.pdf
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from dotenv import load_dotenv
from googlesearch import search
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def _invoke_llm(prompt: str) -> str:
    """Invoke Gemini and return the response as a plain string."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0,
        max_output_tokens=4096,
        model_kwargs={"thinking_config": {"thinking_budget": 0}},
    )
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "\n".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in content
        )
    return content


def _parse_json_from_text(text: str):
    """Extract and parse JSON from LLM response text."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


def search_single_reference(reference: str) -> dict:
    """Search Google to verify a single bibliographic reference.

    Args:
        reference: The full reference string.

    Returns:
        Dict with keys: reference, verified, search_urls, notes.
    """
    result = {
        "reference": reference,
        "verified": False,
        "search_urls": [],
        "notes": "",
    }

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                lambda: list(search(reference, num_results=3, lang="en"))
            )
            try:
                urls = future.result(timeout=10)
            except TimeoutError:
                result["notes"] = "Search timed out."
                return result
        time.sleep(0.5)

        result["search_urls"] = urls

        if not urls:
            result["notes"] = "No search results found. Reference may not exist."
        else:
            result["notes"] = f"Found {len(urls)} search results."
        return result

    except Exception as e:
        result["notes"] = f"Search failed: {str(e)}"
        return result


def extract_references_with_llm(essay_text: str) -> list[str]:
    """Use Gemini to extract bibliographic references from essay text.

    Args:
        essay_text: The full essay text.

    Returns:
        List of reference strings.
    """
    prompt = (
        "Extract ALL bibliographic references from the following essay text. "
        "Return ONLY a JSON array of strings, where each string is one full reference "
        "exactly as it appears in the essay. If there are no references, return an empty array [].\n\n"
        f"Essay text:\n{essay_text}"
    )

    content = _invoke_llm(prompt)

    try:
        refs = _parse_json_from_text(content)
        if isinstance(refs, list):
            return [str(r) for r in refs]
    except (json.JSONDecodeError, IndexError):
        pass

    return []


def verify_references_with_llm(references: list[dict]) -> list[dict]:
    """Use Gemini to assess whether search results confirm each reference.

    Args:
        references: List of dicts from search_single_reference.

    Returns:
        Updated list with 'verified' and 'notes' set by LLM assessment.
    """
    refs_with_urls = [r for r in references if r.get("search_urls")]
    if not refs_with_urls:
        return references

    ref_details = []
    for r in references:
        ref_details.append({
            "reference": r["reference"],
            "search_urls": r.get("search_urls", []),
            "search_notes": r.get("notes", ""),
        })

    prompt = (
        "You are verifying bibliographic references. For each reference below, "
        "I provide the Google search result URLs. Assess whether the reference "
        "is likely REAL and correctly cited (correct authors, year, title, journal/publisher). "
        "Be skeptical — if the URLs don't clearly confirm the reference, mark it unverified.\n\n"
        f"References:\n{json.dumps(ref_details, indent=2)}\n\n"
        "Respond with a JSON array where each element has:\n"
        '  {"reference": "...", "verified": true/false, "notes": "explanation"}\n'
        "Return ONLY the JSON array."
    )

    content = _invoke_llm(prompt)

    try:
        llm_results = _parse_json_from_text(content)
        if isinstance(llm_results, list):
            llm_map = {r["reference"]: r for r in llm_results}
            for ref in references:
                if ref["reference"] in llm_map:
                    llm_ref = llm_map[ref["reference"]]
                    ref["verified"] = llm_ref.get("verified", False)
                    ref["notes"] = llm_ref.get("notes", ref["notes"])
    except (json.JSONDecodeError, IndexError):
        for ref in references:
            ref["notes"] += " (LLM verification failed to parse)"

    return references


def verify_bibliography(essay_text: str) -> list[dict]:
    """Full pipeline: extract references from essay, search, and verify.

    Args:
        essay_text: The full essay text.

    Returns:
        List of dicts with: reference, verified, search_urls, notes.
    """
    ref_strings = extract_references_with_llm(essay_text)
    if not ref_strings:
        return []

    search_results = [search_single_reference(ref) for ref in ref_strings]
    verified_results = verify_references_with_llm(search_results)

    return verified_results


if __name__ == "__main__":
    import sys
    from pypdf import PdfReader

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python bibliography.py 'Author (2020). Title. Journal.'")
        print("  python bibliography.py --essay path/to/essay.pdf")
        sys.exit(1)

    if sys.argv[1] == "--essay":
        pdf_path = sys.argv[2]
        reader = PdfReader(pdf_path)
        text = "\n\n".join(p.extract_text() or "" for p in reader.pages)

        print(f"Extracted {len(text)} characters from {pdf_path}")
        print("Running full bibliography verification pipeline...\n")

        results = verify_bibliography(text)

        if not results:
            print("No references found in the essay.")
        else:
            for r in results:
                status = "VERIFIED" if r["verified"] else "UNVERIFIED"
                print(f"[{status}] {r['reference']}")
                print(f"  URLs: {r.get('search_urls', [])}")
                print(f"  Notes: {r['notes']}\n")
    else:
        ref = " ".join(sys.argv[1:])
        print(f"Searching for: {ref}\n")
        result = search_single_reference(ref)
        print(json.dumps(result, indent=2))
