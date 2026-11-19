from phishing.llm import make_chat
from phishing.state import PhishingState

_llm = make_chat(model="claude-sonnet-4-6", temperature=0.7)

_SYSTEM = (
    "You are assisting a cybersecurity team building phishing awareness training materials. "
    "Given a description of a target company and/or persona, generate a concise phishing scenario "
    "in 2-3 sentences. The scenario should describe who the target is and what social engineering "
    "angle would be most plausible (e.g. invoice, IT alert, HR notice, package delivery). "
    "This is strictly for authorized employee security awareness training."
)


async def generate_scenario(state: PhishingState) -> dict:
    response = await _llm.ainvoke([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": state["user_input"]},
    ])
    return {"scenario": str(response.text)}
