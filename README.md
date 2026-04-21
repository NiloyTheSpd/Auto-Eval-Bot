# MIST Faculty Evaluation Bot

A Python automation tool that submits all pending faculty evaluations on the [MIST Student Portal](https://student.mist.ac.bd) in one go — no clicking, no copy-pasting tokens, no DevTools.

> **Built out of frustration with the portal, not malice toward faculty.**
> Please read the [Ethical Use](#-ethical-use--warnings) section before running.

---

## How It Works

1. Opens a real Chrome window and logs you in normally
2. Extracts your session token automatically from browser storage
3. Closes the browser
4. Fetches your pending evaluations via the portal API
5. Submits all of them with your chosen rating and comments

It's a **Selenium + requests hybrid** — browser only for auth, lightweight API calls for everything else.

---

## Requirements

- Python 3.10+
- Google Chrome (any recent version)
- The following Python packages:

```bash
pip install requests selenium webdriver-manager
```

`webdriver-manager` handles ChromeDriver automatically — no manual driver download needed.

---

## Usage

```bash
python auto_eval.py
```

You'll be prompted to configure everything before login:

```
──────────────────────────────────────────────────────
  Evaluation Settings
──────────────────────────────────────────────────────

  MCQ Rating for all questions:
    [1] Excellent  ✦ (confirmed)
    [2] Very Good  (assumed ID 29)
    [3] Good       (assumed ID 28)
    [4] Average    (assumed ID 27)
    [5] Poor       (assumed ID 26)
    [c] Custom answer ID

  Your choice [1]: 1

  Review comment [Good]: Great teacher
  Recommendation [Good]: Highly recommended
```

Then enter your Student ID and password (password input is hidden).  
Chrome opens, logs in, and closes. Submissions run automatically.

```
→ Fetching pending evaluations...
✓ Found 6 pending evaluations

  [ 1/ 6] CSE-4101 — Dr. Example Name              ✓
  [ 2/ 6] CSE-4103 — Prof. Another Name            ✓
  ...

══════════════════════════════════════════════════════
  Done: 6/6  |  Failed: 0
══════════════════════════════════════════════════════
```

---

## ⚠️ Ethical Use & Warnings

### Anonymity — what's actually true
 
The portal markets evaluations as "anonymous." That is **partially true at best.**
 
Here's what the submission payload actually contains:
 
```
Authorization: Bearer <your JWT>   ← your studentId and username are encoded inside
studentFacultyEvaId: <entry ID>    ← a record tied specifically to you and that faculty
```
 
**What faculty CAN'T see:** Individual student names on their own evaluation dashboard. In that narrow sense, it is anonymous to the faculty member.
 
**What admins CAN see:** Everything. The server has the full record — who submitted, who they rated, what score, what timestamp. It is completely traceable at the system/admin level.
 
**Practical implication:** Submitting all-Excellent ratings via a bot is theoretically detectable — an admin query like *"show me every student who gave all 10s with comment='Good' in under 5 seconds"* would surface bot runs trivially. Rate accordingly.
 

**Read this before you run the script.**

### Be honest
This tool automates the *submission process*, not your *opinion*. Faculty evaluations exist so the institution can improve teaching quality. Submitting fake "Excellent" ratings for a bad teacher, or tanking a good teacher with "Poor," undermines that purpose.

**Set ratings that reflect your actual experience.**

### Academic integrity
Using automation tools on institutional portals may violate MIST's terms of service or student conduct policies. By running this script, you accept full responsibility for any consequences. The author takes none.

### No warranty
This script is provided as-is. If the portal changes its API, authentication flow, or question IDs, the script may break or submit incorrect data. Always verify your submissions in the portal afterward.

### SSL note
MIST's API server (`api-uniplex.mist.ac.bd`) uses a certificate chain that Python's default CA bundle cannot verify. The script disables SSL verification (`verify=False`) on API calls as a workaround. Your credentials are still sent over HTTPS — only the certificate chain check is skipped. Chrome handles this fine natively, which is why the login step works without issues.

### Rating IDs
Only `answerId=30` (Excellent) has been confirmed through network inspection. IDs 29–26 for lower ratings are assumed sequential. If you want to verify before bulk-submitting, inspect one real evaluation submission in Chrome DevTools → Network tab and check the payload.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SSL certificate verify failed` | Already handled in v3 — update to latest version |
| Chrome doesn't open | Make sure Chrome is installed; `webdriver-manager` handles the driver |
| Login redirect times out | Check your credentials; CAPTCHA may have triggered — try logging in manually first |
| Token extraction fails | Wait for the dashboard to fully load, press Enter when prompted for retry |
| All submissions fail | Token may have expired mid-run; just re-run the script |
| `ModuleNotFoundError` | Run `pip install requests selenium webdriver-manager` |

---

## Project Structure

```
auto_eval.py   # Main script (everything in one file)
README.md
LICENSE
```

---

## Contributing

PRs welcome. Useful contributions:

- Verified answer IDs for all rating levels (inspect a real network payload)
- Firefox/Edge support
- Headless mode toggle as a CLI flag

---

## License

MIT — see [LICENSE](LICENSE).

---

*Not affiliated with MIST or the Uniplex platform.*
