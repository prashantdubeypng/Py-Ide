"""
AI Manager Service
Provider abstraction, async calls, caching, rate limiting, request queue
"""
import asyncio
import json
import time
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import threading
from queue import Queue, Empty

from ide.utils.secret_manager import SecretManager
from ide.utils.logger import logger


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.model = kwargs.get("model", "gpt-3.5-turbo")
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens", 10000)
    
    @abstractmethod
    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate AI response asynchronously"""
        pass
    
    @abstractmethod
    def validate_key(self) -> bool:
        """Validate API key"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider using official SDK"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.model = kwargs.get("model", "gpt-4")
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI SDK not installed. Install with: pip install openai")
        return self._client
    
    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate response using OpenAI SDK"""
        try:
            client = self._get_client()
            
            # Check if Responses API is available (for newer models)
            try:
                # Try Responses API format first
                input_messages = []
                
                if context:
                    input_messages.append({
                        "role": "developer",
                        "content": context
                    })
                
                input_messages.append({
                    "role": "user",
                    "content": prompt
                })
                
                kwargs = {
                    "model": self.model,
                    "input": input_messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
                
                # Add reasoning for reasoning models
                if self.model.startswith(("o3", "gpt-5")):
                    kwargs["reasoning"] = {"effort": "medium"}
                
                response = client.responses.create(**kwargs)
                
                # Extract output text
                if hasattr(response, 'output_text'):
                    return response.output_text.strip()
                
                # Fallback to parsing output array
                text_parts = []
                for item in response.output:
                    if item.type == "message":
                        for content_item in item.content:
                            if content_item.type == "output_text":
                                text_parts.append(content_item.text)
                
                return " ".join(text_parts).strip()
                
            except (AttributeError, Exception) as e:
                # Fallback to Chat Completions API
                logger.info(f"Using Chat Completions API (Responses API unavailable): {e}")
                return await self._chat_completions(prompt, context)
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _chat_completions(self, prompt: str, context: Optional[str] = None) -> str:
        """Use Chat Completions API"""
        try:
            client = self._get_client()
            
            messages = []
            if context:
                messages.append({
                    "role": "system",
                    "content": context
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Chat Completions error: {e}")
            raise
    
    def validate_key(self) -> bool:
        """Validate OpenAI API key format"""
        return bool(self.api_key and self.api_key.startswith("sk-"))


class GeminiProvider(AIProvider):
    """Google Gemini API provider"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = kwargs.get("model", "gemini-2.0-flash-exp")

    
    async def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate response using Gemini API with retry logic"""
        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                import httpx
                
                full_prompt = f"{context}\n\n{prompt}" if context else prompt
                
                payload = {
                    "contents": [{
                        "parts": [{"text": full_prompt}]
                    }],
                    "generationConfig": {
                        "temperature": self.temperature,
                        "maxOutputTokens": self.max_tokens
                    }
                }
                
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(
                        f"{self.base_url}/{self.model}:generateContent?key={self.api_key}",
                        json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            except ImportError:
                logger.warning("httpx not installed, using sync fallback for Gemini")
                return await self._sync_fallback(prompt, context)
            
            except Exception as e:
                error_str = str(e)
                
                # Handle rate limiting (429)
                if "429" in error_str or "Too Many Requests" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error("Rate limit exceeded after all retries")
                        raise Exception("❌ Rate limit exceeded. Please wait a moment and try again.")
                
                # Other errors
                logger.error(f"Gemini API error: {e}")
                raise
    
    async def _sync_fallback(self, prompt: str, context: Optional[str] = None) -> str:
        """Fallback using requests library with retry logic"""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                import requests
                
                full_prompt = f"{context}\n\n{prompt}" if context else prompt
                
                response = requests.post(
                    f"{self.base_url}/{self.model}:generateContent?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {
                            "temperature": self.temperature,
                            "maxOutputTokens": self.max_tokens
                        }
                    },
                    timeout=60
                )
                response.raise_for_status()
                return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                
            except ImportError:
                return "⚠️ httpx and requests not installed. Install with: pip install httpx requests"
            
            except Exception as e:
                error_str = str(e)
                
                # Handle rate limiting
                if "429" in error_str or "Too Many Requests" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt)
                        logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception("❌ Rate limit exceeded. Please wait a moment and try again.")
                
                logger.error(f"Gemini fallback error: {e}")
                raise
    
    def validate_key(self) -> bool:
        """Validate Gemini API key format"""
        return bool(self.api_key and len(self.api_key) > 20)


class RequestCache:
    """Simple cache with TTL support"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
    
    def _make_key(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate cache key"""
        return f"{context or ''}::{prompt}"
    
    def get(self, prompt: str, context: Optional[str] = None) -> Optional[str]:
        """Retrieve cached response if valid"""
        key = self._make_key(prompt, context)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires"]:
                return entry["response"]
            else:
                del self.cache[key]
        return None
    
    def set(self, prompt: str, response: str, context: Optional[str] = None) -> None:
        """Cache response with TTL"""
        key = self._make_key(prompt, context)
        self.cache[key] = {
            "response": response,
            "expires": datetime.now() + timedelta(seconds=self.ttl),
            "timestamp": datetime.now().isoformat()
        }
    
    def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries, return count"""
        now = datetime.now()
        expired = [k for k, v in self.cache.items() if now >= v["expires"]]
        for k in expired:
            del self.cache[k]
        return len(expired)


class RateLimiter:
    """Rate limiter with token bucket algorithm"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = threading.Lock()
    
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Remove old requests outside window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    def wait_if_needed(self) -> float:
        """Wait until next request is allowed, return wait time"""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return 0.0
            
            # Calculate wait time
            wait_until = self.requests[0] + self.window_seconds
            wait_time = wait_until - now
            return max(0, wait_time)


class AIManager:
    """Central AI management service with async support"""
    
    def __init__(self, settings_manager=None, cache_ttl: int = 3600):
        self.settings = settings_manager
        self.secret_manager = SecretManager()
        
        self.provider: Optional[AIProvider] = None
        self.cache = RequestCache(ttl_seconds=cache_ttl)
        # More conservative rate limiting: 5 requests per minute
        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        self.request_queue: Queue = Queue()
        self.request_thread = None
        self.running = False
        
        # Stats
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "rate_limited_requests": 0,
            "errors": 0
        }
        
        logger.info("AI Manager initialized")
    
    def initialize_provider(self, provider_name: str = None) -> bool:
        """Initialize AI provider from settings"""
        if not self.settings:
            logger.warning("No settings manager provided")
            return False
        
        ai_settings = self.settings.get("ai", {})
        provider_name = provider_name or ai_settings.get("provider", "openai")
        
        try:
            api_key = self.secret_manager.get_secret(provider_name)
            
            logger.debug(f"Attempting to initialize provider: {provider_name}")
            logger.debug(f"API key found: {bool(api_key)}, Length: {len(api_key) if api_key else 0}")
            
            if not api_key:
                logger.warning(f"No API key found for provider: {provider_name}")
                logger.info(f"Please configure API key in Settings. Provider: {provider_name}")
                return False
                return False
            
            if provider_name.lower() == "openai":
                self.provider = OpenAIProvider(
                    api_key,
                    model=ai_settings.get("openai_model", "gpt-3.5-turbo"),
                    temperature=ai_settings.get("temperature", 0.7),
                    max_tokens=ai_settings.get("max_tokens", 10000)
                )
            elif provider_name.lower() == "gemini":
                self.provider = GeminiProvider(
                    api_key,
                    model=ai_settings.get("gemini_model", "gemini-2.0-flash-exp"),
                    temperature=ai_settings.get("temperature", 0.7),
                    max_tokens=ai_settings.get("max_tokens", 10000)
                )
            else:
                logger.error(f"Unknown provider: {provider_name}")
                return False
            
            if not self.provider.validate_key():
                logger.error(f"Invalid API key for provider: {provider_name}")
                return False
            
            logger.info(f"AI Provider initialized: {provider_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize AI provider: {e}")
            return False
    
    def is_provider_initialized(self) -> bool:
        """Check if AI provider is initialized and ready"""
        return self.provider is not None
    
    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        use_cache: bool = True,
        timeout: int = 30
    ) -> str:
        """Generate AI response with caching and rate limiting"""
        self.stats["total_requests"] += 1
        
        if not self.provider:
            error_msg = "AI Provider not initialized. Please configure API key in settings."
            logger.error(error_msg)
            return f"❌ {error_msg}"
        
        # Check cache
        if use_cache:
            cached = self.cache.get(prompt, context)
            if cached:
                self.stats["cache_hits"] += 1
                logger.debug("Cache hit")
                return cached
            self.stats["cache_misses"] += 1
        
        # Check rate limit
        wait_time = self.rate_limiter.wait_if_needed()
        if wait_time > 0:
            self.stats["rate_limited_requests"] += 1
            logger.warning(f"Rate limited, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        try:
            self.stats["api_calls"] += 1
            response = await asyncio.wait_for(
                self.provider.generate(prompt, context),
                timeout=timeout
            )
            
            # Cache successful response
            if use_cache:
                self.cache.set(prompt, response, context)
            
            logger.info(f"AI response generated ({len(response)} chars)")
            return response
        
        except asyncio.TimeoutError:
            self.stats["errors"] += 1
            error_msg = "⏱️ AI request timed out. Try again or check your connection."
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            self.stats["errors"] += 1
            error_msg = f"❌ AI error: {str(e)[:100]}"
            logger.error(f"AI generation error: {e}")
            return error_msg
    
    def generate_sync(
        self,
        prompt: str,
        context: Optional[str] = None,
        use_cache: bool = True
    ) -> str:
        """Synchronous wrapper for async generate (for PyQt integration)"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.generate(prompt, context, use_cache)
            )
            return result
        except Exception as e:
            logger.error(f"Sync generate error: {e}")
            return f"❌ Error: {str(e)[:100]}"
        finally:
            loop.close()
    
    def get_code_explanation(self, code_snippet: str, context: str = "") -> str:
        """Get AI explanation for code"""
        prompt = f"Explain this Python code concisely (2-3 sentences):\n\n```python\n{code_snippet}\n```"
        return self.generate_sync(prompt, context)
    
    def get_optimization_suggestions(self, code_snippet: str) -> str:
        """Get optimization suggestions for code"""
        prompt = f"""Analyze this Python code and provide optimization suggestions:

```python
{code_snippet}
```

Provide 2-3 specific suggestions. For EACH suggestion, format as:

**Suggestion [N]: [Brief Title]**
Issue: [One sentence explaining the problem]
Solution: [One sentence explaining the fix]

**Corrected Code:**
```python
[Show the COMPLETE corrected code with this fix applied]
```

---

Be concise and show complete working code for each suggestion."""
        return self.generate_sync(prompt)
    
    def get_refactoring_advice(self, code_snippet: str, issue: str = "") -> str:
        """Get refactoring advice"""
        prompt = f"Provide refactoring advice for this Python code:\n\n```python\n{code_snippet}\n```"
        if issue:
            prompt += f"\n\nContext/Issue: {issue}"
        prompt += "\n\nProvide specific, actionable refactoring suggestions."
        return self.generate_sync(prompt)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        cache_cleanup = self.cache.cleanup_expired()
        return {
            **self.stats,
            "cache_size": len(self.cache.cache),
            "cache_expired_cleanup": cache_cleanup,
            "provider": self.provider.__class__.__name__ if self.provider else "None",
            "timestamp": datetime.now().isoformat()
        }
    
    def clear_cache(self) -> None:
        """Clear request cache"""
        self.cache.clear()
        logger.info("AI cache cleared")
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "rate_limited_requests": 0,
            "errors": 0
        }
        logger.info("AI stats reset")
