"""
log_cleaner.py - Motor de limpeza criteriosa, rotação mensal e compactação de logs do Apache / XAMPP.
"""

import os
import re
import sys
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable

# Mapeamento de abreviações de meses em inglês para números
MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12"
}

# 1. Apache Access Log / Combined: [10/Oct/2024:13:55:36 -0300]
REGEX_APACHE_ACCESS = re.compile(r"\[(\d{1,2})/([A-Za-z]{3})/(\d{4}):\d{2}:\d{2}:\d{2}")

# 2. Apache Error Log 2.4: [Wed Oct 09 09:48:00.123456 2024] ou [Thu Sep 10 14:22:10 2026]
REGEX_APACHE_ERROR = re.compile(r"\[[A-Za-z]{3}\s+([A-Za-z]{3})\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+(\d{4})\]")

# 3. Nginx / ISO: 2024/10/23 15:40:12 ou 2024-10-23 15:40:12
REGEX_ISO_DATE = re.compile(r"^(?:\[)?(\d{4})[/-](\d{1,2})[/-]\d{1,2}")

# 4. PHP Error Log: [09-Oct-2024 15:40:12 UTC]
REGEX_PHP_ERROR = re.compile(r"\[(\d{1,2})-([A-Za-z]{3})-(\d{4})\s+\d{2}:\d{2}:\d{2}")


