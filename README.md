# ⚡ XAMPP & PHP Upgrade Master

Aplicação desktop com **Interface Gráfica Moderna (CustomTkinter)** e **Executável Standalone (.EXE)** desenvolvida para:
1. **Auditar e atualizar o PHP no XAMPP** com 100% de segurança, tolerância zero a perdas e reversão garantida.
2. **Diagnosticar e Reparar o Driver Oracle (OCI8 / `oci_connect()`)** resolvendo incompatibilidades de ABI de DLLs e configurando o Oracle Instant Client.
3. **Limpar, rotacionar e compactar logs do Apache** automaticamente com separação mensal, remoção seletiva respeitando o mês informado e arquivamento em `.ZIP`.

---

## 🚀 Como Executar

### Opção 1: Pelo Executável Standalone (Recomendado)
Basta dar dois cliques no arquivo:
👉 **[`XamppPhpUpgradeMaster.exe`](file:///d:/rafael/AtualizaPHP/XamppPhpUpgradeMaster.exe)**

*(Não requer Python instalado na máquina de destino).*

### Opção 2: Pelo script batch ou terminal
```cmd
run_gui.bat
```
ou
```powershell
python main.py
```

---

## 🎯 Principais Recursos

### 1. 🩺 Diagnóstico & Reparo do Driver Oracle OCI8 (`oci_connect()`) (NOVO)
- **Problema Solucionado:** Ao atualizar o PHP (ex: do 8.2 para 8.4/8.5), funções de banco Oracle como `oci_connect()` param de funcionar se a DLL OCI8 não for compatível com a nova versão do PHP (Zend Extension ABI incompatível) ou se o `oci.dll` do Oracle Instant Client não estiver no PATH do Apache.
- **Diagnóstico Profundo:**
  - Testa em tempo real a inicialização com `php.exe --ri oci8`.
  - Verifica a existência de DLLs compatíveis em `php/ext/`.
  - Audita o `php.ini` verificando se `extension=oci8_19` está descomentada.
  - Localiza automaticamente instalações do **Oracle Instant Client** no computador (ex: `instantclient_19_24`).
  - Audita a variável `PATH` do sistema para verificar o acesso à biblioteca `oci.dll`.
- **Reparo em 1 Clique:**
  - Instala e ativa a DLL compatível (do PECL oficial ou pacote fornecido).
  - Descomenta e padroniza a diretiva no `php.ini`.
  - Gera o inicializador **`INICIAR_APACHE_ORACLE.bat`** que injeta o Oracle Instant Client no PATH antes de subir o servidor Apache.
- **Proteção no Atualizador:**
  - O atualizador impede que DLLs antigas compiladas para PHP 8.2 sejam indevidamente migradas para versões mais recentes, prevenindo corrupção no carregamento.

### 2. 🧹 Limpeza & Rotação Mensal de Logs do Apache
- **Varredura Automática:** Localiza todos os logs do Apache/XAMPP (`access.log`, `error.log`, `ssl_request.log`, etc.).
- **Separação por Meses:** Processa arquivos em streaming (sem sobrecarregar memória RAM mesmo com logs gigantescos de vários GBs) e divide os registros linha a linha em arquivos mensais (`access_2024-10.log`, `access_2026-08.log`, etc.).
- **Remoção Seletiva Respeitando o Mês Informado:**
  - Remove do arquivo original **apenas os registros com meses estritamente anteriores** ao mês de corte informado (ex: `< 09/2026`).
  - **Preserva no arquivo original** todos os registros recentes (a partir de `09/2026`).
- **Compactação em `.ZIP` dos Meses Anteriores:**
  - Registros de meses anteriores ao corte são compactados em `.ZIP` de alta taxa de compressão e o `.log` intermediário é excluído.
  - Registros recentes permanecem preservados em formato de texto.

### 3. 🛡️ Atualização Segura do PHP & Reversão 100% Garantida
- **Duplo Backup Blindado:**
  - Cópia integral da pasta `php/` para `backups_php_xampp/backup_TIMESTAMP/`.
  - Arquivo compactado `.ZIP` imutável com checksum SHA-256 de cada arquivo.
  - Cópia dos arquivos de configuração do Apache (`httpd-xampp.conf`, `httpd.conf`, `httpd-vhosts.conf`).
- **Script Autônomo `REVERTER_ULTIMO_BACKUP.bat`:**
  - Permite restaurar tudo com 2 cliques fora do programa caso o computador seja desligado ou ocorra qualquer imprevisto.
- **Pré-Validação em Área Isolada (Staging):**
  - O novo PHP é testado antes de tocar na sua instalação oficial. Se falhar, nada é alterado.
- **Swap Atômico com Rollback Automático Imediato:**
  - A troca de pasta ocorre de forma atômica e reverte automaticamente em caso de anomalia.
- **Restaurar Backup em 1 Clique:**
  - Histórico visual de backups na própria interface gráfica.

### 4. 🔍 Auditoria Profunda da Instalação
- **Extensões Ativas:** Mapeia e reativa automaticamente todas as extensões em uso no `php.ini`.
- **DLLs Personalizadas:** Identifica extensões externas em `ext/` (Oracle `oci8`, Microsoft `sqlsrv`, Xdebug, etc.).
- **Parâmetros Personalizados:** Preserva limites de memória, upload, timeouts e fuso horário (`date.timezone`).
- **Exportação de Relatório HTML:** Gera documento profissional formatado para anexar a ordens de serviço ou auditorias.

---

## 📁 Estrutura do Projeto

- `XamppPhpUpgradeMaster.exe`: Executável nativo standalone do Windows.
- `main.py`: Ponto de entrada do script Python.
- `gui.py`: Interface gráfica CustomTkinter com as 6 abas operacionais.
- `oracle_oci8_manager.py`: Motor de diagnóstico, pacotes PECL OCI8, configuração e reparo do driver Oracle.
- `log_cleaner.py`: Motor de leitura em streaming, extração mensal, remoção seletiva e compactação em `.ZIP`.
- `analyzer.py`: Motor de auditoria, diagnóstico de VC++, diagnóstico OCI8 e exportação de relatório HTML.
- `updater.py`: Motor de download, backup com tolerância zero a perdas, swap atômico e rollback.
- `compatibility.py`: Base de conhecimento de ciclo de vida e breaking changes do PHP.
- `run_gui.bat`: Launcher em lote.
