"""
analyzer.py - Analisador de instalações XAMPP e ambientes PHP no Windows.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    import winreg
except ImportError:
    winreg = None

from compatibility import (
    PHP_LIFECYCLE,
    PHP_VERSION_BREAKING_CHANGES,
    STANDARD_PHP_EXTENSIONS,
    KNOWN_THIRD_PARTY_EXTENSIONS,
    OFFLINE_PHP_CATALOG
)


class XamppAnalyzer:
    """Realiza a varredura profunda e auditoria de uma instalação XAMPP/PHP."""

    COMMON_PATHS = [
        r"C:\xampp",
        r"D:\xampp",
        r"E:\xampp",
        r"D:\WebServer",
        r"C:\WebServer",
        r"C:\Program Files\xampp"
    ]

    def __init__(self, target_path: Optional[str] = None):
        self.target_path = Path(target_path) if target_path else self.auto_detect_path()

    @classmethod
    def auto_detect_path(cls) -> Path:
        """Tenta encontrar automaticamente a pasta do XAMPP ou servidor web local."""
        for p in cls.COMMON_PATHS:
            candidate = Path(p)
            if candidate.exists() and (
                (candidate / "php" / "php.exe").exists() or
                (candidate / "php.exe").exists() or
                (candidate / "apache" / "bin" / "httpd.exe").exists()
            ):
                return candidate
        # Fallback para C:\xampp se nenhum for achado
        return Path(r"C:\xampp")

    def get_php_dir(self) -> Optional[Path]:
        """Localiza o diretório do PHP."""
        if not self.target_path or not self.target_path.exists():
            return None
        
        # Pode ser <xampp>/php ou o próprio diretório se o usuário selecionou a pasta php
        if (self.target_path / "php" / "php.exe").exists():
            return self.target_path / "php"
        elif (self.target_path / "php.exe").exists():
            return self.target_path
        elif (self.target_path / "php").is_dir():
            return self.target_path / "php"
        return None

    def get_apache_dir(self) -> Optional[Path]:
        """Localiza o diretório do Apache (se for XAMPP)."""
        if not self.target_path or not self.target_path.exists():
            return None
        candidate = self.target_path / "apache"
        if candidate.exists() and candidate.is_dir():
            return candidate
        # Se selecionou a pasta php diretamente, verifica o diretório pai
        parent_candidate = self.target_path.parent / "apache"
        if parent_candidate.exists() and parent_candidate.is_dir():
            return parent_candidate
        return None

    def get_php_ini_path(self) -> Optional[Path]:
        """Localiza o arquivo php.ini ativo."""
        php_dir = self.get_php_dir()
        if not php_dir:
            return None
        ini = php_dir / "php.ini"
        if ini.exists():
            return ini
        return None

    def get_httpd_xampp_conf_path(self) -> Optional[Path]:
        """Localiza o arquivo httpd-xampp.conf do Apache."""
        apache_dir = self.get_apache_dir()
        if not apache_dir:
            return None
        conf = apache_dir / "conf" / "extra" / "httpd-xampp.conf"
        if conf.exists():
            return conf
        return None

    def check_running_processes(self) -> List[str]:
        """Verifica se há processos do Apache, PHP ou Nginx em execução."""
        running = []
        process_names = ["httpd.exe", "php.exe", "php-cgi.exe", "nginx.exe", "xampp-control.exe"]
        try:
            res = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=1.5
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    line_lower = line.lower()
                    for proc in process_names:
                        if proc in line_lower and proc not in running:
                            running.append(proc)
        except Exception:
            pass
        return running

    def check_vc_redistributable(self) -> Dict[str, Any]:
        """Verifica se o Microsoft Visual C++ 2015-2022 Redistributable (x64) está instalado no Windows."""
        res = {"installed": False, "version": "", "details": "Não detectado no Registro do Windows"}
        if not winreg:
            return res

        keys_to_check = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64")
        ]
        for hkey, subkey in keys_to_check:
            try:
                with winreg.OpenKey(hkey, subkey) as k:
                    v, _ = winreg.QueryValueEx(k, "Version")
                    inst, _ = winreg.QueryValueEx(k, "Installed")
                    if inst == 1:
                        res["installed"] = True
                        res["version"] = str(v)
                        res["details"] = f"Visual C++ 2015-2022 Redistributable ({v}) instalado com sucesso."
                        return res
            except Exception:
                pass

        return res

    def detect_database_clients(self) -> List[Dict[str, str]]:
        """Detecta clients de banco de dados no diretório alvo ou sistema (ex: Oracle Instant Client)."""
        clients = []
        if not self.target_path or not self.target_path.exists():
            return clients

        # Procurar Oracle Instant Client
        for item in self.target_path.glob("*instantclient*"):
            if item.is_dir():
                clients.append({
                    "name": "Oracle Instant Client",
                    "path": str(item),
                    "details": f"Pasta detectada: {item.name}. Compatível com a extensão oci8."
                })
        return clients

    def generate_html_report(self, report_data: Dict[str, Any], output_path: Path) -> Path:
        """Gera um relatório HTML completo, profissional e responsivo para visualização no navegador."""
        cur = report_data.get("current_php", {})
        lat = report_data.get("latest_php", {})
        exts = report_data.get("active_extensions", [])
        dirs = report_data.get("custom_directives", {})
        tps = report_data.get("custom_extensions", [])
        checklist = report_data.get("action_checklist", [])
        notes = report_data.get("compatibility_notes", [])
        vc = report_data.get("vc_redist", {})

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Auditoria e Upgrade PHP - XAMPP</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            line-height: 1.6;
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid #334155;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 25px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
        }}
        .badge-critica {{ background: #991b1b; color: #fecaca; }}
        .badge-recom {{ background: #854d0e; color: #fef08a; }}
        .badge-ok {{ background: #166534; color: #bbf7d0; }}
        .badge-info {{ background: #1e40af; color: #bfdbfe; }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }}
        .card {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 20px;
        }}
        .card h3 {{
            margin-top: 0;
            color: #38bdf8;
            font-size: 16px;
            border-bottom: 1px solid #334155;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 14px;
        }}
        th, td {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid #334155;
        }}
        th {{
            background-color: #0f172a;
            color: #94a3b8;
        }}
        .tag {{
            background: #334155;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
        }}
        .alert-box {{
            background: #1e293b;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 20px;
        }}
        .section-title {{
            color: #38bdf8;
            font-size: 18px;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0; font-size: 24px;">⚡ Relatório de Auditoria e Diagnóstico de Upgrade do PHP</h1>
            <p style="margin: 5px 0 15px 0; color: #94a3b8;">XAMPP & PHP Upgrade Master • Instalação: <code>{report_data.get('target_path')}</code></p>
            <div>
                <span class="badge badge-{'critica' if report_data.get('update_urgency') == 'CRITICA' else ('recom' if report_data.get('update_urgency') == 'RECOMENDADA' else 'ok')}">
                    {report_data.get('urgency_label')}
                </span>
                <span class="badge badge-info" style="margin-left: 10px;">
                    PHP {cur.get('version', 'N/D')} ➔ PHP {lat.get('version', 'N/D')}
                </span>
            </div>
        </div>

        <div class="cards-grid">
            <div class="card">
                <h3>Versão Atual</h3>
                <p><strong>PHP:</strong> {cur.get('version')} ({cur.get('thread_safety', 'TS')} {cur.get('architecture', 'x64')})</p>
                <p><strong>Ciclo de Vida:</strong> {report_data.get('current_lifecycle', {}).get('status')}</p>
                <p><strong>Compilador:</strong> {cur.get('compiler', 'N/D')}</p>
                <p><strong>Caminho:</strong> <code>{report_data.get('php_dir')}</code></p>
            </div>
            <div class="card">
                <h3>Última Versão Estável</h3>
                <p><strong>PHP:</strong> {lat.get('version')} (Thread Safe x64)</p>
                <p><strong>Lançamento:</strong> {lat.get('release_date')}</p>
                <p><strong>Compatibilidade:</strong> 100% Compatível com Apache 2.4</p>
                <p><strong>Origem:</strong> windows.php.net</p>
            </div>
            <div class="card">
                <h3>Ambiente & Dependências</h3>
                <p><strong>Ambiente:</strong> {'XAMPP (Apache + PHP)' if report_data.get('is_xampp') else 'Servidor PHP'}</p>
                <p><strong>Visual C++ x64:</strong> {'✅ Instalado' if vc.get('installed') else '❌ Ausente'}</p>
                <p><strong>Processos Ativos:</strong> {', '.join(report_data.get('running_processes', [])) if report_data.get('running_processes') else 'Nenhum (Liberado)'}</p>
            </div>
        </div>

        <h2 class="section-title">📦 Extensões Ativas a Preservar ({len(exts)})</h2>
        <div class="card">
            <table>
                <thead>
                    <tr><th>#</th><th>Tipo</th><th>Extensão</th><th>Ação no Upgrade</th></tr>
                </thead>
                <tbody>
        """
        for i, ext in enumerate(exts, 1):
            html += f"<tr><td>{i}</td><td><span class='tag'>{ext['type']}</span></td><td><strong>{ext['name']}</strong></td><td>Reativada no novo php.ini</td></tr>\n"

        html += f"""
                </tbody>
            </table>
        </div>

        <h2 class="section-title">⚙️ Parâmetros Customizados do php.ini ({len(dirs)})</h2>
        <div class="card">
            <table>
                <thead>
                    <tr><th>Diretiva</th><th>Valor Configurado Atual</th><th>Tratamento na Migração</th></tr>
                </thead>
                <tbody>
        """
        for k, v in dirs.items():
            html += f"<tr><td><code>{k}</code></td><td><strong>{v}</strong></td><td>Migrado automaticamente</td></tr>\n"

        html += """
                </tbody>
            </table>
        </div>
        """

        if tps:
            html += f"""
            <h2 class="section-title">🧩 DLLs de Terceiros / Customizadas em ext/ ({len(tps)})</h2>
            <div class="card">
                <table>
                    <thead>
                        <tr><th>Arquivo DLL</th><th>Tamanho</th><th>Informações / Recomendações</th></tr>
                    </thead>
                    <tbody>
            """
            for tp in tps:
                notes = tp.get("notes", "DLL externa. Será copiada para a nova instalação.")
                html += f"<tr><td><code>{tp['filename']}</code></td><td>{tp['size_bytes']/1024:.1f} KB</td><td>{notes}</td></tr>\n"
            html += """
                    </tbody>
                </table>
            </div>
            """

        html += """
        <h2 class="section-title">📋 Checklist Automatizado de Atualização</h2>
        <div class="card">
            <ol style="margin: 0; padding-left: 20px;">
        """
        for item in checklist:
            html += f"<li style='margin-bottom: 8px;'>{item}</li>\n"
        html += """
            </ol>
        </div>
        <p style="text-align: center; color: #64748b; font-size: 12px; margin-top: 40px;">
            Gerado por XAMPP & PHP Upgrade Master em tempo de execução.
        </p>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path


    def get_php_binary_info(self, php_exe_path: Path) -> Dict[str, Any]:
        """Executa o php.exe para coletar versão exata, Thread Safety e Arquitetura."""
        info = {
            "version": "Desconhecida",
            "major_minor": "Desconhecida",
            "thread_safety": "TS",  # Padrão seguro para Apache
            "architecture": "x64",
            "compiler": "vs16",
            "build_date": "Desconhecida",
            "raw_output": ""
        }
        if not php_exe_path.exists():
            return info

        try:
            # Executa php -v
            proc = subprocess.run(
                [str(php_exe_path), "-v"],
                capture_output=True,
                text=True,
                timeout=5
            )
            raw = proc.stdout
            info["raw_output"] = raw

            # Extrair versão: ex: PHP 8.3.13 (cli)
            v_match = re.search(r"PHP\s+([0-9]+\.[0-9]+\.[0-9]+)", raw)
            if v_match:
                info["version"] = v_match.group(1)
                parts = info["version"].split(".")
                info["major_minor"] = f"{parts[0]}.{parts[1]}"

            if "NTS" in raw:
                info["thread_safety"] = "NTS"
            else:
                info["thread_safety"] = "TS"

            if "x64" in raw or "Visual C++ 2019 x64" in raw or "64" in raw:
                info["architecture"] = "x64"
            elif "x86" in raw or "32-bit" in raw:
                info["architecture"] = "x86"

            comp_match = re.search(r"(Visual C\+\+\s+[0-9]+|VS[0-9]+)", raw, re.IGNORECASE)
            if comp_match:
                info["compiler"] = comp_match.group(1)

        except Exception as e:
            # Fallback se não conseguir rodar o binário diretamente
            info["raw_output"] = f"Não foi possível executar php.exe diretamente: {str(e)}"
            # Tentar adivinhar pela pasta ou dlls
            php_dir = php_exe_path.parent
            for f in php_dir.glob("php*.dll"):
                if "php8" in f.name:
                    info["major_minor"] = "8.x"
                elif "php7" in f.name:
                    info["major_minor"] = "7.x"

        return info

    def parse_php_ini(self, ini_path: Path) -> Dict[str, Any]:
        """Faz a análise completa do php.ini ativo."""
        active_extensions = []
        commented_extensions = []
        active_directives: Dict[str, str] = {}
        all_lines = []

        if not ini_path.exists():
            return {
                "active_extensions": [],
                "commented_extensions": [],
                "directives": {},
                "extension_dir": "ext"
            }

        try:
            with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
        except Exception:
            return {
                "active_extensions": [],
                "commented_extensions": [],
                "directives": {},
                "extension_dir": "ext"
            }

        ext_pattern = re.compile(r"^\s*(;)?\s*(extension|zend_extension)\s*=\s*(.+)$", re.IGNORECASE)
        directive_pattern = re.compile(r"^\s*([a-zA-Z0-9_\.]+)\s*=\s*(.*?)\s*(?:;.*)?$")

        extension_dir = "ext"

        for line in all_lines:
            s = line.strip()
            if not s:
                continue

            # Checar extensão
            m_ext = ext_pattern.match(s)
            if m_ext:
                is_commented = bool(m_ext.group(1))
                ext_type = m_ext.group(2).lower()
                ext_name = m_ext.group(3).strip().strip('"').strip("'")
                # Limpa comentário na mesma linha se houver
                if ";" in ext_name:
                    ext_name = ext_name.split(";")[0].strip()

                ext_item = {"name": ext_name, "type": ext_type, "raw": s}
                if is_commented:
                    commented_extensions.append(ext_item)
                else:
                    active_extensions.append(ext_item)
                continue

            # Checar diretiva de configuração
            if not s.startswith(";"):
                m_dir = directive_pattern.match(s)
                if m_dir:
                    key = m_dir.group(1).strip()
                    val = m_dir.group(2).strip().strip('"').strip("'")
                    active_directives[key] = val
                    if key.lower() == "extension_dir":
                        extension_dir = val

        return {
            "active_extensions": active_extensions,
            "commented_extensions": commented_extensions,
            "directives": active_directives,
            "extension_dir": extension_dir
        }

    def scan_ext_directory(self, php_dir: Path) -> Dict[str, Any]:
        """Examina a pasta ext/ para detectar DLLs instaladas e identificar DLLs customizadas/terceiros."""
        ext_path = php_dir / "ext"
        if not ext_path.exists():
            return {"dlls": [], "third_party": [], "standard": []}

        all_dlls = []
        third_party = []
        standard = []

        for f in ext_path.glob("*.dll"):
            dll_name = f.name.lower()
            all_dlls.append(f.name)
            if dll_name in STANDARD_PHP_EXTENSIONS:
                standard.append(f.name)
            else:
                # DLL customizada ou de terceiros (ex: sqlsrv, oci8 personalizada, xdebug)
                tp_info = {"filename": f.name, "size_bytes": f.stat().st_size}
                # Tenta casar com terceiros conhecidos
                for key, meta in KNOWN_THIRD_PARTY_EXTENSIONS.items():
                    if key in dll_name:
                        tp_info["known_name"] = meta["name"]
                        tp_info["provider"] = meta["provider"]
                        tp_info["url"] = meta["url"]
                        tp_info["notes"] = meta["notes"]
                        break
                third_party.append(tp_info)

        return {
            "dlls": all_dlls,
            "third_party": third_party,
            "standard": standard
        }

    def parse_httpd_xampp(self, conf_path: Path) -> Dict[str, Any]:
        """Lê a integração do Apache com o PHP em httpd-xampp.conf."""
        info = {
            "has_apache_conf": False,
            "php_module": None,
            "php_module_dll": None,
            "php_ini_dir": None,
            "load_files": [],
            "raw_lines": []
        }
        if not conf_path.exists():
            return info

        info["has_apache_conf"] = True
        try:
            with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                info["raw_lines"] = lines
                for line in lines:
                    s = line.strip()
                    if s.startswith("#") or not s:
                        continue
                    if s.lower().startswith("loadmodule") and "php" in s.lower():
                        parts = s.split()
                        if len(parts) >= 3:
                            info["php_module"] = parts[1]
                            info["php_module_dll"] = parts[2].strip('"')
                    elif s.lower().startswith("loadfile") and "php" in s.lower():
                        parts = s.split()
                        if len(parts) >= 2:
                            info["load_files"].append(parts[1].strip('"'))
                    elif s.lower().startswith("phpinidir"):
                        parts = s.split(maxsplit=1)
                        if len(parts) >= 2:
                            info["php_ini_dir"] = parts[1].strip('"')
        except Exception:
            pass

        return info

    def perform_full_analysis(self) -> Dict[str, Any]:
        """Executa a análise completa e retorna um relatório estruturado para a UI."""
        report: Dict[str, Any] = {
            "target_path": str(self.target_path) if self.target_path else "",
            "is_valid_installation": False,
            "is_xampp": False,
            "php_dir": "",
            "apache_dir": "",
            "running_processes": self.check_running_processes(),
            "current_php": {},
            "latest_php": OFFLINE_PHP_CATALOG[0],  # Versão estável mais recente
            "needs_update": False,
            "update_urgency": "INFO",  # OK, INFO, RECOMENDADA, CRÍTICA
            "urgency_label": "Verificação Pendente",
            "php_ini_path": "",
            "active_extensions": [],
            "custom_extensions": [],
            "custom_directives": {},
            "apache_integration": {},
            "compatibility_notes": [],
            "action_checklist": [],
            "errors": []
        }

        php_dir = self.get_php_dir()
        if not php_dir or not (php_dir / "php.exe").exists():
            report["errors"].append("Nenhum binário php.exe encontrado no caminho selecionado.")
            return report

        report["is_valid_installation"] = True
        report["php_dir"] = str(php_dir)

        apache_dir = self.get_apache_dir()
        if apache_dir and (apache_dir / "bin" / "httpd.exe").exists():
            report["is_xampp"] = True
            report["apache_dir"] = str(apache_dir)

        # Informações do binário PHP atual
        php_info = self.get_php_binary_info(php_dir / "php.exe")
        report["current_php"] = php_info

        # Análise do php.ini
        ini_path = self.get_php_ini_path()
        if ini_path:
            report["php_ini_path"] = str(ini_path)
            ini_data = self.parse_php_ini(ini_path)
            report["active_extensions"] = ini_data["active_extensions"]
            report["commented_extensions"] = ini_data["commented_extensions"]

            # Identificar diretivas alteradas ou críticas
            critical_keys = [
                "memory_limit", "upload_max_filesize", "post_max_size",
                "max_execution_time", "max_input_time", "max_input_vars",
                "date.timezone", "error_reporting", "display_errors",
                "curl.cainfo", "openssl.cafile", "session.save_path"
            ]
            custom_dirs = {}
            for k in critical_keys:
                if k in ini_data["directives"]:
                    custom_dirs[k] = ini_data["directives"][k]
            report["custom_directives"] = custom_dirs

        # Varredura da pasta ext/
        ext_scan = self.scan_ext_directory(php_dir)
        report["custom_extensions"] = ext_scan["third_party"]
        report["all_installed_ext_dlls"] = ext_scan["dlls"]

        # Análise do Apache
        conf_path = self.get_httpd_xampp_conf_path()
        if conf_path:
            report["apache_integration"] = self.parse_httpd_xampp(conf_path)

        # Checar Visual C++ Redistributable e Clients de Banco
        report["vc_redist"] = self.check_vc_redistributable()
        report["db_clients"] = self.detect_database_clients()

        # Avaliação de Necessidade de Atualização
        current_ver = php_info.get("version", "0.0.0")
        current_mm = php_info.get("major_minor", "0.0")
        latest_ver = report["latest_php"]["version"]
        latest_mm = report["latest_php"]["major_minor"]

        # Ciclo de vida da versão atual
        lifecycle = PHP_LIFECYCLE.get(current_mm, {"status": "Desconhecido", "risk": "Desconhecido"})
        report["current_lifecycle"] = lifecycle

        if current_ver == latest_ver:
            report["needs_update"] = False
            report["update_urgency"] = "OK"
            report["urgency_label"] = "PHP Atualizado (Última Versão Estável)"
        elif lifecycle.get("status") == "EOL":
            report["needs_update"] = True
            report["update_urgency"] = "CRITICA"
            report["urgency_label"] = f"CRÍTICO - Versão {current_mm} Descontinuada (EOL). Atualização Obrigatória!"
        elif current_mm != latest_mm:
            report["needs_update"] = True
            report["update_urgency"] = "RECOMENDADA"
            report["urgency_label"] = f"Atualização Recomendada: {current_ver} -> {latest_ver} (Novos recursos e performance)"
        else:
            # Mesma versão minor, apenas patch desatualizado
            report["needs_update"] = True
            report["update_urgency"] = "INFO"
            report["urgency_label"] = f"Patch de Segurança Disponível: {current_ver} -> {latest_ver}"

        # Compilar notas de compatibilidade para o salto de versão
        comp_notes = []
        for ver, changes in PHP_VERSION_BREAKING_CHANGES.items():
            try:
                if float(ver) > float(current_mm):
                    comp_notes.append({
                        "version": ver,
                        "changes": changes
                    })
            except Exception:
                pass
        report["compatibility_notes"] = comp_notes

        # Gerar Checklist de Ação Detalhado
        checklist = [
            f"Fazer Backup Integral da pasta atual do PHP ({php_dir}) e arquivo de configuração do Apache.",
            f"Baixar a versão estável compatível do PHP ({latest_ver} Thread Safe x64 para Apache do XAMPP).",
            f"Descompactar os novos arquivos mantendo a estrutura de diretórios do XAMPP.",
            f"Migrar automaticamente as {len(report['active_extensions'])} extensões ativas para o novo php.ini.",
            f"Preservar as configurações personalizadas de memória ({report['custom_directives'].get('memory_limit', 'padrão')}), upload ({report['custom_directives'].get('upload_max_filesize', 'padrão')}) e timezone.",
        ]
        if report["custom_extensions"]:
            checklist.append(
                f"ATENÇÃO: Foram encontradas {len(report['custom_extensions'])} DLLs de terceiros (ex: {[x['filename'] for x in report['custom_extensions']]}). "
                "Estas DLLs serão migradas, mas drivers específicos de banco (como SQL Server ou Oracle) podem precisar de DLLs compiladas para o novo PHP."
            )
        if report["apache_integration"].get("has_apache_conf"):
            checklist.append("Ajustar o httpd-xampp.conf do Apache para carregar o módulo php_module e php8apache2_4.dll da nova versão.")

        checklist.append("Executar teste de integridade sintática (php -v e php -m) antes de reiniciar os serviços.")

        report["action_checklist"] = checklist

        return report
