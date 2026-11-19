import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class OrgData(BaseModel):
    company_name: str
    company_url: str
    company_description: str
    other_information: str = ""


class LogoFormat(BaseModel):
    src: str
    format: str
    background: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    analysis: Optional[str] = None
    usable: Optional[bool] = None


class Logo(BaseModel):
    theme: str = ""
    type: str = ""
    tags: list[str] = Field(default_factory=list)
    formats: list[LogoFormat] = Field(default_factory=list)


class BrandData(BaseModel):
    name: str = ""
    domain: str = ""
    description: Optional[str] = None
    logos: list[Logo] = Field(default_factory=list)
    colors: list[dict] = Field(default_factory=list)
    fonts: list[dict] = Field(default_factory=list)


class PhishingState(TypedDict):
    user_input: str
    override_domain: Optional[str]        # user-supplied domain, bypasses LLM extraction
    include_training_banner: bool         # whether to append training watermark
    include_landing_page: bool            # whether to also generate a matching landing page
    landing_debrief_message: Optional[str]  # custom message shown after a user submits the form
    gophish_mode: bool                    # format email + landing page for GoPhish import
    scenario: Optional[str]
    org_data: Optional[OrgData]
    brand_data: Optional[BrandData]
    html_email: Optional[str]
    landing_page_html: Optional[str]      # generated standalone landing page (None if skipped)
    landing_page_filename: Optional[str]  # relative filename the email CTA links to
    awareness_page_html: Optional[str]    # post-submit awareness page (GoPhish mode only)
    awareness_page_filename: Optional[str]  # relative filename for the awareness page
    output_path: Optional[str]
    landing_page_path: Optional[str]      # absolute path the landing page was saved to
    awareness_page_path: Optional[str]    # absolute path the awareness page was saved to
    # reducer: each node appends, never overwrites
    errors: Annotated[list[str], operator.add]
