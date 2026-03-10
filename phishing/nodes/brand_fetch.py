import os
import httpx
from pydantic import ValidationError
from phishing.state import PhishingState, BrandData

_BRANDFETCH_BASE = "https://api.brandfetch.io/v2/brands"


async def fetch_brand_data(state: PhishingState) -> dict:
    api_key = os.environ.get("BRANDFETCH_API_KEY")
    domain = state["org_data"].company_url

    if not api_key:
        # No key — let the email builder use Claude's built-in brand knowledge
        return {"brand_data": None}

    url = f"{_BRANDFETCH_BASE}/{domain}"

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            resp.raise_for_status()
            raw = resp.json()
        except httpx.HTTPStatusError as e:
            return {
                "brand_data": BrandData(name=state["org_data"].company_name, domain=domain),
                "errors": [f"BrandFetch {e.response.status_code} for {domain}: {e}"],
            }
        except Exception as e:
            return {
                "brand_data": BrandData(name=state["org_data"].company_name, domain=domain),
                "errors": [f"BrandFetch request failed for {domain}: {e}"],
            }

    try:
        brand = BrandData.model_validate(raw)
    except ValidationError as e:
        # Parse what we can; fall back to minimal data
        brand = BrandData(
            name=raw.get("name", state["org_data"].company_name),
            domain=domain,
            description=raw.get("description"),
        )
        return {"brand_data": brand, "errors": [f"BrandFetch parse error: {e}"]}

    return {"brand_data": brand}
