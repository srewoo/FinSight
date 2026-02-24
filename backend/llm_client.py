"""
Unified async LLM client supporting OpenAI, Google Gemini, and Anthropic Claude.
No third-party wrappers — direct SDK calls only.
"""
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported providers & models
# ---------------------------------------------------------------------------
SUPPORTED_MODELS = {
    "openai": ["gpt-5-mini", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini"],
    "gemini": ["gemini-3.0", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "claude": ["claude-sonnet-4-6", "claude-opus-4-5", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
}


async def call_llm(
    provider: str,
    model: str,
    api_key: str,
    prompt: str,
    system_message: str = "You are an expert Indian stock market analyst. Respond with valid JSON only.",
    image_b64: Optional[str] = None,
) -> str:
    """
    Call the specified LLM provider and return the raw text response.

    Args:
        provider: "openai" | "gemini" | "claude"
        model:    Model name (must be in SUPPORTED_MODELS[provider])
        api_key:  API key for the provider
        prompt:   User message / instruction
        system_message: System-level instruction
        image_b64: Optional base64-encoded image (for vision-capable models)

    Returns:
        Raw string response from the model.

    Raises:
        ValueError: Unknown provider / model or missing key.
        RuntimeError: API call failure.
    """
    if not api_key:
        raise ValueError("No API key configured. Please set your API key in Settings.")

    provider = provider.lower().strip()
    if provider not in SUPPORTED_MODELS:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(SUPPORTED_MODELS)}")
    if model not in SUPPORTED_MODELS[provider]:
        raise ValueError(f"Unknown model '{model}' for provider '{provider}'. Choose from: {SUPPORTED_MODELS[provider]}")

    if provider == "openai":
        return await _call_openai(api_key, model, system_message, prompt, image_b64)
    elif provider == "gemini":
        return await _call_gemini(api_key, model, system_message, prompt, image_b64)
    elif provider == "claude":
        return await _call_claude(api_key, model, system_message, prompt, image_b64)


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
async def _call_openai(api_key: str, model: str, system_message: str, prompt: str, image_b64: Optional[str]) -> str:
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)

        messages = [{"role": "system", "content": system_message}]

        if image_b64:
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ]
        else:
            user_content = prompt

        messages.append({"role": "user", "content": user_content})

        # Modern OpenAI models (gpt-5-mini, o1, o3, etc.) only accept the
        # default temperature (1) — omit it entirely to avoid 400 errors.
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=2048,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI call failed: {e}")
        raise RuntimeError(f"OpenAI error: {e}")


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------
async def _call_gemini(api_key: str, model: str, system_message: str, prompt: str, image_b64: Optional[str]) -> str:
    try:
        import google.generativeai as genai
        import asyncio

        genai.configure(api_key=api_key)
        gmodel = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_message,
        )

        parts = []
        if image_b64:
            image_bytes = base64.b64decode(image_b64)
            parts.append({"mime_type": "image/jpeg", "data": image_bytes})
        parts.append(prompt)

        # Gemini SDK is sync; run in executor to keep FastAPI async-friendly
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: gmodel.generate_content(parts, generation_config={"temperature": 0.2, "max_output_tokens": 2048}),
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        raise RuntimeError(f"Gemini error: {e}")


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------
async def _call_claude(api_key: str, model: str, system_message: str, prompt: str, image_b64: Optional[str]) -> str:
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)

        if image_b64:
            user_content = [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64},
                },
                {"type": "text", "text": prompt},
            ]
        else:
            user_content = prompt

        response = await client.messages.create(
            model=model,
            system=system_message,
            messages=[{"role": "user", "content": user_content}],
            max_tokens=2048,
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude call failed: {e}")
        raise RuntimeError(f"Claude error: {e}")
