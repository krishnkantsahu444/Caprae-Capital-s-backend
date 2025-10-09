from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List, Optional

import httpx


class ApolloScraper:
    """Scrape company and contact records from Apollo.

    The scraper supports both the Apollo HTTP API (when an API key is supplied)
    and a lightweight mock mode that returns deterministic sample data. The mock
    mode is useful for local development or integration tests where the Apollo
    credentials are not configured yet.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        saved_list_url: Optional[str] = None,
        base_url: str = "https://api.apollo.io/v1",
        client: Optional[httpx.Client] = None,
        request_timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.email = email
        self.password = password
        self.saved_list_url = saved_list_url
        self.base_url = base_url.rstrip("/")
        self._authenticated = False
        self._client_provided = client is not None
        self._client = client or httpx.Client(timeout=request_timeout)
        self._mock_mode = api_key is None

    def __enter__(self) -> "ApolloScraper":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def authenticate(self) -> None:
        """Authenticate against Apollo if credentials are available.

        When an API key is supplied the scraper adds it as an authorization
        header. Username/password authentication can be added later if needed.
        """

        headers = {"User-Agent": "LeadGenBackend/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self._client.headers.update(headers)
        self._authenticated = True

    def search_companies(self, query: str, limit: int = 25) -> List[Dict[str, Optional[str]]]:
        """Retrieve companies that match the provided query."""

        if self._mock_mode:
            return self._mock_companies(query, limit)

        self._ensure_authenticated()
        payload = {"q_keywords": query, "page": 1, "per_page": limit}
        response = self._client.post(f"{self.base_url}/companies/search", json=payload)
        response.raise_for_status()

        companies: List[Dict[str, Optional[str]]] = []
        for entry in response.json().get("companies", []):
            companies.append(
                {
                    "business_name": entry.get("name"),
                    "website": entry.get("website_url"),
                    "industry": entry.get("industry"),
                    "country": entry.get("country"),
                    "company_linkedin_url": entry.get("linkedin_url"),
                }
            )
        return companies

    def search_contacts(self, query: str, limit: int = 25) -> List[Dict[str, Optional[str]]]:
        """Retrieve contacts that match the provided query."""

        if self._mock_mode:
            return self._mock_contacts(query, limit)

        self._ensure_authenticated()
        payload = {"q_keywords": query, "page": 1, "per_page": limit}
        response = self._client.post(f"{self.base_url}/contacts/search", json=payload)
        response.raise_for_status()

        contacts: List[Dict[str, Optional[str]]] = []
        for entry in response.json().get("contacts", []):
            contact_company = entry.get("organization", {})
            contacts.append(
                {
                    "business_name": contact_company.get("name"),
                    "website": contact_company.get("website_url"),
                    "industry": contact_company.get("industry"),
                    "country": contact_company.get("country"),
                    "first_name": entry.get("first_name"),
                    "last_name": entry.get("last_name"),
                    "job_title": entry.get("title"),
                    "phone": entry.get("phone"),
                    "linkedin_url": entry.get("linkedin_url"),
                    "email": entry.get("email"),
                }
            )
        return contacts

    def scrape(self, query: str, limit: int = 25) -> List[Dict[str, Optional[str]]]:
        """Run the full scraping flow for a query."""

        companies = self.search_companies(query, limit=limit)
        contacts = self.search_contacts(query, limit=limit)

        if not contacts:
            leads = [self._normalize_company(company) for company in companies]
        else:
            leads = []
            matched_domains = set()
            for company, contact in self._match_records(companies, contacts):
                domain = self._extract_domain((company or {}).get("website")) or self._extract_domain(contact.get("website"))
                if domain:
                    matched_domains.add(domain)
                leads.append(self._combine_records(company, contact))

            for company in companies:
                domain = self._extract_domain(company.get("website"))
                if domain and domain in matched_domains:
                    continue
                leads.append(self._normalize_company(company))

        return self._deduplicate(leads)

    def close(self) -> None:
        """Dispose of the underlying HTTP client if owned by the scraper."""
        if not self._client_provided:
            self._client.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_authenticated(self) -> None:
        if not self._authenticated:
            self.authenticate()

    @staticmethod
    def _normalize_company(company: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        return {
            "business_name": company.get("business_name"),
            "website": company.get("website"),
            "industry": company.get("industry"),
            "country": company.get("country"),
            "first_name": None,
            "last_name": None,
            "job_title": None,
            "phone": None,
            "linkedin_url": company.get("company_linkedin_url"),
            "email": None,
        }

    def _combine_records(
        self,
        company: Optional[Dict[str, Optional[str]]],
        contact: Dict[str, Optional[str]],
    ) -> Dict[str, Optional[str]]:
        """Merge company and contact information into a single lead dictionary."""

        combined: Dict[str, Optional[str]] = {
            "business_name": None,
            "website": None,
            "industry": None,
            "country": None,
            "first_name": contact.get("first_name"),
            "last_name": contact.get("last_name"),
            "job_title": contact.get("job_title"),
            "phone": contact.get("phone"),
            "linkedin_url": contact.get("linkedin_url"),
            "email": contact.get("email"),
        }

        if company:
            combined.update(
                {
                    "business_name": company.get("business_name") or combined["business_name"],
                    "website": company.get("website") or combined["website"],
                    "industry": company.get("industry") or combined["industry"],
                    "country": company.get("country") or combined["country"],
                }
            )
        else:
            combined.update(
                {
                    "business_name": contact.get("business_name"),
                    "website": contact.get("website"),
                    "industry": contact.get("industry"),
                    "country": contact.get("country"),
                }
            )
        return combined

    def _match_records(
        self,
        companies: Iterable[Dict[str, Optional[str]]],
        contacts: Iterable[Dict[str, Optional[str]]],
    ) -> Iterable[tuple[Optional[Dict[str, Optional[str]]], Dict[str, Optional[str]]]]:
        """Pair contacts with their corresponding companies using domain matching."""

        company_by_domain = {
            self._extract_domain(company.get("website")): company for company in companies if company.get("website")
        }

        for contact in contacts:
            domain = self._extract_domain(contact.get("website"))
            yield company_by_domain.get(domain), contact

    @staticmethod
    def _extract_domain(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        cleaned = url.lower().split("//")[-1]
        return cleaned.split("/")[0]

    def _deduplicate(self, leads: Iterable[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
        """Remove duplicate leads based on email or a tuple of key attributes."""

        seen: set[Any] = set()
        unique: List[Dict[str, Optional[str]]] = []
        for lead in leads:
            key = lead.get("email") or (
                lead.get("business_name"),
                lead.get("first_name"),
                lead.get("last_name"),
                lead.get("job_title"),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(lead)
        return unique

    # ------------------------------------------------------------------
    # Mock helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _mock_companies(query: str, limit: int) -> List[Dict[str, Optional[str]]]:
        seed = random.Random(hash(query) & 0xFFFFFFFF)
        companies = []
        for idx in range(min(limit, 5)):
            slug = f"{query.replace(' ', '-').lower()}-{idx}"
            companies.append(
                {
                    "business_name": f"{query.title()} Solutions {idx + 1}",
                    "website": f"https://{slug}.com",
                    "industry": seed.choice(["Software", "Marketing", "Consulting", "Finance"]),
                    "country": seed.choice(["United States", "Canada", "United Kingdom", "Australia"]),
                    "company_linkedin_url": f"https://www.linkedin.com/company/{slug}",
                }
            )
        return companies

    @staticmethod
    def _mock_contacts(query: str, limit: int) -> List[Dict[str, Optional[str]]]:
        seed = random.Random((hash(query) >> 1) & 0xFFFFFFFF)
        contacts = []
        first_names = ["Avery", "Jordan", "Taylor", "Riley", "Morgan"]
        last_names = ["Smith", "Johnson", "Lee", "Patel", "Garcia"]
        roles = ["Founder", "Head of Growth", "CTO", "Marketing Director", "Operations Manager"]

        for idx in range(min(limit, 5)):
            domain = f"{query.replace(' ', '').lower()}-{idx}.com"
            first_name = seed.choice(first_names)
            last_name = seed.choice(last_names)
            contacts.append(
                {
                    "business_name": f"{query.title()} Solutions {idx + 1}",
                    "website": f"https://{domain}",
                    "industry": seed.choice(["Software", "Marketing", "Consulting", "Finance"]),
                    "country": seed.choice(["United States", "Canada", "United Kingdom", "Australia"]),
                    "first_name": first_name,
                    "last_name": last_name,
                    "job_title": seed.choice(roles),
                    "phone": None,
                    "linkedin_url": f"https://www.linkedin.com/in/{first_name.lower()}.{last_name.lower()}",
                    "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
                }
            )
        return contacts