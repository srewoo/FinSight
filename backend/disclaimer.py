"""
SEBI Disclaimer System.
Manages disclaimer text, versioning, and response field generation.
"""

CURRENT_DISCLAIMER_VERSION = "1.0"

SEBI_DISCLAIMER_TEXT = (
    "IMPORTANT DISCLAIMER: FinSight is NOT a SEBI-registered Investment Adviser "
    "under the SEBI (Investment Advisers) Regulations, 2013. The information, "
    "analysis, and recommendations provided by this application are generated "
    "by artificial intelligence for educational and informational purposes only. "
    "They do NOT constitute investment advice, financial advice, trading advice, "
    "or any other form of professional advice. Past performance of any stock, "
    "index, or AI prediction does not guarantee future results. Stock market "
    "investments are subject to market risks. Read all scheme-related documents "
    "carefully before investing. You should consult a SEBI-registered investment "
    "adviser before making any investment decisions. By using AI-powered features "
    "of this app, you acknowledge and accept that you are solely responsible for "
    "your investment decisions and any gains or losses resulting from them."
)

SEBI_DISCLAIMER_SHORT = (
    "Not SEBI-registered. AI analysis is for informational purposes only. "
    "Past performance does not guarantee future results. Invest at your own risk."
)


def build_disclaimer_response_field() -> dict:
    """Returns the disclaimer dict to include in AI analysis responses."""
    return {
        "version": CURRENT_DISCLAIMER_VERSION,
        "text": SEBI_DISCLAIMER_SHORT,
        "full_text_available": True,
    }
