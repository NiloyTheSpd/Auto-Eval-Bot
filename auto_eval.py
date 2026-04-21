"""
MIST Faculty Evaluation Bot — Selenium + API Hybrid
=======================================================
Opens a real Chrome window to log you in, extracts your
session token automatically, then fires API submissions.
No DevTools. No manual token copying. No hassle.

Requirements:
    pip install requests selenium webdriver-manager

Usage:
    python auto_eval.py
"""

import json
import sys
import time
import getpass
import warnings
import requests
import urllib3
from selenium import webdriver

# MIST's API cert chain isn't trusted by Python's default CA bundle.
# The browser handles it fine; suppress the warning for CLI cleanliness.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

try:
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False

# ── API Endpoints ─────────────────────────────────────────────────────────────

BASE_URL   = "https://api-uniplex.mist.ac.bd/student-portal"
LIST_URL   = f"{BASE_URL}/pending-student-faculty-evaluation-list"
SUBMIT_URL = f"{BASE_URL}/submit-faculty-evaluation"
PORTAL_URL = "https://student.mist.ac.bd"

# ── Rating Options ────────────────────────────────────────────────────────────
# answerId 30 = Excellent is confirmed from reverse engineering.
# The rest (29–26) are assumed sequential — they may differ on your portal.
# If submissions succeed but ratings feel off, inspect a real network payload.

RATING_OPTIONS = {
    "1": (30, "Excellent  ✦ (confirmed)"),
    "2": (29, "Very Good  (assumed ID 29)"),
    "3": (28, "Good       (assumed ID 28)"),
    "4": (27, "Average    (assumed ID 27)"),
    "5": (26, "Poor       (assumed ID 26)"),
}

QUESTION_IDS = [56, 57, 58, 59, 60, 61, 62, 63, 64, 65]
DELAY        = 0.4   # seconds between submissions


# ── Config Prompts ────────────────────────────────────────────────────────────

def prompt_config() -> tuple[int, str, str]:
    """
    Interactive pre-run configuration.
    Returns (answer_id, comments, recommendations).
    """
    W = 54
    print("─" * W)
    print("  Evaluation Settings")
    print("─" * W)

    # Rating
    print("\n  MCQ Rating for all questions:")
    for key, (aid, label) in RATING_OPTIONS.items():
        print(f"    [{key}] {label}")
    print("    [c] Custom answer ID")
    print()

    while True:
        choice = input("  Your choice [1]: ").strip() or "1"
        if choice in RATING_OPTIONS:
            answer_id, rating_label = RATING_OPTIONS[choice]
            print(f"  → Rating set to: {rating_label.split('(')[0].strip()}")
            break
        elif choice.lower() == "c":
            try:
                answer_id = int(input("  Enter custom answer ID: ").strip())
                rating_label = f"Custom (ID {answer_id})"
                print(f"  → Rating set to ID {answer_id}")
                break
            except ValueError:
                print("  ✗ Invalid ID. Try again.")
        else:
            print("  ✗ Invalid choice. Try again.")

    # Comments
    print()
    default_comments = "Good"
    raw = input(f"  Review comment [{default_comments}]: ").strip()
    comments = raw if raw else default_comments

    # Recommendations
    default_rec = "Good"
    raw = input(f"  Recommendation [{default_rec}]: ").strip()
    recommendations = raw if raw else default_rec

    print()
    print("─" * W)
    print(f"  Rating        : {rating_label.split('(')[0].strip()}")
    print(f"  Comment       : {comments}")
    print(f"  Recommendation: {recommendations}")
    print("─" * W)
    input("\n  Press Enter to continue to login... ")

    return answer_id, comments, recommendations


# ── Selenium Login → Token Extraction ─────────────────────────────────────────

