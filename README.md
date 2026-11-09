# ⚡ XAMPP & PHP Upgrade Master

Aplicação desktop com **Interface Gráfica Moderna (CustomTkinter)** e **Executável Standalone (.EXE)** desenvolvida para:
1. **Auditar e atualizar o PHP no XAMPP** com 100% de segurança, tolerância zero a perdas e reversão garantida.
2. **Limpar, rotacionar e compactar logs do Apache** automaticamente com separação mensal e arquivamento em `.ZIP`.

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

### 1. 🧹 Limpeza & Rotação Mensal de Logs do Apache (NOVO)
- **Varredura Automática:** Localiza todos os logs do Apache/XAMPP (`access.log`, `error.log`, `ssl_request.log`, etc.).
- **Separação por Meses:** Processa arquivos em streaming (sem sobrecarregar memória RAM mesmo com logs gigantescos de vários GBs) e divide os registros linha a linha em arquivos mensais (`access_2024-10.log`, `access_2026-08.log`, etc.).
- **Limpeza do Arquivo Original:** Trunca os logs originais para **0 bytes**, liberando espaço imediato no disco rígido sem derrubar o Apache.
- **Compactação em `.ZIP` dos Meses Anteriores a 09/2026:**
  - Meses estritamente anteriores a `09/2026` (`< 2026-09`) são automaticamente compactados em formato `.ZIP` de alta taxa de compressão e o `.log` intermediário é excluído.
  - Meses a partir de `09/2026` (`>= 2026-09`) permanecem preservados em formato de texto descompactado.

### 2. 🛡️ Atualização Segura do PHP & Reversão 100% Garantida
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

### 3. 🔍 Auditoria Profunda da Instalação
- **Extensões Ativas:** Mapeia e reativa automaticamente todas as extensões em uso no `php.ini`.
- **DLLs Personalizadas:** Identifica extensões externas em `ext/` (Oracle `oci8`, Microsoft `sqlsrv`, Xdebug, etc.).
- **Parâmetros Personalizados:** Preserva limites de memória, upload, timeouts e fuso horário (`date.timezone`).
- **Exportação de Relatório HTML:** Gera documento profissional formatado para anexar a ordens de serviço ou auditorias.

---

## 📁 Estrutura do Projeto

- `XamppPhpUpgradeMaster.exe`: Executável nativo standalone do Windows.
- `main.py`: Ponto de entrada do script Python.
- `gui.py`: Interface gráfica CustomTkinter com as 5 abas operacionais.
- `log_cleaner.py`: Motor de leitura em streaming, extração mensal, truncamento e compactação em `.ZIP`.
- `analyzer.py`: Motor de auditoria, diagnóstico de VC++ e exportação de relatório HTML.
- `updater.py`: Motor de download, backup com tolerância zero a perdas, swap atômico e rollback.
- `compatibility.py`: Base de conhecimento de ciclo de vida e breaking changes do PHP.
- `run_gui.bat`: Launcher em lote.
