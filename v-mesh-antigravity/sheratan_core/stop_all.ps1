#== == == == == == == == == == == == == == == == == == == == == ==
#Sheratan Quick Stop Script
#== == == == == == == == == == == == == == == == == == == == == ==
#Stoppt alle Sheratan Services

Write - Host "" Write - Host "🛑 Stopping Sheratan System..." -
        ForegroundColor Red Write -
        Host ""

#Stop all background jobs
        Write -
        Host "Stopping background jobs..." - ForegroundColor Yellow Get - Job |
    Where - Object{$_.Name - like "*sheratan*" - or
                   $_.Command - like "*uvicorn*" - or
                   $_.Command - like "*npm*"} |
    Stop - Job Get - Job |
    Where - Object{$_.Name - like "*sheratan*" - or
                   $_.Command - like "*uvicorn*" - or
                   $_.Command - like "*npm*"} |
    Remove - Job Get - Job | Stop - Job Get - Job |
    Remove -
        Job

#Stop Docker containers
            Write -
        Host "Stopping Docker containers..." - ForegroundColor Yellow Push -
        Location - Path "C:\sheratan-core-poc" docker - compose down Pop -
        Location

            Write -
        Host "" Write - Host "✅ All services stopped!" -
        ForegroundColor Green Write - Host "" Write -
        Host "ℹ️  Chrome Debug Mode still running - close manually if needed" -
        ForegroundColor Gray
