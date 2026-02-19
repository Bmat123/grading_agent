import json
import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from prompts import SYSTEM_PROMPT, GRADING_PROMPT
from tools import search_reference

load_dotenv()


def create_grading_agent():
    """Create and return the grading agent."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.1,
        max_output_tokens=8192,
        timeout=120,
        model_kwargs={"thinking_config": {"thinking_budget": 0}},
    )

    agent = create_react_agent(
        model=llm,
        tools=[search_reference],
        prompt=SYSTEM_PROMPT,
    )

    return agent


def grade_essay(criteria_text: str, essay_text: str) -> dict:
    """Grade an essay against the provided criteria.

    Args:
        criteria_text: The grading criteria text.
        essay_text: The student's essay text.

    Returns:
        A dictionary with grading results.
    """
    agent = create_grading_agent()

    prompt = GRADING_PROMPT.format(
        criteria_text=criteria_text,
        essay_text=essay_text,
    )

    result = agent.invoke(
        {"messages": [("user", prompt)]},
        config={"recursion_limit": 30},
    )

    # Extract the final AI message content
    final_message = result["messages"][-1].content
    # Gemini may return content as a list of parts — extract text parts
    if isinstance(final_message, list):
        final_message = "\n".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in final_message
        )

    # Try to parse JSON from the response
    try:
        # The model might wrap JSON in markdown code blocks
        text = final_message
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        # Return raw text if JSON parsing fails
        return {
            "raw_response": final_message,
            "parse_error": True,
        }
