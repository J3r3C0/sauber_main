@echo off
REM ============================================
REM Git History Cleanup - Remove Private Keys
REM ============================================

echo [WARNING] This will REWRITE Git history!
echo [WARNING] All commit hashes will change!
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo [1/4] Removing node-A.json from history...
git filter-repo --path mesh/offgrid/keys/node-A.json --invert-paths --force

echo.
echo [2/4] Removing node-B.json from history...
git filter-repo --path mesh/offgrid/keys/node-B.json --invert-paths --force

echo.
echo [3/4] Verifying removal...
git log --all --full-history -- mesh/offgrid/keys/node-A.json
git log --all --full-history -- mesh/offgrid/keys/node-B.json

echo.
echo [4/4] Ready to force push to origin
echo.
echo NEXT STEP: Run this command manually:
echo   git push origin --force --all
echo.
pause
