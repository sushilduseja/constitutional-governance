"""
AI Governance SDK.

Usage:
    from governance import Governance

    gov = Governance(
        api_key="gov_...",
        constitution_version="latest",
        async_mode=True
    )

    response = await gov.wrap(
        provider="anthropic",
        call=lambda: client.messages.create(model="claude-3-5-sonnet-20260220", ...)
    )
"""

__version__ = "0.1.0"
