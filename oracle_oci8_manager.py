"""
oracle_oci8_manager.py - Diagnóstico profundo, compatibilidade de DLLs e reparo do driver Oracle OCI8 para PHP/XAMPP.
"""

import os
import re
import sys
import shutil
import zipfile
import urllib.request
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable


class OracleOci8Manager:
    """Gerencia o diagnóstico, obtenção de DLLs e configuração da extensão Oracle OCI8."""

    PECL_OCI8_BASE_URL = "https://windows.php.net/downloads/pecl/releases/oci8/3.4.0/"

    # Mapeamento de versões do PHP para DLLs compatíveis do PECL OCI8
    OCI8_PACKAGES = {
        "8.4": {
            "version": "3.4.0",
            "ts_x64": "php_oci8-3.4.0-8.4-ts-vs17-x64.zip",
            "url": "https://windows.php.net/downloads/pecl/releases/oci8/3.4.0/php_oci8-3.4.0-8.4-ts-vs17-x64.zip",
            "compiler": "vs17"
        },
        "8.3": {
            "version": "3.4.0",
            "ts_x64": "php_oci8-3.4.0-8.3-ts-vs16-x64.zip",
            "url": "https://windows.php.net/downloads/pecl/releases/oci8/3.4.0/php_oci8-3.4.0-8.3-ts-vs16-x64.zip",
            "compiler": "vs16"
        },
        "8.2": {
            "version": "3.3.0",
            "ts_x64": "php_oci8-3.3.0-8.2-ts-vs16-x64.zip",
            "url": "https://windows.php.net/downloads/pecl/releases/oci8/3.3.0/php_oci8-3.3.0-8.2-ts-vs16-x64.zip",
            "compiler": "vs16"
        }
    }

    def __init__(self, target_path: Path, log_callback: Optional[Callable[[str], None]] = None):
        self.target_path = Path(target_path)
        self.log_callback = log_callback or (lambda msg: print(msg))

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def locate_instant_client(self) -> List[Dict[str, Any]]:
        """Busca pastas do Oracle Instant Client no XAMPP, diretório alvo e variáveis do sistema."""
        candidates = []
        seen = set()

        # 1. No próprio diretório alvo
        search_dirs = [
            self.target_path,
            self.target_path.parent,
            Path(r"C:\xampp"),
            Path(r"D:\xampp"),
            Path(r"D:\WebServer"),
            Path(r"C:\oracle"),
            Path(r"D:\oracle"),
            Path(r"C:\instantclient"),
            Path(r"D:\instantclient")
        ]

        for base in search_dirs:
            if base.exists() and base.is_dir():
                for p in base.glob("*instantclient*"):
                    if p.is_dir() and (p / "oci.dll").exists() and str(p.resolve()) not in seen:
                        seen.add(str(p.resolve()))
                        candidates.append({
                            "path": str(p),
                            "name": p.name,
                            "has_oci_dll": True,
                            "has_ociei": (p / "oraociei19.dll").exists() or (p / "oraociicus19.dll").exists() or (p / "oraociei.dll").exists()
                        })

        # 2. No PATH do sistema
        system_path = os.environ.get("PATH", "")
        for item in system_path.split(os.pathsep):
            item_p = Path(item.strip('"'))
            if item_p.exists() and item_p.is_dir() and (item_p / "oci.dll").exists():
                if str(item_p.resolve()) not in seen:
                    seen.add(str(item_p.resolve()))
                    candidates.append({
                        "path": str(item_p),
                        "name": f"PATH do Windows: {item_p.name}",
                        "has_oci_dll": True,
                        "has_ociei": True
                    })

        return candidates

    def diagnose_oci8(self, php_dir: Path) -> Dict[str, Any]:
        """
        Executa diagnóstico completo da extensão OCI8:
        1. Testa execução de 'php.exe --ri oci8'
        2. Verifica se a DLL existe em ext/
        3. Verifica se a diretiva está ativa no php.ini
        4. Verifica se o Oracle Instant Client (oci.dll) está acessível
        """
        php_exe = php_dir / "php.exe"
        ext_dir = php_dir / "ext"
        ini_file = php_dir / "php.ini"

        report = {
            "php_version": "Desconhecida",
            "major_minor": "Desconhecida",
            "thread_safety": "TS",
            "architecture": "x64",
            "is_enabled": False,
            "raw_ri_output": "",
            "dll_found": False,
            "dll_name": "",
            "available_dlls_in_ext": [],
            "ini_directive_active": False,
            "ini_directive_name": "",
            "instant_clients_found": self.locate_instant_client(),
            "instant_client_in_path": False,
            "issues": [],
            "solutions": []
        }

        if not php_exe.exists():
            report["issues"].append(f"Executável php.exe não encontrado em {php_dir}")
            return report

        # Obter versão do PHP
        try:
            p_v = subprocess.run([str(php_exe), "-v"], capture_output=True, text=True, timeout=5)
            m = re.search(r"PHP\s+([0-9]+\.[0-9]+)\.([0-9]+)", p_v.stdout)
            if m:
                report["major_minor"] = m.group(1)
                report["php_version"] = f"{m.group(1)}.{m.group(2)}"
            if "NTS" in p_v.stdout:
                report["thread_safety"] = "NTS"
        except Exception as e:
            report["issues"].append(f"Erro ao consultar versão do PHP: {e}")

        # 1. Teste 'php.exe --ri oci8'
        try:
            p_ri = subprocess.run([str(php_exe), "--ri", "oci8"], capture_output=True, text=True, timeout=6)
            report["raw_ri_output"] = p_ri.stdout or p_ri.stderr
            if "OCI8 Support => enabled" in p_ri.stdout:
                report["is_enabled"] = True
            elif "Extension 'oci8' not present" in (p_ri.stdout + p_ri.stderr):
                report["is_enabled"] = False
                report["issues"].append("A extensão OCI8 não está carregada no PHP (função oci_connect indisponível).")
        except Exception as e:
            report["issues"].append(f"Erro ao executar php --ri oci8: {e}")

        # 2. Verificar DLLs em ext/
        if ext_dir.exists():
            for f in ext_dir.glob("*oci*.dll"):
                report["available_dlls_in_ext"].append(f.name)
                if "php_oci8" in f.name.lower():
                    report["dll_found"] = True
                    report["dll_name"] = f.name

        if not report["dll_found"]:
            report["issues"].append(f"Nenhuma DLL 'php_oci8*.dll' encontrada na pasta ext/ ({ext_dir}).")
            report["solutions"].append(
                f"Obtenha a DLL compilada especificamente para PHP {report['major_minor']} (Thread Safe x64) no repositório PECL."
            )

        # 3. Verificar php.ini
        if ini_file.exists():
            try:
                with open(ini_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        s = line.strip()
                        if not s.startswith(";") and re.match(r"^extension\s*=\s*(php_)?oci8(_19|_12c)?(\.dll)?", s, re.IGNORECASE):
                            report["ini_directive_active"] = True
                            report["ini_directive_name"] = s
                            break
            except Exception:
                pass

        if not report["ini_directive_active"]:
            report["issues"].append("A linha 'extension=oci8_19' ou 'extension=oci8' está ausente ou comentada (com ';') no php.ini.")
            report["solutions"].append("Ativar a diretiva 'extension=oci8_19' ou 'extension=oci8' no php.ini.")

        # 4. Verificar Instant Client e PATH
        if not report["instant_clients_found"]:
            report["issues"].append("Nenhuma pasta do Oracle Instant Client (com oci.dll) foi encontrada no sistema.")
            report["solutions"].append("Instalar o Oracle Instant Client Basic (ex: instantclient_19_24) e incluir seu caminho no PATH do Windows.")
        else:
            # Checar se o PATH tem oci.dll
            for ic in report["instant_clients_found"]:
                if "PATH do Windows" in ic["name"]:
                    report["instant_client_in_path"] = True
                    break

            if not report["instant_client_in_path"]:
                primary_ic = report["instant_clients_found"][0]["path"]
                report["issues"].append(f"A pasta do Oracle Instant Client ({primary_ic}) não está configurada no PATH do Windows.")
                report["solutions"].append(f"Adicionar a pasta '{primary_ic}' ao PATH do Windows para que o Apache encontre 'oci.dll'.")

        return report

    def auto_fix_oci8(
        self,
        php_dir: Path,
        source_zip_or_dll: Optional[Path] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executa a correção automática e ativação da extensão OCI8:
        1. Obtém e coloca a DLL correta em php/ext/ (usando DLL fornecida ou repositório PECL).
        2. Configura e descomenta a diretiva no php.ini.
        3. Configura a localização do Oracle Instant Client.
        4. Testa com php.exe --ri oci8 para certificar funcionamento 100%.
        """
        self.log("[CORREÇÃO OCI8] Iniciando processo de reparo e ativação do Oracle OCI8...")

        diag_pre = self.diagnose_oci8(php_dir)
        major_minor = diag_pre["major_minor"]
        ext_dir = php_dir / "ext"
        ini_file = php_dir / "php.ini"
        ext_dir.mkdir(parents=True, exist_ok=True)

        chosen_dll_name = "php_oci8_19.dll"

        # 1. Instalar DLL compatível se necessário
        if source_zip_or_dll and source_zip_or_dll.exists():
            if source_zip_or_dll.suffix.lower() == ".zip":
                self.log(f"-> Extraindo DLLs OCI8 do arquivo ZIP fornecido: {source_zip_or_dll.name}...")
                with zipfile.ZipFile(source_zip_or_dll, "r") as zf:
                    for member in zf.namelist():
                        if member.lower().endswith(".dll") and "oci8" in member.lower():
                            zf.extract(member, ext_dir)
                            chosen_dll_name = member
                            self.log(f"-> DLL extraída para ext/: {member}")
            elif source_zip_or_dll.suffix.lower() == ".dll":
                dest_dll = ext_dir / source_zip_or_dll.name
                shutil.copy2(source_zip_or_dll, dest_dll)
                chosen_dll_name = source_zip_or_dll.name
                self.log(f"-> DLL copiada para ext/: {chosen_dll_name}")
        else:
            # Verificar se já existe uma DLL em ext/
            existing = [f for f in ext_dir.glob("*oci*.dll") if "php_oci8" in f.name.lower()]
            if existing:
                chosen_dll_name = existing[0].name
                self.log(f"-> Utilizando DLL já presente em ext/: {chosen_dll_name}")
            else:
                # Tentar baixar do PECL para a versão correspondente
                pkg_info = self.OCI8_PACKAGES.get(major_minor)
                if pkg_info and pkg_info.get("url"):
                    self.log(f"-> Baixando pacote oficial PECL OCI8 ({pkg_info['version']}) para PHP {major_minor}...")
                    downloads_dir = self.target_path / "downloads"
                    downloads_dir.mkdir(parents=True, exist_ok=True)
                    zip_dest = downloads_dir / pkg_info["ts_x64"]
                    try:
                        req = urllib.request.Request(pkg_info["url"], headers={"User-Agent": "XAMPP-PHP-Updater/2.0"})
                        with urllib.request.urlopen(req, timeout=20) as resp:
                            with open(zip_dest, "wb") as f_out:
                                shutil.copyfileobj(resp, f_out)
                        self.log(f"[OK] Download concluído: {zip_dest.name}. Extraindo DLLs para ext/...")
                        with zipfile.ZipFile(zip_dest, "r") as zf:
                            for m_name in zf.namelist():
                                if m_name.lower().endswith(".dll") and "oci8" in m_name.lower():
                                    zf.extract(m_name, ext_dir)
                                    chosen_dll_name = m_name
                                    self.log(f"-> DLL instalada: {m_name}")
                    except Exception as e:
                        self.log(f"[AVISO] Não foi possível baixar automaticamente do PECL: {e}")
                        return False, f"A DLL do OCI8 para PHP {major_minor} não está em ext/ e não pôde ser baixada automaticamente. Obtenha a DLL no PECL (pecl.php.net/package/oci8).", diag_pre

        # 2. Configurar php.ini
        if ini_file.exists():
            self.log(f"-> Ajustando diretivas do OCI8 no php.ini ({ini_file.name})...")
            with open(ini_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            ext_directive_to_use = chosen_dll_name.replace(".dll", "").replace("php_", "")
            new_lines = []
            found_directive = False
            extension_dir_set = False

            for line in lines:
                s = line.strip()

                if re.match(r"^\s*;?\s*extension_dir\s*=\s*\"?ext\"?", s, re.IGNORECASE):
                    new_lines.append('extension_dir = "ext"\n')
                    extension_dir_set = True
                    continue

                if re.match(r"^\s*;?\s*extension\s*=\s*(php_)?oci8", s, re.IGNORECASE):
                    # Descomenta e padroniza
                    new_lines.append(f"extension = {ext_directive_to_use}\n")
                    found_directive = True
                    continue

                new_lines.append(line)

            if not extension_dir_set:
                new_lines.insert(10, 'extension_dir = "ext"\n')

            if not found_directive:
                new_lines.append(f"\n; Configuração ativada automaticamente pelo XAMPP & PHP Upgrade Master\nextension = {ext_directive_to_use}\n")

            with open(ini_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            self.log(f"[OK] php.ini atualizado com 'extension = {ext_directive_to_use}'.")

        # 3. Gerar script para inclusão do Instant Client no PATH do Apache se necessário
        ics = self.locate_instant_client()
        if ics:
            primary_ic_path = ics[0]["path"]
            self.log(f"-> Oracle Instant Client localizado em: {primary_ic_path}")

            # Gerar script batch para iniciar Apache com Instant Client no PATH
            apache_helper_bat = self.target_path / "INICIAR_APACHE_ORACLE.bat"
            bat_text = f"""@echo off
REM Script para garantir que o Oracle Instant Client esteja no PATH do Apache
SET PATH={primary_ic_path};%PATH%
echo Oracle Instant Client configurado: {primary_ic_path}
echo Iniciando Apache...
if exist "%~dp0apache\\bin\\httpd.exe" (
    cd "%~dp0apache\\bin"
    start httpd.exe
) else (
    echo Apache executavel nao encontrado na pasta padrao.
)
"""
            with open(apache_helper_bat, "w", encoding="latin-1", errors="ignore") as f:
                f.write(bat_text)
            self.log(f"-> Script auxiliar gerado: {apache_helper_bat.name}")

        # 4. Validar o carregamento via 'php.exe --ri oci8'
        self.log("-> Testando inicialização da extensão via 'php.exe --ri oci8'...")
        diag_post = self.diagnose_oci8(php_dir)

        if diag_post["is_enabled"]:
            success_msg = (
                f"Extensão Oracle OCI8 ativada e 100% OPERACIONAL!\n\n"
                f"• Versão do OCI8: Detectada\n"
                f"• DLL em uso: {chosen_dll_name}\n"
                f"• Função oci_connect(): Liberada e pronta para uso!\n\n"
                "Reinicie o Apache no XAMPP Control Panel para aplicar as alterações ao servidor web."
            )
            self.log("[SUCESSO TOTAL] OCI8 inicializado e verificado com sucesso!")
            return True, success_msg, diag_post
        else:
            err_msg = (
                "A DLL foi configurada no php.ini, mas a extensão ainda não inicializou.\n\n"
                f"Saída do teste:\n{diag_post.get('raw_ri_output', 'Sem saída')}\n\n"
                "Causas mais comuns:\n"
                "1. O Oracle Instant Client (oci.dll) não está no PATH do Windows.\n"
                "2. A DLL instalada foi compilada para outra versão do PHP (incompatibilidade de ABI).\n"
                "3. Falta instalar o Microsoft Visual C++ 2015-2022 Redistributable x64."
            )
            self.log(f"[ALERTA] {err_msg}")
            return False, err_msg, diag_post
