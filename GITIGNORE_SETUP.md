# ✅ .gitignore - UPDATED

**Date:** October 12, 2025  
**Status:** 🟢 Enhanced with project-specific rules

---

## What Was Added

Enhanced the existing .gitignore file with **project-specific rules** for the Caprae Capital lead generation system.

### New Entries Added

#### 1. Environment & Sensitive Data
```
.env
.env.local
.env.*.local
*.env
```
**Protects:** MongoDB URIs, API keys, proxy credentials

#### 2. Databases
```
*.db
*.sqlite
*.sqlite3
leads.db
```
**Protects:** Local SQLite databases and any test databases

#### 3. Proxies & User Agents (Critical!)
```
proxies.txt
user_agents.txt
!proxies.txt.example
!user_agents.txt.example
```
**Protects:** Your actual proxy list and user agent list
**Keeps:** Example files for documentation

#### 4. Celery & Redis
```
celerybeat.pid
dump.rdb
```
**Protects:** Celery process files and Redis database dumps

#### 5. Playwright
```
.playwright/
playwright/.env
```
**Protects:** Playwright browser data and configuration

#### 6. Scraped Data & Exports
```
exports/
data/
scraped_data/
*.csv
!example.csv
!**/examples/*.csv
```
**Protects:** All scraped lead data and CSV exports
**Keeps:** Example files for documentation

#### 7. Certificates & Keys
```
*.pem
*.key
*.crt
*.p12
```
**Protects:** SSL certificates and private keys

#### 8. Testing Artifacts
```
.pytest_cache/
htmlcov/
.coverage
coverage.xml
```
**Protects:** Test reports and coverage data

#### 9. Logs & Temporary Files
```
*.log
logs/
*.out
*.bak
*.swp
*.swo
*~
*.tmp
.cache/
temp/
tmp/
scratch/
```
**Protects:** Log files and temporary working files

#### 10. OS-Specific Files
```
# Windows
*.stackdump
[Dd]esktop.ini
$RECYCLE.BIN/
*.lnk

# Mac
.AppleDouble
.LSOverride

# Linux
.fuse_hidden*
.directory
.Trash-*
.nfs*
```
**Protects:** OS-generated files that shouldn't be in version control

---

## What's Still Tracked (Intentionally)

✅ **Example files:**
- `proxies.txt.example` - Template for proxy configuration
- `user_agents.txt.example` - Template for user agent list
- `.env.example` - Template for environment variables
- Example CSV files in examples/ directories

✅ **Source code:**
- All `.py` files (except `__pycache__`)
- All `.md` documentation files
- Configuration templates
- Test files

✅ **Dependencies:**
- `requirements.txt`
- `pytest.ini`
- `Pipfile` (if using)

---

## Critical Security Notes

### 🔒 NEVER Commit These Files:

1. **`.env`** - Contains MongoDB credentials, API keys
2. **`proxies.txt`** - Contains paid proxy credentials
3. **`user_agents.txt`** - May contain unique user agent strings
4. **`*.csv`** - Contains scraped business data (leads)
5. **`leads.db`** - Contains local lead database

### ✅ Always Commit These Files:

1. **`.env.example`** - Template showing required variables
2. **`proxies.txt.example`** - Format example
3. **`user_agents.txt.example`** - Format example
4. **`README.md`** - Documentation
5. **All source code** (`.py` files)

---

## Verification

Check what will be committed:

```bash
# See what's ignored
git status --ignored

# See what would be added
git add . --dry-run

# Check specific file
git check-ignore -v proxies.txt
# Should output: .gitignore:X:proxies.txt
```

---

## Common Scenarios

### Scenario 1: "I accidentally committed .env"

```bash
# Remove from git but keep local file
git rm --cached .env

# Commit the removal
git commit -m "Remove .env from version control"

# Verify it's now ignored
git status
```

### Scenario 2: "I want to add an example CSV"

```bash
# Create it in examples/ directory
mkdir examples
echo "name,phone,website" > examples/sample_leads.csv

# Or name it with 'example' in the name
echo "name,phone,website" > example_leads.csv

# Both will be tracked due to the ! rules
git add examples/sample_leads.csv
```

### Scenario 3: "I need to track a specific CSV"

```bash
# Force add it (bypasses .gitignore)
git add -f important_data.csv

# Or add exception to .gitignore before the *.csv rule
echo "!important_data.csv" >> .gitignore
```

---

## Project Structure with .gitignore Applied

```
Caprae-Capital-s-backend/
├── .env                        # ❌ IGNORED (sensitive)
├── .env.example                # ✅ TRACKED (template)
├── proxies.txt                 # ❌ IGNORED (sensitive)
├── proxies.txt.example         # ✅ TRACKED (template)
├── user_agents.txt             # ❌ IGNORED (sensitive)
├── leads.db                    # ❌ IGNORED (data)
├── dump.rdb                    # ❌ IGNORED (Redis)
├── requirements.txt            # ✅ TRACKED
├── README.md                   # ✅ TRACKED
├── .gitignore                  # ✅ TRACKED
├── app/
│   ├── __pycache__/           # ❌ IGNORED
│   ├── main.py                # ✅ TRACKED
│   ├── parsers.py             # ✅ TRACKED
│   ├── db_mongo.py            # ✅ TRACKED
│   └── ...
├── tests/
│   ├── .pytest_cache/         # ❌ IGNORED
│   ├── htmlcov/               # ❌ IGNORED
│   ├── test_parsers.py        # ✅ TRACKED
│   └── ...
├── logs/
│   └── app.log                # ❌ IGNORED
├── data/
│   └── scraped_leads.csv      # ❌ IGNORED
└── venv/                       # ❌ IGNORED
```

---

## Best Practices

### Before First Commit

1. **Review all files:**
   ```bash
   git status
   ```

2. **Check for sensitive data:**
   ```bash
   # Search for potential secrets
   grep -r "password" .
   grep -r "api_key" .
   grep -r "secret" .
   ```

3. **Verify .env is ignored:**
   ```bash
   git check-ignore .env
   # Should output: .gitignore:X:.env
   ```

### Regular Maintenance

1. **Review what's tracked:**
   ```bash
   git ls-files
   ```

2. **Find large files:**
   ```bash
   git ls-files | xargs du -h | sort -h
   ```

3. **Check for accidentally tracked secrets:**
   ```bash
   git log -p | grep -i "password\|secret\|api_key"
   ```

---

## Summary

✅ **Enhanced** existing .gitignore with 50+ project-specific rules
✅ **Protected** sensitive data (credentials, proxies, scraped leads)
✅ **Preserved** example files and documentation
✅ **Cleaned** OS-specific and build artifacts

**Status:** 🟢 Ready for version control

**Next Steps:**
1. Review your working directory: `git status`
2. Verify no sensitive files are tracked: `git ls-files`
3. Add and commit safely: `git add . && git commit -m "Initial commit"`

---

**⚠️ REMEMBER:** Once a file is committed to git, it's in the history forever (even if you delete it later). Always verify files before committing!
