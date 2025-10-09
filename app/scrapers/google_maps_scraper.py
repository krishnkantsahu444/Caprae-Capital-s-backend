from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager


class AntiBotDetectedError(RuntimeError):
    """Raised when Google blocks the current session with anti-bot measures."""


@dataclass
class ScraperResult:
    business_name: Optional[str]
    website: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    service_options: Optional[List[str]]
    address: Optional[str]
    phone: Optional[str]
    google_maps_url: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "business_name": self.business_name,
            "website": self.website,
            "rating": self.rating,
            "review_count": self.review_count,
            "service_options": self.service_options,
            "address": self.address,
            "phone": self.phone,
            "google_maps_url": self.google_maps_url,
            "industry": None,
            "country": None,
            "first_name": None,
            "last_name": None,
            "job_title": None,
            "linkedin_url": None,
            "email": None,
            "source": "google_maps",
        }


class GoogleMapsScraper:
    """Scrape business listings from Google Maps with proxy rotation support."""

    DEFAULT_USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]

    def __init__(
        self,
        proxies: Optional[Iterable[str]] = None,
        headless: bool = True,
        implicit_wait: float = 10.0,
        scroll_pause: float = 1.0,
        max_scroll_attempts: int = 12,
        user_agents: Optional[List[str]] = None,
    ) -> None:
        self.proxies = list(proxies or [])
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.scroll_pause = scroll_pause
        self.max_scroll_attempts = max_scroll_attempts
        self.user_agents = user_agents or self.DEFAULT_USER_AGENTS
        self._proxy_index = -1
        self._driver: Optional[webdriver.Chrome] = None

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------
    def __enter__(self) -> "GoogleMapsScraper":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def scrape(self, query: str, location: str, max_results: int = 25) -> List[Dict[str, object]]:
        """Scrape Google Maps for businesses matching *query* within *location*."""

        attempts = 0
        max_attempts = max(len(self.proxies), 1) * 3

        while attempts < max_attempts:
            try:
                driver = self._ensure_driver()
                url = self._build_search_url(query, location)
                driver.get(url)
                self._handle_cookie_consent(driver)
                self._scroll_results_panel(driver, max_results)
                html = driver.page_source

                if self._is_blocked(html):
                    raise AntiBotDetectedError("Google Maps blocked the session")

                results = self._parse_results(html)
                if results:
                    return [result.to_dict() for result in results[:max_results]]
            except AntiBotDetectedError:
                attempts += 1
                self._rotate_proxy(restart_driver=True)
                continue
            except WebDriverException:
                attempts += 1
                self._rotate_proxy(restart_driver=True)
                time.sleep(2)
                continue
            else:
                break

        return []

    def close(self) -> None:
        """Dispose of the Selenium driver when the scraper owns it."""

        if self._driver is not None:
            try:
                self._driver.quit()
            finally:
                self._driver = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_driver(self) -> webdriver.Chrome:
        if self._driver is None:
            self._driver = self._create_driver()
        return self._driver

    def _create_driver(self) -> webdriver.Chrome:
        seleniumwire_options = self._build_proxy_config()
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-agent={random.choice(self.user_agents)}")
        options.add_argument("--disable-blink-features=AutomationControlled")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options, seleniumwire_options=seleniumwire_options)
        driver.implicitly_wait(self.implicit_wait)
        return driver

    def _rotate_proxy(self, restart_driver: bool = False) -> None:
        if not self.proxies:
            if restart_driver:
                self.close()
            return

        self._proxy_index = (self._proxy_index + 1) % len(self.proxies)
        if restart_driver:
            self.close()

    def _current_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        if self._proxy_index == -1:
            self._proxy_index = 0
        return self.proxies[self._proxy_index]

    def _build_proxy_config(self) -> Optional[dict]:
        proxy = self._current_proxy()
        if not proxy:
            return None

        formatted_proxy = proxy if "@" in proxy else f"{proxy}"
        return {
            "proxy": {
                "http": formatted_proxy,
                "https": formatted_proxy,
                "no_proxy": "localhost,127.0.0.1",
            }
        }

    def _build_search_url(self, query: str, location: str) -> str:
        normalized_query = query.replace(" ", "+")
        normalized_location = location.replace(" ", "+")
        return f"https://www.google.com/maps/search/{normalized_query}+in+{normalized_location}/"

    def _handle_cookie_consent(self, driver: webdriver.Chrome) -> None:
        try:
            button = driver.find_element(By.XPATH, "//button[@jsname='b3VHJd']")
            button.click()
        except NoSuchElementException:
            pass

    def _scroll_results_panel(self, driver: webdriver.Chrome, max_results: int) -> None:
        panel_xpath = "//*[@id='QA0Szd']/div/div/div[1]/div[2]/div"
        presses = max(5, min(max_results // 10, self.max_scroll_attempts))
        try:
            panel = driver.find_element(By.XPATH, panel_xpath)
        except NoSuchElementException:
            return

        ActionChains(driver).move_to_element(panel).click().perform()
        for _ in range(presses):
            ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
            time.sleep(self.scroll_pause)

    def _is_blocked(self, html: str) -> bool:
        lowered = html.lower()
        return "unusual traffic" in lowered or "captcha" in lowered

    def _parse_results(self, html: str) -> List[ScraperResult]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div[role='article']")
        results: List[ScraperResult] = []

        for card in cards:
            title_element = card.find("a", class_="hfpxzc") or card.find("a", class_="qBF1Pd")
            name = title_element.get("aria-label") if title_element else None
            maps_url = f"https://www.google.com{title_element.get('href')}" if title_element and title_element.get("href") else None

            rating = self._safe_float(self._extract_text(card, "span", "MW4etd"))
            review_text = self._extract_text(card, "span", "UY7F9")
            review_count = self._parse_review_count(review_text)
            services = self._extract_services(card)
            address = self._extract_text(card, "div", "W4Efsd")
            phone = self._extract_phone(card)

            results.append(
                ScraperResult(
                    business_name=name,
                    website=None,
                    rating=rating,
                    review_count=review_count,
                    service_options=services,
                    address=address,
                    phone=phone,
                    google_maps_url=maps_url,
                )
            )
        return results

    @staticmethod
    def _extract_text(container, tag: str, class_name: str) -> Optional[str]:
        element = container.find(tag, class_=class_name)
        if element is None:
            return None
        return element.get_text(strip=True) or None

    @staticmethod
    def _extract_services(card) -> Optional[List[str]]:
        services_container = card.find("div", class_="Ahnjwc")
        if not services_container:
            return None
        raw_text = services_container.get_text(" | ", strip=True)
        if not raw_text:
            return None
        parts = [part.strip() for part in raw_text.replace("·", "|").split("|")]
        return [part for part in parts if part]

    @staticmethod
    def _extract_phone(card) -> Optional[str]:
        phone_container = card.find("div", class_="W4Efsd")
        if not phone_container:
            return None
        spans = phone_container.find_all("span")
        for span in spans:
            text = span.get_text(strip=True)
            if text and any(char.isdigit() for char in text):
                return text
        return None

    @staticmethod
    def _parse_review_count(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else None

    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
