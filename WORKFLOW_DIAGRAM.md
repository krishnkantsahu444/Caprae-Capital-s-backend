# CAPTCHA Detection & Rate Limiting - Complete Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Google Maps Scraping Workflow                           │
│                     (with CAPTCHA Detection & Rate Limiting)                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. CELERY TASK INITIATED                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    │  scrape_leads_from_google_maps_crawlee.delay(
    │      query="restaurant",
    │      location="Miami, FL",
    │      options={"max_results": 50}
    │  )
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. INITIALIZE CRAWLER                                                        │
│    • Load proxies from proxies.txt                                          │
│    • Load user agents from user_agents.txt                                  │
│    • Initialize RateLimiter(min=2s, max=5s)                                 │
│    • Initialize stats = {attempted: 0, successful: 0, captcha: 0, ...}     │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. NAVIGATE TO SEARCH RESULTS PAGE                                          │
│    • Rotate proxy (if available)                                            │
│    • Rotate user agent                                                      │
│    • Build search URL: google.com/maps/search/restaurant+Miami+FL          │
│    • Launch Playwright browser (headless)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. CHECK FOR CAPTCHA (SEARCH PAGE)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ├─YES─► ┌──────────────────────────────────────────────┐
    │       │ • Log: 🚫 CAPTCHA detected on search page    │
    │       │ • stats["captcha_encounters"]++              │
    │       │ • Raise CaptchaDetectedError                 │
    │       │ • Close browser                              │
    │       └──────────────────────────────────────────────┘
    │           │
    │           ▼
    │       ┌──────────────────────────────────────────────┐
    │       │ CELERY RETRY WITH EXPONENTIAL BACKOFF        │
    │       │ • Attempt 1: Immediate                       │
    │       │ • Attempt 2: 5s delay + new proxy           │
    │       │ • Attempt 3: 10s delay + new proxy          │
    │       │ • Attempt 4: 20s delay + new proxy          │
    │       └──────────────────────────────────────────────┘
    │           │
    │           └──► BACK TO STEP 3 (with new proxy)
    │
    NO
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. SCROLL & PARSE SEARCH RESULTS                                            │
│    • Scroll results panel (up to 8 times)                                  │
│    • Parse business cards with parse_card_html()                           │
│    • Extract: name, category, address, rating, reviews, google_maps_url   │
│    • Log: 📋 Found 25 businesses on page                                   │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. PROCESS EACH BUSINESS                                                    │
│    FOR EACH business IN parsed_businesses:                                  │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. CHECK IF BUSINESS EXISTS                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ├─EXISTS─► ┌───────────────────────────────────────────┐
    │          │ • Log: ⏭️  Skipping duplicate            │
    │          │ • SKIP TO NEXT BUSINESS                   │
    │          └───────────────────────────────────────────┘
    │
    NEW
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 8. CHECK IF COMPLETE FROM SEARCH RESULTS                                    │
│    is_record_complete(business) checks:                                     │
│    • Has phone number?                                                      │
│    • Has website?                                                           │
│    • Has rating >= 4.0?                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ├─COMPLETE─► ┌──────────────────────────────────────────┐
    │            │ • Log: ✨ Already complete                │
    │            │ • SKIP DETAIL PAGE VISIT                  │
    │            │ • SAVE TO MONGODB                         │
    │            │ • GO TO STEP 18                           │
    │            └──────────────────────────────────────────┘
    │
    INCOMPLETE (need phone/website)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 9. APPLY RATE LIMITING BEFORE DETAIL PAGE                                   │
