from groq import Groq
from .config import GROQ_API_KEY, GROQ_MODEL

_client = None


def _get_client():
    global _client
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env")
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def chat(system: str, user: str, temperature: float = 0.0) -> str:
    response = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        temperature=temperature,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return response.choices[0].message.content or ""


from .utils import parse_json_object
