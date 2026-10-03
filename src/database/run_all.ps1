# =============================================================================
# SISTEMA TRIBUTÁRIO - Script de Execução (Windows PowerShell)
# Arquivo: db/run_all.ps1
# Uso:     .\run_all.ps1 [-Host localhost] [-Port 5432] [-DB tributario_db] [-User postgres]
# =============================================================================

param(
    [string]$DBHost = "localhost",
    [string]$Port   = "5432",
    [string]$DB     = "tributario_db",
    [string]$User   = "postgres"
)

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$SchemaDir  = Join-Path $ScriptDir "schema"
$ExportDir  = Join-Path $ScriptDir "exports"

if (-not (Test-Path $ExportDir)) { New-Item -ItemType Directory -Path $ExportDir | Out-Null }

function Log   { param($msg) Write-Host "[OK] $msg"    -ForegroundColor Green  }
function Warn  { param($msg) Write-Host "[AVISO] $msg" -ForegroundColor Yellow }
function Err   { param($msg) Write-Host "[ERRO] $msg"  -ForegroundColor Red; exit 1 }

function Invoke-Psql {
    param([string]$Database, [string]$File, [string]$Command)
    $args_list = @("-h", $DBHost, "-p", $Port, "-U", $User, "-d", $Database, "--set", "ON_ERROR_STOP=1")
    if ($File)    { $args_list += @("-f", $File) }
    if ($Command) { $args_list += @("-c", $Command) }
    & psql @args_list
    if ($LASTEXITCODE -ne 0) { Err "Falha no comando psql." }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SISTEMA TRIBUTÁRIO - Inicialização do Banco de Dados"
Write-Host " Host: $DBHost | Porta: $Port | Banco: $DB | Usuário: $User"
Write-Host "============================================================"
Write-Host ""

# Verifica psql
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    Err "psql não encontrado. Adicione o PostgreSQL ao PATH do sistema."
}

# Testa conexão
try { Invoke-Psql -Database "postgres" -Command '\q' } catch { Err "Falha ao conectar ao PostgreSQL." }
Log "Conexão estabelecida."

# Cria banco se não existir
$dbExists = (& psql -h $DBHost -p $Port -U $User -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'" 2>$null)
if ($dbExists -ne "1") {
    Warn "Banco '$DB' não encontrado. Criando..."
    Invoke-Psql -Database "postgres" -Command "CREATE DATABASE $DB ENCODING='UTF8';"
    Log "Banco '$DB' criado."
} else {
    Log "Banco '$DB' já existe."
}

# Executa scripts em ordem
Write-Host "`n--- V1 - Criação do Schema ---"
Invoke-Psql -Database $DB -File (Join-Path $SchemaDir "V1__create_schema.sql")
Log "Schema criado."

Write-Host "`n--- V2 - Carga dos Dados Piloto ---"
Invoke-Psql -Database $DB -File (Join-Path $SchemaDir "V2__seed_dados_piloto.sql")
Log "Dados piloto inseridos."

Write-Host "`n--- V3 - Consultas de Validação ---"
Invoke-Psql -Database $DB -File (Join-Path $SchemaDir "V3__consultas_validacao.sql")
Log "Consultas de validação executadas."

# Exporta schema para versionamento
Write-Host "`n--- Exportando schema ---"
$timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$exportFile = Join-Path $ExportDir "schema_export_$timestamp.sql"
$canonical  = Join-Path $ScriptDir "schema_atual.sql"

& pg_dump -h $DBHost -p $Port -U $User -d $DB `
    --schema=tributario `
    --schema-only `
    --no-owner `
    --no-privileges `
    --no-comments `
    -f $exportFile

if ($LASTEXITCODE -ne 0) { Err "Falha no pg_dump." }
Copy-Item -Path $exportFile -Destination $canonical -Force
Log "Schema exportado: $exportFile"
Log "schema_atual.sql atualizado."

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " CONCLUÍDO COM SUCESSO!"
Write-Host " Para versionar, execute:"
Write-Host "   git add db\schema_atual.sql"
Write-Host "   git commit -m 'chore(db): atualiza schema exportado'"
Write-Host "============================================================"
Write-Host ""
