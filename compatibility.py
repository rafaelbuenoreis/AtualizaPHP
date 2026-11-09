"""
compatibility.py - Base de conhecimento de versões do PHP, compatibilidade e ciclo de vida.
"""

from typing import Dict, List, Any, Optional

# Ciclo de vida e suporte oficial do PHP (Security / Active / EOL)
PHP_LIFECYCLE: Dict[str, Dict[str, Any]] = {
    "7.0": {"status": "EOL", "eol_date": "2019-01-10", "risk": "CRÍTICO - Sem correções de segurança há anos"},
    "7.1": {"status": "EOL", "eol_date": "2019-12-01", "risk": "CRÍTICO - Sem correções de segurança há anos"},
    "7.2": {"status": "EOL", "eol_date": "2020-11-30", "risk": "CRÍTICO - Sem correções de segurança há anos"},
    "7.3": {"status": "EOL", "eol_date": "2021-12-06", "risk": "CRÍTICO - Sem correções de segurança há anos"},
    "7.4": {"status": "EOL", "eol_date": "2022-11-28", "risk": "CRÍTICO - Versão descontinuada, vulnerável a exploits modernos"},
    "8.0": {"status": "EOL", "eol_date": "2023-11-26", "risk": "ALTO - Versão descontinuada (Fim de vida oficial)"},
    "8.1": {"status": "EOL", "eol_date": "2025-12-31", "risk": "ALTO - Versão descontinuada recentemente"},
    "8.2": {"status": "Security Only", "eol_date": "2026-12-31", "risk": "MÉDIO - Apenas correções críticas de segurança"},
    "8.3": {"status": "Active / Security", "eol_date": "2027-12-31", "risk": "BAIXO - Versão madura e amplamente suportada"},
    "8.4": {"status": "Active (Última Estável)", "eol_date": "2028-12-31", "risk": "MÍNIMO - Versão estável mais recente com novos recursos"}
}

# Principais mudanças e quebras de compatibilidade conhecidas por versão
PHP_VERSION_BREAKING_CHANGES: Dict[str, List[str]] = {
    "8.0": [
        "ext/json agora é compilada nativamente no núcleo (diretiva extension=json removida).",
        "ext/xmlrpc foi descontinuada e removida do núcleo (movida para PECL).",
        "Operador de concatenação '.' tem precedência diferente em expressões aritméticas.",
        "Erros de aviso (Warnings/Notices) internos agora lançam exceções TypeError ou ValueError.",
        "create_function() foi completamente removida.",
        "each() foi completamente removida.",
        "mbstring: diretivas mbstring.func_overload removidas."
    ],
    "8.1": [
        "A função strftime() e gmstrftime() foram descontinuadas (substituir por date() ou IntlDateFormatter).",
        "Retornos de funções internas agora forçam tipos de retorno estritos em interfaces (Return Types).",
        "Passagem de 'null' para parâmetros nativos que não aceitam nulo agora lança aviso de depreciação."
    ],
    "8.2": [
        "Criação dinâmica de propriedades em classes agora é descontinuada (exceto com #[AllowDynamicProperties]).",
        "utf8_encode() e utf8_decode() foram descontinuadas (substituir por mb_convert_encoding()).",
        "Interpolação de string com '${var}' foi descontinuada (usar '{$var}')."
    ],
    "8.3": [
        "Tipagem em constantes de classe (Class Constants Typing) introduzida.",
        "Novas funções nativas como json_validate().",
        "Alterações sutis no tratamento de números com vírgula flutuante e serialização."
    ],
    "8.4": [
        "Property Hooks introduzidos (sintaxe moderna de getters/setters).",
        "Asymmetric Visibility (visibilidade pública para leitura e privada para escrita).",
        r"Novo atributo nativo #[\Deprecated].",
        "ext/imap foi removida do núcleo e movida para o PECL.",
        "ext/pspell foi removida do núcleo.",
        "mysqli_ping() foi removida definitivamente.",
        "Assinaturas de métodos agora requerem compatibilidade estrita com parâmetros nulos tipados."
    ]
}

# Lista de extensões padrão que vêm pré-empacotadas no PHP oficial para Windows
STANDARD_PHP_EXTENSIONS = {
    "php_bz2.dll", "php_curl.dll", "php_dba.dll", "php_enchant.dll", "php_exif.dll",
    "php_fileinfo.dll", "php_ffi.dll", "php_ftp.dll", "php_gd.dll", "php_gettext.dll",
    "php_gmp.dll", "php_intl.dll", "php_imap.dll", "php_ldap.dll", "php_mbstring.dll",
    "php_mysqli.dll", "php_oci8_12c.dll", "php_oci8_19.dll", "php_odbc.dll",
    "php_opcache.dll", "php_openssl.dll", "php_pdo_firebird.dll", "php_pdo_mysql.dll",
    "php_pdo_oci.dll", "php_pdo_odbc.dll", "php_pdo_pgsql.dll", "php_pdo_sqlite.dll",
    "php_pgsql.dll", "php_shmop.dll", "php_snmp.dll", "php_soap.dll", "php_sockets.dll",
    "php_sodium.dll", "php_sqlite3.dll", "php_tidy.dll", "php_xsl.dll", "php_zip.dll"
}