class ApacheLogCleaner:
    """
    Gerencia a auditoria, divisão mensal, remoção seletiva respeitando o mês informado
    e compactação em .ZIP dos logs anteriores ao mês de corte.
    """

    def __init__(self, target_base_path: Path, log_callback: Optional[Callable[[str], None]] = None):
        self.target_base_path = Path(target_base_path)
        self.log_callback = log_callback or (lambda msg: print(msg))

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    @staticmethod
    def parse_threshold_month(raw_input: str) -> str:
        """
        Normaliza formatos de entrada do usuário como '09/2026', '9/2026', '2026-09', '09-2026'
        para a chave padronizada 'YYYY-MM' (ex: '2026-09').
        """
        s = raw_input.strip()
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 2:
                p1, p2 = parts[0].strip(), parts[1].strip()
                if len(p1) <= 2 and len(p2) == 4:
                    return f"{p2}-{int(p1):02d}"
                elif len(p1) == 4 and len(p2) <= 2:
                    return f"{p1}-{int(p2):02d}"
        elif "-" in s:
            parts = s.split("-")
            if len(parts) == 2:
                p1, p2 = parts[0].strip(), parts[1].strip()
                if len(p1) <= 2 and len(p2) == 4:
                    return f"{p2}-{int(p1):02d}"
                elif len(p1) == 4 and len(p2) <= 2:
                    return f"{p1}-{int(p2):02d}"
        return "2026-09"

    def locate_log_files(self) -> List[Dict[str, Any]]:
        """Localiza todos os arquivos de log no Apache (apache/logs) ou Nginx/WebServer."""
        log_files = []
        candidate_dirs = [
            self.target_base_path / "apache" / "logs",
            self.target_base_path / "logs",
            self.target_base_path / "nginx" / "logs",
            self.target_base_path
        ]

        seen_paths = set()

        for d in candidate_dirs:
            if d.exists() and d.is_dir():
                for f in d.glob("*.log"):
                    if f.is_file() and f.resolve() not in seen_paths:
                        seen_paths.add(f.resolve())
                        size_b = f.stat().st_size
                        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                        log_files.append({
                            "path": str(f),
                            "name": f.name,
                            "size_bytes": size_b,
                            "size_formatted": self.format_bytes(size_b),
                            "last_modified": mtime,
                            "directory": str(d)
                        })

        log_files.sort(key=lambda x: x["size_bytes"], reverse=True)
        return log_files

    @staticmethod
    def format_bytes(size: int) -> str:
        """Formata tamanho de bytes para KB, MB, GB."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024*1024):.2f} MB"
        else:
            return f"{size / (1024*1024*1024):.2f} GB"

    @classmethod
    def extract_year_month(cls, line: str) -> Optional[str]:
        """
        Extrai o ano e mês de uma linha de log.
        Retorna string 'YYYY-MM' (ex: '2024-10', '2026-09') ou None.
        """
        m = REGEX_APACHE_ACCESS.search(line)
        if m:
            month_str = m.group(2).lower()
            year_str = m.group(3)
            mm = MONTH_MAP.get(month_str, "01")
            return f"{year_str}-{mm}"

        m = REGEX_APACHE_ERROR.search(line)
        if m:
            month_str = m.group(1).lower()
            year_str = m.group(2)
            mm = MONTH_MAP.get(month_str, "01")
            return f"{year_str}-{mm}"

        m = REGEX_ISO_DATE.search(line)
        if m:
            year_str = m.group(1)
            mm = f"{int(m.group(2)):02d}"
            return f"{year_str}-{mm}"

        m = REGEX_PHP_ERROR.search(line)
        if m:
            month_str = m.group(2).lower()
            year_str = m.group(3)
            mm = MONTH_MAP.get(month_str, "01")
            return f"{year_str}-{mm}"

        return None

    def process_and_clean_log(
        self,
        log_file_path: Path,
        output_dir: Optional[Path] = None,
        truncate_original: bool = True,
        compression_threshold_ym: str = "2026-09",
        progress_callback: Optional[Callable[[float, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executa o pipeline criterioso respeitando o mês informado:
        1. Lê o arquivo original linha a linha (streaming).
        2. Separa TODOS os registros em arquivos mensais dedicados (<log>_YYYY-MM.log).
        3. REMOÇÃO NO ARQUIVO ORIGINAL RESPEITANDO O MÊS INFORMADO:
           - Remove do arquivo original APENAS as linhas de meses ANTERIORES ao mês informado (< compression_threshold_ym).
           - PRESERVA no arquivo original todas as linhas do mês informado e posteriores (>= compression_threshold_ym).
        4. COMPACTAÇÃO EM .ZIP:
           - Compacta em .ZIP os arquivos mensais de meses anteriores ao limite (< compression_threshold_ym).
           - Exclui o .log intermediário compactado.
           - Mantém os arquivos de log mensais a partir do mês informado descompactados.
        """
        log_file_path = Path(log_file_path)
        if not log_file_path.exists() or not log_file_path.is_file():
            raise FileNotFoundError(f"Arquivo de log não encontrado: {log_file_path}")

        # Normaliza o mês de corte (ex: '09/2026' -> '2026-09')
        cutoff_ym = self.parse_threshold_month(compression_threshold_ym)

        if not output_dir:
            output_dir = log_file_path.parent / "archived_logs"
        output_dir.mkdir(parents=True, exist_ok=True)

        base_stem = log_file_path.stem
        total_size = log_file_path.stat().st_size

        self.log(f"[LOG PROCESSOR] Processando {log_file_path.name} ({self.format_bytes(total_size)})...")
        self.log(f"-> Mês de referência informado: {cutoff_ym} (Remover do original logs < {cutoff_ym}; Manter logs >= {cutoff_ym}).")
        self.log(f"-> Pasta de arquivamento: {output_dir}")

        month_files: Dict[str, Any] = {}
        month_counts: Dict[str, int] = {}

        # Arquivo temporário para acumular as linhas recentes que PERMANECERÃO no arquivo original
        temp_recent_file = output_dir / f"{base_stem}_recent_temp_{datetime.now().strftime('%H%M%S')}.tmp"
        f_recent = open(temp_recent_file, "w", encoding="utf-8", errors="replace")

        last_known_ym = datetime.now().strftime("%Y-%m")
        lines_count = 0
        lines_removed_old = 0
        lines_kept_recent = 0
        bytes_read = 0

        try:
            with open(log_file_path, "r", encoding="utf-8", errors="replace") as infile:
                for line in infile:
                    lines_count += 1
                    bytes_read += len(line.encode("utf-8", errors="replace"))

                    ym = self.extract_year_month(line)
                    if ym:
                        last_known_ym = ym
                    else:
                        ym = last_known_ym

                    # Gravar no arquivo mensal correspondente
                    if ym not in month_files:
                        dest_file_path = output_dir / f"{base_stem}_{ym}.log"
                        month_files[ym] = open(dest_file_path, "a", encoding="utf-8", errors="replace")
                        month_counts[ym] = 0

                    month_files[ym].write(line)
                    month_counts[ym] += 1

                    # Decisão de remoção do arquivo original respeitando o mês informado:
                    if ym < cutoff_ym:
                        # Linha antiga: será REMOVIDA do arquivo original (não é gravada em temp_recent)
                        lines_removed_old += 1
                    else:
                        # Linha recente (>= mês informado): PRESERVADA no arquivo original
                        f_recent.write(line)
                        lines_kept_recent += 1

                    if progress_callback and lines_count % 1000 == 0 and total_size > 0:
                        prog = min(0.65, (bytes_read / total_size) * 0.65)
                        progress_callback(prog, lines_count, f"Processando logs ({lines_count:,} linhas)...")

        finally:
            for ym, f_handle in month_files.items():
                f_handle.close()
            f_recent.close()

        self.log(f"[OK] Leitura concluída: {lines_count:,} linhas processadas.")
        self.log(f"   • Linhas anteriores a {cutoff_ym} (removidas do original): {lines_removed_old:,}")
        self.log(f"   • Linhas recentes a partir de {cutoff_ym} (mantidas no original): {lines_kept_recent:,}")

        # 3. Atualizar o arquivo Original (Removendo apenas as linhas antigas < cutoff_ym)
        if truncate_original:
            self.log(f"[REMOÇÃO RESPEITANDO O MÊS {cutoff_ym}] Atualizando arquivo original '{log_file_path.name}'...")
            try:
                # Copiar o conteúdo recente para o arquivo original
                with open(temp_recent_file, "r", encoding="utf-8", errors="replace") as f_src:
                    with open(log_file_path, "w", encoding="utf-8") as f_dst:
                        shutil.copyfileobj(f_src, f_dst)

                new_size = log_file_path.stat().st_size
                freed_bytes = max(0, total_size - new_size)
                self.log(f"[OK] Arquivo original atualizado: {lines_kept_recent:,} linhas mantidas ({self.format_bytes(new_size)}). Liberados {self.format_bytes(freed_bytes)}.")
            except Exception as e:
                self.log(f"[AVISO NA ATUALIZAÇÃO DO ORIGINAL] {e}. Tentando método alternativo...")
                try:
                    shutil.copy2(temp_recent_file, log_file_path)
                except Exception as ex2:
                    self.log(f"[ERRO CRÍTICO AO ATUALIZAR ARQUIVO ORIGINAL] {ex2}")
            finally:
                if temp_recent_file.exists():
                    temp_recent_file.unlink()

        # 4. Compactar em .ZIP arquivos mensais de meses anteriores ao corte (< cutoff_ym)
        if progress_callback:
            progress_callback(0.8, lines_count, f"Compactando arquivos anteriores a {cutoff_ym} em .ZIP...")

        compressed_files = []
        kept_uncompressed = []

        self.log(f"[COMPACTAÇÃO] Compactando arquivos de meses anteriores a '{cutoff_ym}' em .ZIP...")

        for ym in sorted(month_files.keys()):
            dest_log = output_dir / f"{base_stem}_{ym}.log"
            if not dest_log.exists():
                continue

            if ym < cutoff_ym:
                zip_path = output_dir / f"{base_stem}_{ym}.zip"
                self.log(f"-> Compactando mês antigo {ym} (< {cutoff_ym}) em {zip_path.name}...")
                try:
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(dest_log, arcname=dest_log.name)

                    dest_log.unlink()
                    compressed_files.append({
                        "month": ym,
                        "zip_path": str(zip_path),
                        "zip_size": zip_path.stat().st_size
                    })
                    self.log(f"   [OK] {zip_path.name} gerado ({self.format_bytes(zip_path.stat().st_size)}).")
                except Exception as e:
                    self.log(f"   [ERRO AO COMPACTAR {dest_log.name}] {e}")
            else:
                kept_uncompressed.append({
                    "month": ym,
                    "log_path": str(dest_log),
                    "size": dest_log.stat().st_size
                })
                self.log(f"-> Mês {ym} mantido descompactado em arquivo .log (>= {cutoff_ym}).")

        if progress_callback:
            progress_callback(1.0, lines_count, "Operação de limpeza concluída!")

        return {
            "original_file": str(log_file_path),
            "original_size": total_size,
            "new_size": log_file_path.stat().st_size,
            "lines_processed": lines_count,
            "lines_removed_old": lines_removed_old,
            "lines_kept_recent": lines_kept_recent,
            "cutoff_month": cutoff_ym,
            "output_directory": str(output_dir),
            "month_counts": month_counts,
            "compressed_zips": compressed_files,
            "kept_uncompressed": kept_uncompressed
        }
