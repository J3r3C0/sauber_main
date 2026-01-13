# Sheratan Repository Portability Fixes

## Status: ✅ All Fixes Applied

All portability issues identified during PC2 setup have been resolved.

---

## Fixes Applied

### 1. Dynamic Chrome Detection ✅

**Created**: `scripts/find_chrome.bat`

**Purpose**: Automatically locates Chrome across different installation paths

**Checks**:
- `C:\Program Files\Google\Chrome\Application\chrome.exe`
- `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
- `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`

**Updated Scripts**:
- `START_COMPLETE_SYSTEM.bat` - Now uses `%CHROME_PATH%`
- `RUN_PRODUCTION_VALIDATION.bat` - Now uses `%CHROME_PATH%`

---

### 2. Dashboard Path Fix ✅

**File**: `scripts/INSTALL_DEPENDENCIES.ps1`

**Change**:
```powershell
# Before
$dashboardPkg = Join-Path $PROJECT_ROOT "dashboard\package.json"

# After
$dashboardPkg = Join-Path $PROJECT_ROOT "external\dashboard\package.json"
```

**Impact**: Dashboard dependencies now install correctly

---

### 3. Missing Dashboard Components ✅

**Status**: Already present in repository

**Files verified**:
- `external/dashboard/src/features/logs/LogsTab.tsx` ✅
- `external/dashboard/src/data/mockData.ts` ✅
- `external/dashboard/.env.example` ✅ (template committed to Git)

**Note**: `.env` file is auto-created from `.env.example` by `SETUP_PC2.ps1`

---

### 4. Environment Configuration ✅

**File**: `external/dashboard/.env` (auto-generated)

**Source**: `external/dashboard/.env.example` (committed to Git)

**Content**:
```
VITE_API_BASE_URL=http://localhost:8001
VITE_BACKEND_POC_URL=http://localhost:7007
```

**Handling**: 
- `.env` is in `.gitignore` (not committed)
- `.env.example` is committed as template
- `SETUP_PC2.ps1` automatically copies `.env.example` → `.env`

---

### 5. PC2 Setup Script ✅

**Created**: `scripts/SETUP_PC2.ps1`

**Features**:
- Automated repository cloning
- Dependency installation
- Chrome verification
- Network configuration
- Burn-in test directory setup

---

## PC2 Setup Instructions

### On PC2:

1. **Clone Repository** (or copy from PC1)
   ```powershell
   git clone <your-repo-url> C:\sheratan_test
   cd C:\sheratan_test
   ```

2. **Run Setup Script**
   ```powershell
   .\scripts\SETUP_PC2.ps1
   ```

3. **Update Configuration**
   - Edit `SETUP_PC2.ps1` and set:
     - `$REPO_URL` (your Git repository)
     - `$PC1_IP` (your PC1 IP address)

4. **Start System**
   ```powershell
   .\START_COMPLETE_SYSTEM.bat
   ```

5. **Run Burn-In Tests**
   ```powershell
   .\tests\burn_in\RUN_ALL_TESTS.ps1
   ```

### From PC1 (Monitor Remotely):

1. **Open Dashboard**
   ```
   http://<PC2-IP>:3001
   ```

2. **Check WHY-API**
   ```
   http://<PC2-IP>:8001/api/why/stats
   ```

3. **View Logs** (via network share)
   ```
   \\<PC2-IP>\C$\sheratan_test\logs\
   ```

---

## Burn-In Test Workflow

```
PC1 (Development)          PC2 (Testing)
─────────────────          ─────────────
1. Write code              
2. Commit & Push    ──────▶ 3. Pull latest
                            4. Run burn-in tests
                            5. Generate reports
6. Review results  ◀────── 
   (via Dashboard)
```

---

## Files Changed

| File | Change | Status |
|------|--------|--------|
| `scripts/find_chrome.bat` | Created | ✅ New |
| `scripts/INSTALL_DEPENDENCIES.ps1` | Dashboard path fix | ✅ Fixed |
| `START_COMPLETE_SYSTEM.bat` | Dynamic Chrome detection | ✅ Fixed |
| `RUN_PRODUCTION_VALIDATION.bat` | Dynamic Chrome detection | ✅ Fixed |
| `scripts/SETUP_PC2.ps1` | Created | ✅ New |

---

## Next Steps

1. ✅ **Commit these changes** to your repository
2. ✅ **Test on PC1** to ensure nothing broke
3. ✅ **Clone/Pull on PC2** and run `SETUP_PC2.ps1`
4. ✅ **Run burn-in tests** on PC2
5. ✅ **Monitor from PC1** via Dashboard

---

## Troubleshooting

### Chrome Not Found
```powershell
# Manually set CHROME_PATH
set CHROME_PATH="C:\Path\To\Chrome\chrome.exe"
.\START_COMPLETE_SYSTEM.bat
```

### Dashboard Build Fails
```powershell
# Rebuild dashboard
cd external\dashboard
npm install
npm run build
```

### Network Access Issues
```powershell
# Check firewall rules
New-NetFirewallRule -DisplayName "Sheratan Dashboard" -Direction Inbound -LocalPort 3001 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Sheratan Core API" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```

---

**Status**: Ready for PC2 deployment! 🚀
