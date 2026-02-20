"""Test bibliography verification against a real PDF.

Usage:
    pytest test_bibliography.py -s
    pytest test_bibliography.py -s --pdf path/to/other.pdf
"""

import pytest
from pypdf import PdfReader
from bibliography import verify_bibliography


def pytest_addoption(parser):
    parser.addoption(
        "--pdf", default="test.pdf", help="Path to the PDF essay to test"
    )


@pytest.fixture
def essay_text(request):
    pdf_path = request.config.getoption("--pdf")
    reader = PdfReader(pdf_path)
    text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
    assert text.strip(), f"Could not extract text from {pdf_path}"
    return text


def test_bibliography_verification(essay_text):
    results = verify_bibliography(essay_text)

    assert len(results) > 0, "No references were extracted from the essay"

    print(f"\n{'='*60}")
    print(f"Found {len(results)} references\n")

    for r in results:
        status = "VERIFIED" if r["verified"] else "UNVERIFIED"
        print(f"[{status}] {r['reference']}")
        print(f"  URLs:  {r.get('search_urls', [])}")
        print(f"  Notes: {r['notes']}\n")

    verified = [r for r in results if r["verified"]]
    print(f"{'='*60}")
    print(f"Summary: {len(verified)}/{len(results)} references verified")