│    await rate_limiter.wait()                                                │
│    • Random delay: 2000-5000ms (configurable)                              │
│    • Log: 🕒 Rate limited before visiting detail page                      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 10. DETAIL PAGE ENRICHMENT - ATTEMPT 1 of 3                                │
│     stats["total_attempted"]++                                              │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 11. OPEN DETAIL PAGE IN NEW TAB                                             │
│     • Create new page (isolation from main page)                           │
│     • Rotate user agent                                                    │
│     • Navigate to google_maps_url                                          │
│     • Timeout: 20 seconds                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 12. CHECK FOR CAPTCHA (DETAIL PAGE)                                         │
│     is_captcha_present(page):                                               │
│     • Check for: iframe[src*='recaptcha']                                  │
│     • Check for: form[action*='CaptchaRedirect']                           │
│     • Check for text: "unusual traffic", "verify you're not a robot"      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ├─YES─► ┌──────────────────────────────────────────────┐
    │       │ • Log: 🚫 CAPTCHA detected on attempt 1      │
    │       │ • stats["captcha_encounters"]++              │
    │       │ • Close detail page                          │
    │       │ • Raise CaptchaDetectedError                 │
    │       └──────────────────────────────────────────────┘
    │           │
    │           ▼
    │       ┌──────────────────────────────────────────────┐
    │       │ RETRY WITH EXPONENTIAL BACKOFF               │
    │       │ • Rotate proxy (next_proxy())                │
    │       │ • Rotate user agent (next_user_agent())      │
    │       │ • Wait 2000ms (attempt 1)                    │
    │       │ • Wait 4000ms (attempt 2)                    │
    │       │ • Wait 6000ms (attempt 3)                    │
    │       └──────────────────────────────────────────────┘
    │           │
    │           └─► IF attempt < 3: GO TO STEP 10 (next attempt)
    │               IF attempt >= 3: GO TO STEP 17 (failure)
    │
    NO (No CAPTCHA detected)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 13. WAIT FOR DETAIL PAGE CONTENT                                            │
│     • Try multiple selectors (5 fallbacks)                                 │
│     • Wait up to 5 seconds per selector                                    │
│     • Wait additional 1-2 seconds for dynamic content                      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 14. EXTRACT DETAIL PAGE DATA                                                │
│     html = await page.content()                                             │
│     detail_data = parse_detail_page_html(html)                             │
│     • Extract: phone, website, hours, services                             │
│     • Normalize phone numbers (remove non-digits, validate length)         │
│     • Log: ✅ Successfully enriched: Business Name | Phone: +1234567890    │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 15. MERGE DATA & ATOMIC SAVE                                                │
│     business.update(detail_data)                                            │
│     save_business(business)  # Atomic upsert to MongoDB                    │
│     stats["detail_successes"]++                                             │
│     stats["total_successful"]++                                             │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 16. CLOSE DETAIL PAGE & RETURN SUCCESS                                      │
│     await detail_page.close()                                               │
│     return True                                                              │
│     GO TO STEP 18                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    │  ┌──────────────────────────────────────────────────────────────────────┐
    │  │ IF TIMEOUT OR ERROR IN STEPS 11-15:                                  │
    │  │ • Log: ⏱️  Timeout on attempt 1 or ⚠️  Error on attempt 1          │
    │  │ • Close detail page (in finally block)                              │
    │  │ • IF attempt < 3:                                                   │
    │  │   - Rotate proxy                                                    │
    │  │   - Wait 2s/4s/6s (exponential backoff)                             │
    │  │   - GO TO STEP 10 (retry)                                           │
    │  │ • IF attempt >= 3:                                                  │
    │  │   - GO TO STEP 17 (failure)                                         │
    │  └──────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 17. DETAIL PAGE ENRICHMENT FAILED (after 3 attempts)                        │
│     • Log: ❌ Failed to enrich after 3 attempts                            │
│     • stats["detail_failures"]++                                            │
│     • Save partial data to MongoDB (has basic info from search results)    │
│     • Continue to next business                                            │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 18. SAVE TO DATABASE                                                         │
│     save_business(business)  # Upsert via google_maps_url                  │
│     results_count++                                                          │
│     completeness = "✅ Complete" if is_record_complete else "⚠️  Partial" │
│     Log: 💾 Saved (15/50): Business Name | ✅ Complete                     │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 19. APPLY RATE LIMITING BETWEEN BUSINESSES                                  │
│     await rate_limiter.wait()                                                │
│     • Random delay: 2000-5000ms                                             │
│     • Log: ⏱️  Rate limited after processing Business Name                │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    │  ┌──────────────────────────────────────────────────────────────────────┐
    │  │ IF results_count >= max_results (50):                                │
    │  │ • Log: 🎯 Reached max results limit: 50                             │
    │  │ • STOP PROCESSING                                                   │
    │  │ • GO TO STEP 20                                                     │
    │  └──────────────────────────────────────────────────────────────────────┘
    │
    │  ELSE: GO TO STEP 6 (next business)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 20. ALL BUSINESSES PROCESSED                                                │
