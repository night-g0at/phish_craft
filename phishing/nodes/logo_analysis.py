import asyncio
from langchain_anthropic import ChatAnthropic
from phishing.state import PhishingState, BrandData, Logo, LogoFormat

_llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=200)
_SEM = asyncio.Semaphore(5)

_VISION_RASTER = {"png", "jpg", "jpeg", "webp"}

_SYSTEM = (
    "You are evaluating a company logo for use in a phishing awareness training email. "
    "Assess: (1) clarity at small sizes, (2) whether it will render well on a white email background, "
    "(3) overall visual recognizability. Reply in one sentence, then on a new line write exactly "
    "'USABLE: YES' or 'USABLE: NO'."
)


async def _analyze_single(fmt: LogoFormat) -> LogoFormat:
    async with _SEM:
        try:
            response = await _llm.ainvoke([
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": fmt.src}},
                        {"type": "text", "text": "Evaluate this logo for email use."},
                    ],
                },
            ])
            text = response.content
            usable = "USABLE: YES" in text.upper()
            analysis = text.split("USABLE:")[0].strip()
        except Exception as e:
            analysis = f"Analysis failed: {e}"
            usable = False

    return fmt.model_copy(update={"analysis": analysis, "usable": usable})


async def analyze_logos(state: PhishingState) -> dict:
    brand = state.get("brand_data")
    if not brand or not brand.logos:
        return {}

    updated_logos: list[Logo] = []
    for logo in brand.logos:
        updated_formats: list[LogoFormat] = []
        tasks = []
        raster_indices = []

        for i, fmt in enumerate(logo.formats):
            if fmt.format.lower() in _VISION_RASTER:
                tasks.append(_analyze_single(fmt))
                raster_indices.append(i)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        result_map = {}
        for idx, result in zip(raster_indices, results):
            if not isinstance(result, Exception):
                result_map[idx] = result

        for i, fmt in enumerate(logo.formats):
            updated_formats.append(result_map.get(i, fmt))

        updated_logos.append(logo.model_copy(update={"formats": updated_formats}))

    updated_brand = brand.model_copy(update={"logos": updated_logos})
    return {"brand_data": updated_brand}
