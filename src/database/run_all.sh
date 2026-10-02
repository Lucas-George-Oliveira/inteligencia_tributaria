#!/usr/bin/env bash
# =============================================================================
# SISTEMA TRIBUTÁRIO - Script de Execução Automatizada
# Arquivo: db/run_all.sh
# Uso:     ./run_all.sh [host] [porta] [banco] [usuario]
# Exemplo: ./run_all.sh localhost 5432 tributario_db postgres
#
# O script executa em ordem:
#   1. V1 - Schema (tabelas, índices)
#   2. V2 - Dados piloto
#   3. V3 - Consultas de validação
#   4. pg_dump - Exporta o schema para versionamento
# =============================================================================

set -euo pipefail

# --- Parâmetros (com defaults) -----------------------------------------------
HOST="${1:-localhost}"
PORT="${2:-5432}"
DB="${3:-tributario_db}"
USER="${4:-postgres}"

# --- Cores para output --------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_DIR="$SCRIPT_DIR/schema"
EXPORT_DIR="$SCRIPT_DIR/exports"

mkdir -p "$EXPORT_DIR"

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
err()  { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

echo ""
echo "============================================================"
echo " SISTEMA TRIBUTÁRIO - Inicialização do Banco de Dados"
echo " Host: $HOST | Porta: $PORT | Banco: $DB | Usuário: $USER"
echo "============================================================"
echo ""

# --- Verifica se psql está disponível ----------------------------------------
command -v psql &>/dev/null || err "psql não encontrado. Instale o PostgreSQL client."

# --- Testa conexão -----------------------------------------------------------
psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -c '\q' 2>/dev/null \
    || err "Não foi possível conectar ao PostgreSQL em $HOST:$PORT como $USER."
log "Conexão com PostgreSQL estabelecida."

# --- Cria o banco se não existir ---------------------------------------------
DB_EXISTS=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres \
    -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'" 2>/dev/null || echo "")

if [[ "$DB_EXISTS" != "1" ]]; then
    warn "Banco '$DB' não encontrado. Criando..."
    psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres \
        -c "CREATE DATABASE $DB ENCODING='UTF8' LC_COLLATE='pt_BR.UTF-8' LC_CTYPE='pt_BR.UTF-8' TEMPLATE template0;" \
        2>/dev/null || \
    psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres \
        -c "CREATE DATABASE $DB ENCODING='UTF8';"
    log "Banco '$DB' criado."
else
    log "Banco '$DB' já existe. Continuando..."
fi

# --- Executa os scripts SQL em ordem -----------------------------------------
run_sql() {
    local file="$1"
    local label="$2"
    echo ""
    echo "--- $label ---"
    psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" \
        --set ON_ERROR_STOP=1 \
        -f "$file" \
        && log "$label concluído." \
        || err "Falha ao executar $file"
}

run_sql "$SCHEMA_DIR/V1__create_schema.sql"   "V1 - Criação do Schema"
run_sql "$SCHEMA_DIR/V2__seed_dados_piloto.sql" "V2 - Carga dos Dados Piloto"

# --- Consultas de validação (exibe resultado no terminal) --------------------
echo ""
echo "--- V3 - Consultas de Validação ---"
psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" \
    --set ON_ERROR_STOP=1 \
    -f "$SCHEMA_DIR/V3__consultas_validacao.sql" \
    && log "V3 - Consultas de validação executadas." \
    || err "Falha nas consultas de validação."

# --- Exporta o schema (pg_dump) para versionamento --------------------------
echo ""
echo "--- Exportando schema para versionamento ---"
EXPORT_FILE="$EXPORT_DIR/schema_export_$(date +%Y%m%d_%H%M%S).sql"

pg_dump \
    -h "$HOST" \
    -p "$PORT" \
    -U "$USER" \
    -d "$DB" \
    --schema=tributario \
    --schema-only \
    --no-owner \
    --no-privileges \
    --no-comments \
    -f "$EXPORT_FILE" \
    && log "Schema exportado: $EXPORT_FILE" \
    || err "Falha ao exportar o schema."

# Copia como arquivo canônico (sempre sobrescreve - para o git rastrear diff)
cp "$EXPORT_FILE" "$SCRIPT_DIR/schema_atual.sql"
log "schema_atual.sql atualizado (pronto para commit no git)."

echo ""
echo "============================================================"
echo " CONCLUÍDO COM SUCESSO!"
echo " Para versionar, execute:"
echo "   git add db/schema_atual.sql"
echo "   git commit -m 'chore(db): atualiza schema exportado'"
echo "============================================================"
echo ""
