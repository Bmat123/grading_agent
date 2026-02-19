import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pypdf import PdfReader
from langchain_core.tools import tool
from googlesearch import search


def extract_pdf_text(pdf_file) -> str:
    """Extract all text from an uploaded PDF file."""
    reader = PdfReader(pdf_file)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def extract_text_from_file(uploaded_file) -> str:
    """Extract text from an uploaded file (PDF or TXT)."""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)
    else:
        return uploaded_file.read().decode("utf-8", errors="replace")


@tool
def search_reference(reference: str) -> str:
    """Search Google to verify whether a bibliographic reference exists and is correctly cited.

    Args:
        reference: The full bibliographic reference string to verify (e.g. 'Smith, J. (2020). Title of Paper. Journal Name, 15(2), 45-60.')

    Returns:
        A summary of search results indicating whether the reference appears to be real.
    """
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: list(search(reference, num_results=3, lang="en")))
            try:
                results = future.result(timeout=10)
            except TimeoutError:
                return f"Search timed out for '{reference}'. Could not verify this reference."
        time.sleep(0.5)

        if not results:
            return (
                f"NO RESULTS FOUND for: '{reference}'. "
                "This reference may not exist or may be incorrectly cited."
            )

        result_text = f"Search results for: '{reference}':\n"
        for i, url in enumerate(results, 1):
            result_text += f"  {i}. {url}\n"
        result_text += (
            "\nBased on these results, assess whether the reference is real "
            "and correctly cited (authors, year, title, journal)."
        )
        return result_text

    except Exception as e:
        return f"Search failed for '{reference}': {str(e)}. Could not verify this reference."
