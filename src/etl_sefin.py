"""Orquestrador ETL da Sprint E2 - receitas municipais (NUCLEOGOV).

Exemplos (a partir da raiz do repositório):
  python -m src.etl_sefin --sem-carga
  python -m src.etl_sefin --criar-tabela
  python -m src.etl_sefin --coletar --paginas 3 --criar-tabela
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
import pandas as pd
from sqlalchemy.engine import make_url

from src.core.limpeza_receitas import limpar_receitas
from src.database.carga_receitas import carregar_receitas

RAIZ = Path(__file__).resolve().parents[1]
PASTA_BRUTOS = RAIZ / "data" / "bruto"
PASTA_PROCESSADOS = RAIZ / "data" / "processado"
PASTA_REJEITADOS = RAIZ / "data" / "rejeitados"
PASTA_LOGS = RAIZ / "logs"


def configurar_logger() -> logging.Logger:
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("etl_sefin")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        arquivo = RotatingFileHandler(
            PASTA_LOGS / "etl_sefin.log", maxBytes=5_000_000, backupCount=3,
            encoding="utf-8",
        )
        arquivo.setFormatter(formato)
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formato)
        logger.addHandler(arquivo)
        logger.addHandler(console)
    return logger


def encontrar_json_mais_recente() -> Path:
    arquivos = list(PASTA_BRUTOS.glob("coleta_api_*.json"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhuma coleta encontrada em {PASTA_BRUTOS}. "
            "Execute src/api/coleta_dados.py ou use --arquivo ou --coletar."
        )
    return max(arquivos, key=lambda item: (item.stat().st_mtime_ns, item.name))


def ler_json(caminho: Path) -> list[dict]:
    with caminho.open("r", encoding="utf-8") as arquivo:
        conteudo = json.load(arquivo)
    if isinstance(conteudo, list):
        return conteudo
    if isinstance(conteudo, dict):
        if isinstance(conteudo.get("k1"), dict):
            return conteudo["k1"].get("dados", [])
        if isinstance(conteudo.get("dados"), list):
            return conteudo["dados"]
    raise ValueError("JSON incompatível: esperado uma lista ou um objeto contendo 'dados'.")


def nova_coleta(paginas: int, logger: logging.Logger) -> Path:
    if paginas < 1:
        raise ValueError("O número de páginas deve ser maior que zero.")
    # Reutiliza a função existente; não altera src/api/coleta_dados.py.
    from src.api.coleta_dados import buscar_dados_paginados
    logger.info("Chamando coletor original para até %s página(s)...", paginas)
    dados = buscar_dados_paginados(limite_paginas=paginas)
    if not dados:
        raise RuntimeError("O coletor não retornou registros; carga cancelada.")
    PASTA_BRUTOS.mkdir(parents=True, exist_ok=True)
    instante = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    destino = PASTA_BRUTOS / f"coleta_api_{instante}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Coleta salva em %s (%s registros).", destino, len(dados))
    logger.warning("A quantidade de páginas foi limitada pelo parâmetro --paginas; esta coleta pode ser parcial.")
    return destino


def exportar_csv_seguro(tabela: pd.DataFrame, caminho: Path) -> None:
    """Escapa fórmulas em campos textuais para quem abrir CSV em planilhas."""
    copia = tabela.copy()
    for coluna in copia.columns:
        if coluna in {"valor_orcado", "valor_arrecado_mes", "valor_arrecado_periodo", "ano", "mes", "linha_origem"}:
            continue
        copia[coluna] = copia[coluna].map(
            lambda valor: "'" + valor if isinstance(valor, str) and valor.lstrip().startswith(("=", "+", "-", "@")) else valor
        )
    copia.to_csv(caminho, sep=";", index=False, encoding="utf-8-sig")


def executar(args: argparse.Namespace) -> dict:
    load_dotenv(RAIZ / ".env")
    logger = configurar_logger()
    inicio = datetime.now(timezone.utc)
    id_execucao = inicio.strftime("%Y%m%d_%H%M%S_%f")
    PASTA_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    PASTA_REJEITADOS.mkdir(parents=True, exist_ok=True)
    relatorio = {
        "id_execucao": id_execucao,
        "iniciado_em_utc": inicio.isoformat(),
        "status": "iniciado", "total_bruto": 0, "validos": 0,
        "rejeitados": 0, "duplicados_exatos": 0, "grupos_conflitantes": 0,
        "inseridos": 0, "atualizados": 0, "sem_alteracao": 0,
    }
    relatorio_path = PASTA_PROCESSADOS / f"resumo_etl_{id_execucao}.json"
    try:
        if args.sem_carga and args.criar_tabela:
            raise ValueError("Não use --sem-carga com --criar-tabela.")
        if args.coletar:
            caminho = nova_coleta(args.paginas, logger)
        elif args.arquivo:
            caminho = Path(args.arquivo).expanduser()
            if not caminho.is_absolute():
                caminho = RAIZ / caminho
        else:
            caminho = encontrar_json_mais_recente()
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo JSON não encontrado: {caminho}")

        relatorio["arquivo_origem"] = str(caminho)
        logger.info("Extraindo: %s", caminho)
        registros = ler_json(caminho)
        resultado = limpar_receitas(registros)
        relatorio.update({
            "total_bruto": resultado.total_entrada,
            "validos": len(resultado.validos),
            "rejeitados": len(resultado.rejeitados),
            "duplicados_exatos": resultado.duplicados,
            "grupos_conflitantes": resultado.grupos_conflitantes,
        })
        logger.info(
            "Transformação: entrada=%s, válidos=%s, rejeitados=%s, duplicados=%s, grupos_conflitantes=%s",
            resultado.total_entrada, len(resultado.validos), len(resultado.rejeitados),
            resultado.duplicados, resultado.grupos_conflitantes,
        )
        if resultado.grupos_conflitantes:
            logger.warning("Existem chaves lógicas com valores diferentes; confira os rejeitados.")

        tratados = PASTA_PROCESSADOS / f"receitas_tratadas_{id_execucao}.csv"
        rejeitados = PASTA_REJEITADOS / f"receitas_rejeitadas_{id_execucao}.csv"
        exportar_csv_seguro(resultado.validos, tratados)
        exportar_csv_seguro(resultado.rejeitados, rejeitados)
        relatorio["arquivo_tratado"] = str(tratados)
        relatorio["arquivo_rejeitados"] = str(rejeitados)
        logger.info("CSV tratado: %s", tratados)
        logger.info("CSV de rejeitados: %s", rejeitados)
        if resultado.validos.empty:
            raise RuntimeError("Nenhum registro válido: carga cancelada. Revise o CSV de rejeitados.")

        if args.sem_carga:
            relatorio["carga"] = "ignorada_por_opcao"
            logger.info("Modo --sem-carga: nenhuma alteração no banco.")
        else:
            url = os.getenv("ETL_DATABASE_URL") or os.getenv("DATABASE_URL")
            if not url:
                raise ValueError(
                    "Sem URL de banco. Copie .env.example para .env, configure "
                    "ETL_DATABASE_URL e execute novamente; ou use --sem-carga."
                )
            relatorio["tabela_destino"] = os.getenv("ETL_TABELA", "receitas_sefin_etl")
            esquema = os.getenv("ETL_SCHEMA") or (
                "tributario" if make_url(url).get_backend_name() == "postgresql" else None
            )
            relatorio["esquema_destino"] = esquema
            carga = carregar_receitas(
                resultado.validos,
                url_banco=url,
                origem_arquivo=caminho.name,
                criar_tabela=args.criar_tabela,
                nome_tabela=relatorio["tabela_destino"],
                schema=esquema,
                tamanho_lote=args.lote,
            )
            relatorio.update({
                "inseridos": carga.inseridos,
                "atualizados": carga.atualizados,
                "sem_alteracao": carga.sem_alteracao,
                "carga": "concluida",
            })
            logger.info(
                "Carga concluída: inseridos=%d, atualizados=%d, sem alteração=%d",
                carga.inseridos, carga.atualizados, carga.sem_alteracao,
            )
        relatorio["status"] = "sucesso"
        return relatorio
    except Exception as erro:
        relatorio["status"] = "falha"
        relatorio["erro"] = f"{type(erro).__name__}: {erro}"
        logger.exception("Falha no ETL")
        raise
    finally:
        relatorio["finalizado_em_utc"] = datetime.now(timezone.utc).isoformat()
        relatorio_path.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Relatório da execução: %s | status=%s", relatorio_path, relatorio["status"])


def main() -> int:
    parser = argparse.ArgumentParser(description="ETL de receitas da SEFIN - Sprint E2")
    origem = parser.add_mutually_exclusive_group()
    origem.add_argument("--arquivo", help="Arquivo JSON existente (relativo à raiz do projeto ou absoluto)")
    origem.add_argument("--coletar", action="store_true", help="Executa src/api/coleta_dados.py antes de transformar")
    parser.add_argument("--paginas", type=int, default=3, help="Número de páginas quando usar --coletar (padrão: 3)")
    parser.add_argument("--sem-carga", action="store_true", help="Somente processa, valida e exporta; não acessa o banco")
    parser.add_argument("--criar-tabela", action="store_true", help="Cria explicitamente a tabela de integração, se não existir")
    parser.add_argument("--lote", type=int, default=500, help="Quantidade de registros por lote (padrão: 500)")
    args = parser.parse_args()
    if args.lote < 1:
        parser.error("--lote deve ser maior que zero")
    try:
        executar(args)
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
