"""
log_cleaner.py - Motor de limpeza, rotação mensal e compactação de logs do Apache / XAMPP.
"""

import os
import re
import sys
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

# Padrões regex para detecção de datas em logs do Apache, PHP e Nginx
# 1. Apache Access Log / Combined: [10/Oct/2024:13:55:36 -0300]
REGEX_APACHE_ACCESS = re.compile(r"\[(\d{1,2})/([A-Za-z]{3})/(\d{4}):\d{2}:\d{2}:\d{2}")

# 2. Apache Error Log 2.4: [Wed Oct 09 09:48:00.123456 2024] ou [Thu Sep 10 14:22:10 2026]
REGEX_APACHE_ERROR = re.compile(r"\[[A-Za-z]{3}\s+([A-Za-z]{3})\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+(\d{4})\]")

# 3. Nginx / ISO / Standard: 2024/10/23 15:40:12 ou 2024-10-23 15:40:12
REGEX_ISO_DATE = re.compile(r"^(?:\[)?(\d{4})[/-](\d{1,2})[/-]\d{1,2}")

# 4. PHP Error Log: [09-Oct-2024 15:40:12 UTC]
REGEX_PHP_ERROR = re.compile(r"\[(\d{1,2})-([A-Za-z]{3})-(\d{4})\s+\d{2}:\d{2}:\d{2}")