│     • Close browser                                                         │
│     • Return enhanced statistics                                           │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 21. CELERY TASK RETURNS RESULT                                              │
│     {                                                                       │
│         "status": "completed",                                              │
│         "stats": {                                                          │
│             "results_count": 50,                                            │
│             "query": "restaurant",                                          │
│             "location": "Miami, FL",                                        │
│             "total_attempted": 50,                                          │
│             "total_successful": 42,                                         │
│             "captcha_encounters": 3,                                        │
│             "detail_failures": 8,                                           │
│             "detail_successes": 42                                          │
│         },                                                                  │
│         "message": "Scraped 50 businesses. CAPTCHA encounters: 3..."       │
│     }                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 22. DONE! ✅                                                                │
│     Success Rate: 42/50 = 84%                                               │
│     CAPTCHA Rate: 3/50 = 6%                                                 │
│     Completeness: 42 complete, 8 partial                                    │
└─────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                              KEY FEATURES SUMMARY
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🚫 CAPTCHA DETECTION (3 methods)                                            │
│ ────────────────────────────────────────────────────────────────────────── │
│ 1. reCAPTCHA iframe: iframe[src*='recaptcha']                              │
│ 2. CAPTCHA form: form[action*='CaptchaRedirect']                           │
│ 3. Text indicators: "unusual traffic", "verify you're not a robot", etc.   │
│                                                                             │
│ Action: Raise CaptchaDetectedError → Celery retries with exponential delay │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ⏱️  RATE LIMITING (2 locations)                                             │
│ ────────────────────────────────────────────────────────────────────────── │
│ 1. Before detail page visit: await rate_limiter.wait()                     │
│    • Delay: 2000-5000ms (configurable via MIN_DELAY_MS/MAX_DELAY_MS)      │
│                                                                             │
│ 2. Between businesses: await rate_limiter.wait()                           │
│    • Delay: 2000-5000ms                                                    │
│                                                                             │
│ Purpose: Prevent IP bans, mimic human behavior                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔄 RETRY LOGIC (3 attempts with exponential backoff)                        │
│ ────────────────────────────────────────────────────────────────────────── │
│ Attempt 1: Immediate (no backoff)                                          │
│ Attempt 2: 2000ms backoff + proxy rotation + UA rotation                   │
│ Attempt 3: 4000ms backoff + proxy rotation + UA rotation                   │
│                                                                             │
│ On failure: stats["detail_failures"]++, save partial data                  │
│ On success: stats["detail_successes"]++, save complete data                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 STATISTICS TRACKING (5 metrics)                                          │
│ ────────────────────────────────────────────────────────────────────────── │
│ • total_attempted: Total detail pages attempted                            │
│ • total_successful: Successful enrichments                                 │
│ • captcha_encounters: CAPTCHAs detected                                    │
│ • detail_failures: Failed after 3 attempts                                 │
│ • detail_successes: Successful detail page enrichments                     │
│                                                                             │
│ Returned in task result for analysis and monitoring                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 💾 ATOMIC SAVES (MongoDB upsert)                                            │
│ ────────────────────────────────────────────────────────────────────────── │
│ • After detail page enrichment: save_business(business)                    │
│ • After processing each business: save_business(business)                  │
│                                                                             │
│ Method: update_one({"google_maps_url": url}, {"$set": data}, upsert=True) │
│ Benefit: No data loss, prevents race conditions                            │
└─────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                          ERROR HANDLING STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

Error Type                 | Action                          | Retry
──────────────────────────────────────────────────────────────────────────────
CaptchaDetectedError       | Close page, rotate proxy       | YES (5s→10s→20s)
PlaywrightTimeout          | Close page, exponential backoff| YES (2s→4s→6s)
Generic Exception          | Close page, exponential backoff| YES (2s→4s→6s)
Max retries exceeded       | Log failure, save partial data | NO
──────────────────────────────────────────────────────────────────────────────

