$pgDir = "C:\Program Files\PostgreSQL\17"
$vectorDir = "v:\graphmind\vector_extracted"

if (-Not (Test-Path -Path $pgDir)) {
    Write-Error "PostgreSQL 17 installation not found at $pgDir"
    Exit
}

Write-Host "Copying pgvector files to $pgDir..."
Copy-Item -Path "$vectorDir\include\*" -Destination "$pgDir\include" -Recurse -Force
Copy-Item -Path "$vectorDir\lib\*" -Destination "$pgDir\lib" -Recurse -Force
Copy-Item -Path "$vectorDir\share\*" -Destination "$pgDir\share" -Recurse -Force

Write-Host "pgvector installed successfully! Please restart the PostgreSQL service."
Write-Host "You can do this by running: Restart-Service -Name postgresql-x64-17 (if that is your service name)"