# Conhecimento sobre extensões de terceiros comuns que precisam de DLLs específicas de versão
KNOWN_THIRD_PARTY_EXTENSIONS = {
    "sqlsrv": {
        "name": "Microsoft Drivers for PHP for SQL Server (sqlsrv)",
        "provider": "Microsoft",
        "url": "https://learn.microsoft.com/en-us/sql/connect/php/download-drivers-php-sql-server",
        "notes": "Requer DLL específica para a versão do PHP (ex: php_sqlsrv_83_ts_x64.dll). Não é compatível entre versões maiores sem atualizar a DLL."
    },
    "pdo_sqlsrv": {
        "name": "Microsoft PDO Driver for SQL Server (pdo_sqlsrv)",
        "provider": "Microsoft",
        "url": "https://learn.microsoft.com/en-us/sql/connect/php/download-drivers-php-sql-server",
        "notes": "Requer DLL correspondente ao SQL Server da Microsoft compilada para a versão exata do PHP."
    },
    "xdebug": {
        "name": "Xdebug (Depurador e Profiler)",
        "provider": "Derick Rethans",
        "url": "https://xdebug.org/download",
        "notes": "Requer binário compatível com a versão do PHP e arquitetura (TS x64)."
    },
    "redis": {
        "name": "PhpRedis",
        "provider": "PECL",
        "url": "https://pecl.php.net/package/redis",
        "notes": "Driver de alta performance para Redis. Requer compilação compatível com a versão do PHP."
    },
    "imagick": {
        "name": "ImageMagick (imagick)",
        "provider": "PECL",
        "url": "https://pecl.php.net/package/imagick",
        "notes": "Requer DLL da extensão e binários do ImageMagick correspondentes no PATH."
    },
    "oci8": {
        "name": "Oracle OCI8 / Instant Client",
        "provider": "Oracle / PHP",
        "url": "https://www.oracle.com/database/technologies/instant-client/downloads.html",
        "notes": "Requer Oracle Instant Client configurado no PATH do sistema compatível com x64."
    }
}

# Catálogo offline de versões estáveis para uso caso não haja conexão com a internet
OFFLINE_PHP_CATALOG = [
    {
        "version": "8.4.1",
        "major_minor": "8.4",
        "channel": "Stable",
        "release_date": "2024-11-21",
        "is_latest_stable": True,
        "files": {
            "ts_x64": {
                "filename": "php-8.4.1-Win32-vs17-x64.zip",
                "url": "https://windows.php.net/downloads/releases/php-8.4.1-Win32-vs17-x64.zip",
                "compiler": "vs17",
                "thread_safe": True,
                "arch": "x64"
            },
            "nts_x64": {
                "filename": "php-8.4.1-nts-Win32-vs17-x64.zip",
                "url": "https://windows.php.net/downloads/releases/php-8.4.1-nts-Win32-vs17-x64.zip",
                "compiler": "vs17",
                "thread_safe": False,
                "arch": "x64"
            }
        }
    },
    {
        "version": "8.3.14",
        "major_minor": "8.3",
        "channel": "Stable",
        "release_date": "2024-11-21",
        "is_latest_stable": False,
        "files": {
            "ts_x64": {
                "filename": "php-8.3.14-Win32-vs16-x64.zip",
                "url": "https://windows.php.net/downloads/releases/php-8.3.14-Win32-vs16-x64.zip",
                "compiler": "vs16",
                "thread_safe": True,
                "arch": "x64"
            },
            "nts_x64": {
                "filename": "php-8.3.14-nts-Win32-vs16-x64.zip",
                "url": "https://windows.php.net/downloads/releases/php-8.3.14-nts-Win32-vs16-x64.zip",
                "compiler": "vs16",
                "thread_safe": False,
                "arch": "x64"
            }
        }
    },
    {
        "version": "8.2.26",
        "major_minor": "8.2",
        "channel": "Security Support",
        "release_date": "2024-11-21",
        "is_latest_stable": False,
        "files": {
            "ts_x64": {
                "filename": "php-8.2.26-Win32-vs16-x64.zip",
                "url": "https://windows.php.net/downloads/releases/php-8.2.26-Win32-vs16-x64.zip",
                "compiler": "vs16",
                "thread_safe": True,
                "arch": "x64"
            }
        }
    }
]
