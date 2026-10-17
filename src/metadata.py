from .gemini import generate_json

def build(topic, script):
    prompt = (
        "You write YouTube metadata for a faceless psychology and self-discipline channel "
        "called Red Thread Mind. Audience: US English viewers.\n"
        f"Topic: {topic}\n"
        f"Script: {script[:3000]}\n\n"
        "Return a JSON object with:\n"
        '  "titles": 5 clickable titles, each under 70 characters, using proven frames '
        'when they fit: "The Art of ...", "The Psychology of ...", "How to ... (qualifier)". '
        "No all-caps words, no false claims.\n"
        '  "description": two short paragraphs with a hook and the key takeaways. No links.\n'
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