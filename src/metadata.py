from .gemini import generate_json


def build(topic, script, avoid=None):
    avoid_text = "; ".join(avoid) if avoid else "none"
    prompt = (
        "You write YouTube metadata for a faceless psychology and self-discipline channel "
        "called Red Thread Mind. Audience: US English viewers.\n"
        f"Topic: {topic}\n"
        f"Script: {script[:3000]}\n\n"
        f"Titles already used. Do not repeat or closely reword them: {avoid_text}\n\n"
        "Return a JSON object with:\n"
        '  "titles": 5 specific, clickable titles under 70 characters. Each names one concrete '
        'idea from the script. Use frames like "The Art of ...", "The Psychology of ...", or '
        '"How to ... (qualifier)" only when they fit. No all-caps words, no false claims.\n'
        '  "description": two short paragraphs. The first states one specific idea from the script '
        "as a personal observation. End with one question that invites viewers to comment. No links.\n"
        '  "tags": 15 relevant search tags.\n'
        "Return only the JSON object."
    )
    data = generate_json(prompt)
    titles = [str(t)[:90] for t in data.get("titles", [])][:5] or [topic[:90]]
    return {
        "titles": titles,
        "description": str(data.get("description", topic)),
        "tags": [str(t)[:30] for t in data.get("tags", [])][:15],
    }