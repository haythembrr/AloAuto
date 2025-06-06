# Remove all __pycache__ directories
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force

# Remove all migrations folders except __init__.py
Get-ChildItem -Path . -Filter "migrations" -Recurse -Directory  | Remove-Item -Recurse -Force

# Remove the database file
if (Test-Path "db.sqlite3") {
    Remove-Item "db.sqlite3" -Force
}

Write-Host "Cleaned all __pycache__, migrations, and database files"