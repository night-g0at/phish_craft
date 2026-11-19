from langgraph.graph import StateGraph, END
from phishing.state import PhishingState
from phishing.nodes.scenario import generate_scenario
from phishing.nodes.org_data import extract_org_data
from phishing.nodes.brand_fetch import fetch_brand_data
from phishing.nodes.logo_analysis import analyze_logos
from phishing.nodes.landing_page import build_landing_page
from phishing.nodes.email_builder import build_email
from phishing.nodes.output import save_output


def build_graph():
    g = StateGraph(PhishingState)

    g.add_node("generate_scenario", generate_scenario)
    g.add_node("extract_org_data",  extract_org_data)
    g.add_node("fetch_brand_data",  fetch_brand_data)
    g.add_node("analyze_logos",      analyze_logos)
    g.add_node("build_landing_page", build_landing_page)
    g.add_node("build_email",        build_email)
    g.add_node("save_output",        save_output)

    g.set_entry_point("generate_scenario")
    g.add_edge("generate_scenario",  "extract_org_data")
    g.add_edge("extract_org_data",   "fetch_brand_data")
    g.add_edge("fetch_brand_data",   "analyze_logos")
    # Landing page runs before the email so the email CTA can link to its file.
    g.add_edge("analyze_logos",      "build_landing_page")
    g.add_edge("build_landing_page", "build_email")
    g.add_edge("build_email",        "save_output")
    g.add_edge("save_output",        END)

    return g.compile()
