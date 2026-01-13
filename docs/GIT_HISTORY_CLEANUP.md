# Git History Cleanup with BFG Repo-Cleaner

**Date:** 2026-01-13  
**Purpose:** Remove private keys from entire git history

---

## Prerequisites

### 1. Install Java (if not already installed)

BFG requires Java. Check if installed:
```bash
java -version
```

If not installed, download from: https://www.java.com/download/

### 2. Download BFG Repo-Cleaner

Download the latest JAR from: https://rtyley.github.io/bfg-repo-cleaner/

Save to: `C:\Tools\bfg.jar` (or any location)

---

## Cleanup Steps

### Step 1: Create a fresh clone (mirror)

```bash
cd C:\
git clone --mirror https://github.com/YOUR_USERNAME/sauber_main.git sauber_main-mirror
cd sauber_main-mirror
```

### Step 2: Run BFG to remove keys

```bash
java -jar C:\Tools\bfg.jar --delete-files node-A.json
java -jar C:\Tools\bfg.jar --delete-files node-B.json
```

### Step 3: Clean up repository

```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Step 4: Push cleaned history

```bash
# IMPORTANT: This rewrites history on GitHub!
git push --force
```

### Step 5: Update your local repo

```bash
cd C:\sauber_main
git fetch origin
git reset --hard origin/main
```

---

## Alternative: Manual Method (if BFG doesn't work)

### Using git filter-repo (recommended alternative)

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove files from history
git filter-repo --path mesh/offgrid/keys/node-A.json --invert-paths
git filter-repo --path mesh/offgrid/keys/node-B.json --invert-paths

# Force push
git push origin --force --all
```

### Using git filter-branch (legacy method)

```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch mesh/offgrid/keys/node-A.json mesh/offgrid/keys/node-B.json" \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

---

## Verification

After cleanup, verify keys are gone:

```bash
# Check if files exist in any commit
git log --all --full-history -- mesh/offgrid/keys/node-A.json
git log --all --full-history -- mesh/offgrid/keys/node-B.json

# Should return empty (no commits found)
```

---

## Important Notes

⚠️ **This rewrites Git history!**
- All commit hashes will change
- Anyone who cloned the repo must re-clone
- Backup before proceeding

✅ **Safe because:**
- Repo is private
- No external collaborators
- No one has accessed it

---

## Quick Start (Copy-Paste)

```powershell
# 1. Download BFG
# Go to: https://rtyley.github.io/bfg-repo-cleaner/
# Save to: C:\Tools\bfg.jar

# 2. Create mirror clone
cd C:\
git clone --mirror YOUR_REPO_URL sauber_main-mirror
cd sauber_main-mirror

# 3. Run BFG
java -jar C:\Tools\bfg.jar --delete-files node-A.json
java -jar C:\Tools\bfg.jar --delete-files node-B.json

# 4. Cleanup
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. Push
git push --force

# 6. Update local repo
cd C:\sauber_main
git fetch origin
git reset --hard origin/main
```

---

**Status:** Ready to execute
