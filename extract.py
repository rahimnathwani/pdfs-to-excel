"""LLM-based extraction using OpenAI's structured output parsing."""

from openai import OpenAI


def chunk_with_nodes(text: str, chunk_size: int = 500) -> str:
    """Split text into chunks, prepend [NODE N] markers, return concatenated result."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        node_num = (i // chunk_size) + 1
        chunks.append(f"[NODE {node_num}] {chunk}")
    return "\n".join(chunks)


def resolve_citations(result: dict, original_text: str, chunk_size: int = 500) -> dict:
    """For any key ending in _citation, resolve NODE N references to actual text chunks."""
    import re

    # Build a mapping from node number to text chunk
    node_map = {}
    for i in range(0, len(original_text), chunk_size):
        node_num = (i // chunk_size) + 1
        node_map[node_num] = original_text[i : i + chunk_size]

    resolved = {}
    for key, value in result.items():
        if key.endswith("_citation") and isinstance(value, str):
            # Find all NODE N references and replace with actual text
            def replace_node(match):
                node_num = int(match.group(1))
                return node_map.get(node_num, match.group(0))

            resolved[key] = re.sub(r"NODE\s+(\d+)", replace_node, value)
        else:
            resolved[key] = value
    return resolved


def extract_from_text(
    text: str,
    model_class: type,
    openai_model: str,
    system_prompt: str,
    skip_citations: bool = False,
) -> dict | None:
    """Extract structured data from text using OpenAI's responses.parse API.

    Args:
        text: The source text to extract from.
        model_class: A Pydantic model class defining the extraction schema.
        openai_model: The OpenAI model name to use (e.g. "gpt-4o").
        system_prompt: System-level instructions for the LLM.
        skip_citations: If True, skip NODE marker chunking and citation resolution.

    Returns:
        A dict of extracted fields, or None on error.
    """
    try:
        client = OpenAI()

        if skip_citations:
            input_text = text
        else:
            input_text = chunk_with_nodes(text)

        response = client.responses.parse(
            model=openai_model,
            instructions=system_prompt,
            input=[{"role": "user", "content": input_text}],
            text_format=model_class,
        )
        result = response.output_parsed

        if result is None:
            print("Error: LLM returned no parsed output.")
            return None

        result_dict = result.model_dump()

        if not skip_citations:
            result_dict = resolve_citations(result_dict, text)

        return result_dict

    except Exception as e:
        print(f"Error during extraction: {e}")
        return None