class ApacheLogCleaner:
    """Gerencia a auditoria, divisão mensal, limpeza e compactação de arquivos de log do Apache."""

    def __init__(self, target_base_path: Path, log_callback: Optional[Callable[[str], None]] = None):
        self.target_base_path = Path(target_base_path)
        self.log_callback = log_callback or (lambda msg: print(msg))

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

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

        # Ordena por tamanho decrescente
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
        Extrai o ano e mês de uma linha de log nos formatos Apache/PHP/Nginx.
        Retorna string no formato 'YYYY-MM' (ex: '2024-10', '2026-09') ou None.
        """
        # 1. Apache Access: [10/Oct/2024:...]
        m = REGEX_APACHE_ACCESS.search(line)
        if m:
            month_str = m.group(2).lower()
            year_str = m.group(3)
            mm = MONTH_MAP.get(month_str, "01")
            return f"{year_str}-{mm}"

        # 2. Apache Error: [Wed Oct 09 09:48:00 2024]
        m = REGEX_APACHE_ERROR.search(line)
        if m:
            month_str = m.group(1).lower()
            year_str = m.group(2)
            mm = MONTH_MAP.get(month_str, "01")
            return f"{year_str}-{mm}"

        # 3. Nginx / ISO: 2024/10/23 ou 2024-10-23
        m = REGEX_ISO_DATE.search(line)
        if m:
            year_str = m.group(1)
            mm = f"{int(m.group(2)):02d}"
            return f"{year_str}-{mm}"

        # 4. PHP Error: [09-Oct-2024 15:40:12 UTC]
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
        Executa o pipeline completo solicitado:
        1. Carrega o arquivo de log original linha a linha (streaming).
        2. Separa por vários arquivos por meses (ex: access_2024-10.log, access_2026-09.log).
        3. Esvazia/trunca o arquivo original para zerar o espaço e manter o servidor rodando.
        4. Compacta em .zip os arquivos gerados de meses anteriores a 09/2026 (ou threshold_ym).
        5. Remove os arquivos .log intermediários compactados para economizar espaço em disco.
        """
        log_file_path = Path(log_file_path)
        if not log_file_path.exists() or not log_file_path.is_file():
            raise FileNotFoundError(f"Arquivo de log não encontrado: {log_file_path}")

        # Diretório de destino para os arquivos separados e compactados
        if not output_dir:
            output_dir = log_file_path.parent / "archived_logs"
        output_dir.mkdir(parents=True, exist_ok=True)

        base_stem = log_file_path.stem  # ex: access ou error
        total_size = log_file_path.stat().st_size

        self.log(f"[LOG PROCESSOR] Iniciando processamento de {log_file_path.name} ({self.format_bytes(total_size)})...")
        self.log(f"-> Diretório de arquivamento: {output_dir}")
        self.log(f"-> Meses anteriores a '{compression_threshold_ym}' serão compactados em .ZIP.")

        # Dicionário de handles de arquivos abertos por mês
        month_files: Dict[str, Any] = {}
        month_counts: Dict[str, int] = {}

        last_known_ym = datetime.now().strftime("%Y-%m")
        bytes_read = 0
        lines_count = 0

        try:
            with open(log_file_path, "r", encoding="utf-8", errors="replace") as infile:
                for line in infile:
                    lines_count += 1
                    bytes_read += len(line.encode("utf-8", errors="replace"))

                    # Identificar mês
                    ym = self.extract_year_month(line)
                    if ym:
                        last_known_ym = ym
                    else:
                        # Linhas secundárias (ex: stack trace ou continuações) herdam o mês da linha anterior
                        ym = last_known_ym

                    # Abrir arquivo de destino do mês sob demanda
                    if ym not in month_files:
                        dest_file_path = output_dir / f"{base_stem}_{ym}.log"
                        # Abre em modo append
                        month_files[ym] = open(dest_file_path, "a", encoding="utf-8", errors="replace")
                        month_counts[ym] = 0

                    month_files[ym].write(line)
                    month_counts[ym] += 1

                    if progress_callback and lines_count % 1000 == 0 and total_size > 0:
                        prog = min(0.7, (bytes_read / total_size) * 0.7)
                        progress_callback(prog, lines_count, f"Lendo logs ({lines_count:,} linhas)...")

        finally:
            # Fechar todos os arquivos mensais
            for ym, f_handle in month_files.items():
                f_handle.close()

        self.log(f"[OK] Leitura concluída: {lines_count:,} linhas distribuídas em {len(month_files)} meses:")
        for ym in sorted(month_files.keys()):
            self.log(f"   • Mês {ym}: {month_counts[ym]:,} linhas gravadas em {base_stem}_{ym}.log")

        # 3. Remover do arquivo original (Truncar com segurança)
        if truncate_original:
            self.log(f"[TRUNCAR] Limpando arquivo original '{log_file_path.name}'...")
            try:
                with open(log_file_path, "w", encoding="utf-8") as f_trunc:
                    f_trunc.truncate(0)
                self.log(f"[OK] Arquivo original '{log_file_path.name}' limpo com sucesso (0 bytes).")
            except Exception as e:
                self.log(f"[AVISO] Não foi possível truncar diretamente '{log_file_path.name}': {e}. Tentando cópia e substituição.")
                try:
                    # Alternativa se estiver travado
                    temp_empty = log_file_path.parent / f"{log_file_path.name}.empty"
                    temp_empty.touch()
                    os.replace(temp_empty, log_file_path)
                except Exception as ex2:
                    self.log(f"[ERRO AO LIMPAR ARQUIVO ORIGINAL] {ex2}")

        # 4. Compactar arquivos de meses anteriores ao threshold (09/2026)
        if progress_callback:
            progress_callback(0.8, lines_count, "Compactando meses anteriores em .ZIP...")

        compressed_files = []
        kept_uncompressed = []

        self.log(f"[COMPACTAÇÃO] Analisando meses para compactação (limite: < {compression_threshold_ym})...")

        for ym in sorted(month_files.keys()):
            dest_log = output_dir / f"{base_stem}_{ym}.log"
            if not dest_log.exists():
                continue

            # Comparação lexicográfica válida para YYYY-MM (ex: '2024-10' < '2026-09')
            if ym < compression_threshold_ym:
                zip_path = output_dir / f"{base_stem}_{ym}.zip"
                self.log(f"-> Compactando mês {ym} (< {compression_threshold_ym}) em {zip_path.name}...")

                try:
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(dest_log, arcname=dest_log.name)

                    # Remover arquivo .log descompactado para liberar espaço
                    dest_log.unlink()
                    compressed_files.append({
                        "month": ym,
                        "zip_path": str(zip_path),
                        "zip_size": zip_path.stat().st_size
                    })
                    self.log(f"   [OK] {zip_path.name} gerado ({self.format_bytes(zip_path.stat().st_size)}). Arquivo .log original do mês removido.")
                except Exception as e:
                    self.log(f"   [ERRO AO COMPACTAR {dest_log.name}] {e}")
            else:
                kept_uncompressed.append({
                    "month": ym,
                    "log_path": str(dest_log),
                    "size": dest_log.stat().st_size
                })
                self.log(f"-> Mês {ym} mantido descompactado (>= {compression_threshold_ym}).")

        if progress_callback:
            progress_callback(1.0, lines_count, "Limpeza e arquivamento concluídos!")

        result_summary = {
            "original_file": str(log_file_path),
            "original_size": total_size,
            "lines_processed": lines_count,
            "output_directory": str(output_dir),
            "month_counts": month_counts,
            "compressed_zips": compressed_files,
            "kept_uncompressed": kept_uncompressed,
            "truncated": truncate_original
        }

        self.log("[SUCESSO TOTAL] Operação de limpeza de logs finalizada com êxito!")
        return result_summary
