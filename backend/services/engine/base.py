"""Base class for Groq-powered engine services."""
from __future__ import annotations

from typing import Optional

from core.config import get_settings
from core.utils.key_balancer import get_rotator

# Try the preferred import path first; fall back to the top-level package.
try:
    from groq.client import Groq as GroqClient
except Exception:
    try:
        from groq import Groq as GroqClient
    except Exception:
        GroqClient = None


class GroqEngineBase:
    """Base class for Groq-powered engine services.
    
    Provides common functionality:
    - Groq client initialization (with optional custom API key)
    - Base64 image cleaning
    - Image block building for vision API
    
    Args:
        model: Groq model name (default: meta-llama/llama-4-scout-17b-16e-instruct)
        api_key: Optional custom API key. If not provided, will use keys from GROQ_API_KEYS via the KeyBalancer.
    """
    
    DEFAULT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
    MAX_IMAGES_PER_REQUEST = 5
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.client = None
        self._api_key = api_key
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize Groq client using GroqKeyRotator for cross-process key selection."""
        if GroqClient is None:
            return

        key = self._api_key
        if not key:
            rotator = get_rotator()
            try:
                import asyncio
                key = asyncio.get_event_loop().run_until_complete(rotator.get_key())
            except Exception:
                # Fallback: first key from settings
                settings = get_settings()
                key = None
                if getattr(settings, "GROQ_API_KEYS", None):
                    try:
                        key = settings.GROQ_API_KEYS.split(",")[0].strip()
                    except Exception:
                        key = None

        if key:
            try:
                self.client = GroqClient(api_key=key)
            except Exception as e:
                print(f"{self.__class__.__name__}: failed to create Groq client: {e}")
        else:
            print(f"Warning: GROQ_API_KEYS not set; {self.__class__.__name__} will not be available.")
    
    @staticmethod
    def clean_b64(image: str) -> str:
        """Strip data URI prefix if present, return raw base64."""
        if "," in image:
            return image.split(",", 1)[1]
        return image
    
    def build_image_block(self, b64: str) -> dict:
        """Build an image_url block for Groq chat completions."""
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{self.clean_b64(b64)}"}
        }
