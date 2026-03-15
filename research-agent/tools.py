import os

import trafilatura
from ddgs import DDGS
from langchain_core.tools import tool

from config import Settings

settings = Settings()


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Returns a list of results with title, URL, and snippet for each.

    Args:
        query: The search query string.
    """
    try:
        results = DDGS().text(query, max_results=settings.max_search_results)
        if not results:
            return "No results found."
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. Title: {r.get('title', 'N/A')}\n"
                f"   URL: {r.get('href', 'N/A')}\n"
                f"   Snippet: {r.get('body', 'N/A')}"
            )
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Search error: {e}"


@tool
def read_url(url: str) -> str:
    """Fetch and extract the main text content from a web page. Use this to read full articles found via web_search.

    The result is truncated to avoid context overflow.

    Args:
        url: The full URL of the web page to read.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return f"Error: Could not fetch URL: {url}"
        text = trafilatura.extract(downloaded)
        if not text:
            return f"Error: Could not extract text from: {url}"
        if len(text) > settings.max_url_content_length:
            text = text[: settings.max_url_content_length] + "\n\n[... truncated]"
        return text
    except Exception as e:
        return f"Error reading URL: {e}"


@tool
def write_report(filename: str, content: str) -> str:
    """Save a Markdown research report to a file in the output directory.

    Args:
        filename: Name of the file (e.g. 'report.md').
        content: The full Markdown content of the report.
    """
    try:
        os.makedirs(settings.output_dir, exist_ok=True)
        if not filename.endswith(".md"):
            filename += ".md"
        filepath = os.path.join(settings.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Report saved successfully to: {filepath}"
    except Exception as e:
        return f"Error saving report: {e}"
