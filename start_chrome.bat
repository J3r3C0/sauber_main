@echo off
:: Sheratan V-Mesh Shield - Hardened Browser Startup
SET PROFILE_DIR="%~dp0runtime\transport\chrome_profile"

start chrome ^
  --user-data-dir=%PROFILE_DIR% ^
  --remote-debugging-port=9222 ^
  --disable-background-networking ^
  --disable-client-side-phishing-detection ^
  --disable-component-update ^
  --disable-default-apps ^
  --disable-domain-reliability ^
  --disable-sync ^
  --metrics-recording-only ^
  --no-first-run ^
  --no-pings ^
  --password-store=basic ^
  --disable-features=AutofillServerCommunication,InterestCohort,BrowsingTopics ^
  "https://chatgpt.com" "https://gemini.google.com/app"
