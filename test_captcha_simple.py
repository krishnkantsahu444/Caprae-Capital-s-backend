"""Simple test to verify CAPTCHA detection without full crawler dependencies."""
import asyncio
from playwright.async_api import async_playwright

# Import the CAPTCHA detection logic from the crawler
import sys
sys.path.insert(0, 'app')

async def test_captcha_detection():
    """Test CAPTCHA detection with various HTML scenarios."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("\n🧪 Testing CAPTCHA Detection Scenarios...\n")
        
        # Test 1: Normal page (no CAPTCHA)
        await page.set_content("""
        <html>
            <body>
                <h1>Normal Google Maps Business</h1>
                <div class="business-name">Test Restaurant</div>
                <div class="rating">4.5 stars</div>
            </body>
        </html>
        """)
        
        result = await is_captcha_present(page)
        print(f"✅ Test 1 - Normal page: {'FAILED - False positive' if result else 'PASSED - No CAPTCHA detected'}")
        
        # Test 2: reCAPTCHA iframe
        await page.set_content("""
        <html>
            <body>
                <iframe src="https://www.google.com/recaptcha/api2/anchor"></iframe>
                <h1>Verify you're human</h1>
            </body>
        </html>
        """)
        
        result = await is_captcha_present(page)
        print(f"{'✅' if result else '❌'} Test 2 - reCAPTCHA iframe: {'PASSED - CAPTCHA detected' if result else 'FAILED - Missed CAPTCHA'}")
        
        # Test 3: CAPTCHA redirect form
        await page.set_content("""
        <html>
            <body>
                <form action="/CaptchaRedirect" method="POST">
                    <input type="text" name="captcha">
                    <button>Submit</button>
                </form>
            </body>
        </html>
        """)
        
        result = await is_captcha_present(page)
        print(f"{'✅' if result else '❌'} Test 3 - CAPTCHA form: {'PASSED - CAPTCHA detected' if result else 'FAILED - Missed CAPTCHA'}")
        
        # Test 4: "Unusual traffic" message
        await page.set_content("""
        <html>
            <body>
                <h1>Sorry...</h1>
                <p>Our systems have detected unusual traffic from your computer network.</p>
                <p>Please verify you're not a robot.</p>
            </body>
        </html>
        """)
        
        result = await is_captcha_present(page)
        print(f"{'✅' if result else '❌'} Test 4 - Unusual traffic text: {'PASSED - CAPTCHA detected' if result else 'FAILED - Missed CAPTCHA'}")
        
        # Test 5: Automated requests warning
        await page.set_content("""
        <html>
            <body>
                <h1>Automated requests detected</h1>
                <p>Please complete the CAPTCHA below to continue.</p>
            </body>
        </html>
        """)
        
        result = await is_captcha_present(page)
        print(f"{'✅' if result else '❌'} Test 5 - Automated requests text: {'PASSED - CAPTCHA detected' if result else 'FAILED - Missed CAPTCHA'}")
        
        await browser.close()
        
        print("\n✨ CAPTCHA Detection Tests Complete!\n")


async def is_captcha_present(page) -> bool:
    """
    Enhanced CAPTCHA detection with multiple indicators.
    
    This is a standalone copy of the detection logic for testing.
    """
    try:
        # Check for reCAPTCHA iframe
        captcha_iframe = await page.query_selector("iframe[src*='recaptcha'], iframe[src*='captcha']")
        if captcha_iframe:
            print("  → Detected reCAPTCHA iframe")
            return True
        
        # Check for CAPTCHA redirect form
        captcha_form = await page.query_selector("form[action*='CaptchaRedirect'], form[action*='captcha']")
        if captcha_form:
            print("  → Detected CAPTCHA redirect form")
            return True
        
        # Check page content for blocking indicators
        content = await page.content()
        content_lower = content.lower()
        
        blocking_indicators = [
            "unusual traffic",
            "captcha",
            "sorry",
            "automated requests",
            "verify you're not a robot",
            "our systems have detected",
            "please verify",
        ]
        
        for indicator in blocking_indicators:
            if indicator in content_lower:
                print(f"  → Detected blocking indicator: '{indicator}'")
                return True
        
        return False
        
    except Exception as e:
        print(f"  ⚠️  Error checking for CAPTCHA: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_captcha_detection())
