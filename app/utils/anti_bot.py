"""Anti-bot utilities including proxy rotation, user agent rotation, and delay helpers."""
import random
from pathlib import Path
from typing import List, Optional


def load_lines(path: str) -> List[str]:
    """Load non-empty lines from a text file."""
    try:
        p = Path(path)
        if not p.exists():
            return []
        return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    except Exception:
        return []


class Rotation:
    """Handles round-robin rotation of proxies and user agents."""

    def __init__(self, proxies: Optional[List[str]] = None, user_agents: Optional[List[str]] = None):
        self.proxies = proxies or []
        self.user_agents = user_agents or []
        self.proxy_index = -1
        self.ua_index = -1

    def next_proxy(self) -> Optional[str]:
        """Get the next proxy in rotation (round-robin)."""
        if not self.proxies:
            return None
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.proxies[self.proxy_index]

    def next_user_agent(self) -> Optional[str]:
        """Get the next user agent in rotation (round-robin)."""
        if not self.user_agents:
            return None
        self.ua_index = (self.ua_index + 1) % len(self.user_agents)
        return self.user_agents[self.ua_index]

    def random_delay_ms(self, min_ms: int = 1000, max_ms: int = 3500) -> int:
        """Generate a random delay in milliseconds."""
        return random.randint(min_ms, max_ms)

    def random_user_agent(self) -> Optional[str]:
        """Get a random user agent (not round-robin)."""
        if not self.user_agents:
            return None
        return random.choice(self.user_agents)


# Default user agents for fallback
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]
