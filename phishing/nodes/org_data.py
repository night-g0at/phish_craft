import re
from phishing.llm import make_chat
from phishing.state import PhishingState, OrgData

_llm = make_chat(model="claude-haiku-4-5-20251001", temperature=0).with_structured_output(OrgData)

_SYSTEM = (
    "You are extracting structured company data for a cybersecurity awareness training tool. "
    "From the provided text, determine: the company name, its primary website URL (just the domain, "
    "no path), a one-sentence description of what the company does, and pass through any other "
    "persona or targeting information unchanged in 'other_information'. "
    "For the domain, use the company's exact official corporate domain as it appears in their website "
    "address bar — use the full domain (e.g. 'firstenergycorp.com', 'jpmorganchase.com') rather than "
    "shortened or guessed variants (e.g. not 'firstenergy.com', not 'jpmorgan.com')."
)


def _clean_domain(url: str) -> str:
    url = re.sub(r"^https?://", "", url)
    url = url.rstrip("/").split("/")[0]
    return url


async def extract_org_data(state: PhishingState) -> dict:
    text = f"Scenario: {state['scenario']}\n\nOriginal input: {state['user_input']}"
    result: OrgData = await _llm.ainvoke([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": text},
    ])
    result.company_url = _clean_domain(result.company_url)
    return {"org_data": result}