def build_driver(headless: bool = False) -> webdriver.Chrome:
    """Create a Chrome WebDriver instance."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--window-size=1100,750")

    if USE_WDM:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)
    return webdriver.Chrome(options=opts)


def extract_token_from_storage(driver: webdriver.Chrome) -> str | None:
    """
    Scan localStorage (and cookies) for a JWT access token.
    JWTs always start with 'eyJ'.
    """
    try:
        # --- localStorage scan ---
        all_keys: list = driver.execute_script("return Object.keys(localStorage);")
        for key in all_keys:
            val: str = driver.execute_script(f"return localStorage.getItem('{key}');")
            if not val:
                continue

            # Direct JWT string
            if val.startswith("eyJ"):
                return val

            # JSON object that may contain the token
            try:
                parsed = json.loads(val)
                token = _dig_jwt(parsed)
                if token:
                    return token
            except (json.JSONDecodeError, TypeError):
                pass

        # --- sessionStorage scan ---
        all_keys = driver.execute_script("return Object.keys(sessionStorage);")
        for key in all_keys:
            val = driver.execute_script(f"return sessionStorage.getItem('{key}');")
            if val and val.startswith("eyJ"):
                return val
            try:
                parsed = json.loads(val)
                token = _dig_jwt(parsed)
                if token:
                    return token
            except (json.JSONDecodeError, TypeError):
                pass

    except Exception as exc:
        print(f"  ✗ Storage scan error: {exc}")

    return None


def _dig_jwt(obj, depth: int = 0) -> str | None:
    """Recursively search a dict/list for a JWT string."""
    if depth > 4:
        return None
    if isinstance(obj, str) and obj.startswith("eyJ"):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _dig_jwt(v, depth + 1)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _dig_jwt(item, depth + 1)
            if found:
                return found
    return None


def selenium_login(username: str, password: str) -> str | None:
    """
    Opens Chrome, logs into the MIST portal, extracts the JWT.
    Returns the access token string, or None on failure.
    """
    print("\n→ Opening Chrome browser...")
    try:
        driver = build_driver(headless=False)
    except WebDriverException as e:
        print(f"  ✗ Could not start Chrome: {e}")
        print("  Make sure Chrome is installed and chromedriver matches your version.")
        return None

    wait = WebDriverWait(driver, 20)

    try:
        driver.get(f"{PORTAL_URL}/login")
        print("  → Navigated to login page")

        # Fill in credentials — try common field selectors
        for selector in ['input[type="text"]', 'input[name="username"]',
                          'input[placeholder*="ID"]', 'input[placeholder*="id"]']:
            try:
                field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                field.clear()
                field.send_keys(username)
                break
            except TimeoutException:
                continue

        for selector in ['input[type="password"]', 'input[name="password"]']:
            try:
                field = driver.find_element(By.CSS_SELECTOR, selector)
                field.clear()
                field.send_keys(password)
                break
            except Exception:
                continue

        # Submit
        for selector in ['button[type="submit"]', 'input[type="submit"]',
                          'button.login-btn', 'button']:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                break
            except Exception:
                continue

        print("  → Credentials submitted, waiting for redirect...")

        # Wait until URL changes away from /login
        try:
            wait.until(lambda d: "/login" not in d.current_url)
        except TimeoutException:
            print("  ✗ Login redirect timed out — check credentials or CAPTCHA.")
            driver.quit()
            return None

        print(f"  ✓ Logged in  ({driver.current_url})")

        # Give the SPA a moment to store the token
        time.sleep(1.5)

        token = extract_token_from_storage(driver)
        if token:
            print("  ✓ Token extracted from browser storage")
        else:
            print("  ✗ Could not auto-extract token.")
            print("    The browser will stay open — try refreshing the page,")
            print("    then press Enter here once the dashboard has loaded.")
            input("  Press Enter to retry token extraction: ")
            token = extract_token_from_storage(driver)

        return token

    finally:
        driver.quit()
        print("  → Browser closed")


# ── API Helpers ───────────────────────────────────────────────────────────────

def make_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/plain, */*",
        "Origin":        PORTAL_URL,
        "Referer":       f"{PORTAL_URL}/",
        "User-Agent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def get_pending_evaluations(token: str) -> list[dict]:
    resp = requests.get(LIST_URL, headers=make_headers(token), timeout=10, verify=False)
    data = resp.json()

    if not data.get("success"):
        print(f"✗ Could not fetch evaluation list: {data.get('message')}")
        return []

    pending = []
    for semester in data.get("data", []):
        sem_name = semester.get("semesterName", "")
        for course in semester.get("courses", []):
            code  = course.get("courseCode", "")
            for faculty in course.get("faculties", []):
                pending.append({
                    "confId":      faculty["confId"],
                    "facultyName": faculty.get("facultyName", "Unknown"),
                    "courseCode":  code,
                    "semester":    sem_name,
                })
    return pending


def submit_evaluation(token: str, conf_id: int,
                       answer_id: int, comments: str, recommendations: str) -> bool:
    payload = {
        "recommendations":     recommendations,
        "comments":            comments,
        "studentFacultyEvaId": str(conf_id),
        "answers": [
            {"questionId": qid, "answerId": answer_id}
            for qid in QUESTION_IDS
        ],
    }
    try:
        resp = requests.post(SUBMIT_URL, headers=make_headers(token),
                             json=payload, timeout=10, verify=False)
        return resp.json().get("success", False)
    except Exception as e:
        print(f"    Request error: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    W = 54
    print("=" * W)
    print("  MIST Faculty Evaluation Bot — Selenium Edition")
    print("=" * W)

    # 1. User configures rating / text before login
    answer_id, comments, recommendations = prompt_config()

    # 2. Credentials
    print()
    username = input("Student ID : ").strip()
    password  = getpass.getpass("Password   : ")   # hidden input

    # 3. Selenium login → token
    token = selenium_login(username, password)
    if not token:
        print("\n✗ Could not obtain a session token. Exiting.")
        sys.exit(1)

    # 4. Fetch pending evaluations
    print("\n→ Fetching pending evaluations...")
    pending = get_pending_evaluations(token)

    if not pending:
        print("✓ No pending evaluations found (or token already expired).")
        sys.exit(0)

    total = len(pending)
    print(f"✓ Found {total} pending evaluation(s)\n")

    done = failed = 0

    for i, item in enumerate(pending, 1):
        label = f"{item['courseCode']} — {item['facultyName']}"
        print(f"  [{i:2}/{total}] {label[:52]:<52}", end=" ", flush=True)

        ok = submit_evaluation(token, item["confId"],
                                answer_id, comments, recommendations)
        time.sleep(DELAY)

        if ok:
            print("✓")
            done += 1
        else:
            print("✗ Failed")
            failed += 1

    print(f"\n{'=' * W}")
    print(f"  Done: {done}/{total}  |  Failed: {failed}")
    print(f"{'=' * W}\n")

    if failed:
        print("Tip: Token may have expired mid-run. Re-run the script to retry.\n")


if __name__ == "__main__":
    main()