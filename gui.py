"""
gui.py - Interface Gráfica Moderna em CustomTkinter para Análise, Atualização Criteriosa e Limpeza de Logs do Apache.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Dict, Any, List

import customtkinter as ctk

from analyzer import XamppAnalyzer
from updater import PhpUpdater
from log_cleaner import ApacheLogCleaner
from compatibility import PHP_LIFECYCLE, OFFLINE_PHP_CATALOG, KNOWN_THIRD_PARTY_EXTENSIONS

# Configuração global de aparência
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class XamppPhpUpgradeApp(ctk.CTk):
    """Janela principal da aplicação de atualização, reversão e limpeza de logs do XAMPP."""

    def __init__(self):
        super().__init__()

        self.title("XAMPP & PHP Upgrade Master - Backup Blindado, Rollback & Limpeza de Logs")
        self.geometry("1160x800")
        self.minsize(1020, 720)

        # Estado da aplicação
        self.analyzer: Optional[XamppAnalyzer] = None
        self.updater: Optional[PhpUpdater] = None
        self.log_cleaner: Optional[ApacheLogCleaner] = None
        self.analysis_report: Optional[Dict[str, Any]] = None
        self.available_versions: List[Dict[str, Any]] = []
        self.detected_logs: List[Dict[str, Any]] = []
        self.log_checkboxes: Dict[str, tk.BooleanVar] = {}
        self.is_processing = False
        self.cancel_download_flag = False

        # Construir layout
        self._build_header()
        self._build_tabs()
        self._build_footer()

        # Inicialização com auto-detecção
        self.after(200, self._initial_auto_scan)

    def _build_header(self):
        """Cabeçalho superior com título, caminho do XAMPP e botões rápidos."""
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#2b2b2b", "#1f1f23"))
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(fill="x", padx=15, pady=(10, 5))

        lbl_title = ctk.CTkLabel(
            title_box,
            text="⚡ XAMPP & PHP Upgrade Master",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4dabf7"
        )
        lbl_title.pack(side="left")

        lbl_subtitle = ctk.CTkLabel(
            title_box,
            text="Proteção Blindada • Rollback 100% • Limpeza e Rotação Mensal de Logs",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#51cf66"
        )
        lbl_subtitle.pack(side="left", padx=15)

        path_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        path_box.pack(fill="x", padx=15, pady=(5, 12))

        ctk.CTkLabel(path_box, text="Diretório da Instalação:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))

        self.entry_path = ctk.CTkEntry(
            path_box,
            placeholder_text=r"Exemplo: C:\xampp ou D:\WebServer",
            width=480,
            font=ctk.CTkFont(size=12)
        )
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse = ctk.CTkButton(
            path_box,
            text="📁 Procurar...",
            width=100,
            command=self._on_browse_path
        )
        btn_browse.pack(side="left", padx=(0, 8))

        btn_auto = ctk.CTkButton(
            path_box,
            text="🎯 Auto-Detectar",
            width=110,
            fg_color="#343a40",
            hover_color="#495057",
            command=self._on_auto_detect
        )
        btn_auto.pack(side="left", padx=(0, 8))

        self.btn_analyze = ctk.CTkButton(
            path_box,
            text="🔍 Analisar Instalação",
            width=150,
            fg_color="#1971c2",
            hover_color="#1864ab",
            font=ctk.CTkFont(weight="bold"),
            command=self._start_analysis
        )
        self.btn_analyze.pack(side="left")

    def _build_tabs(self):
        """Cria as abas principais da aplicação."""
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=5)

        self.tab_overview = self.tabview.add("📊 Visão Geral & Diagnóstico")
        self.tab_audit = self.tabview.add("🔍 Auditoria da Instalação (php.ini & Extensões)")
        self.tab_plan = self.tabview.add("📋 Plano de Atualização & Cuidados")
        self.tab_upgrade = self.tabview.add("🚀 Atualizador Seguro & Rollback Garantido")
        self.tab_logs = self.tabview.add("🧹 Limpeza de Logs do Apache")

        self._build_tab_overview()
        self._build_tab_audit()
        self._build_tab_plan()
        self._build_tab_upgrade()
        self._build_tab_logs()

    # -------------------------------------------------------------
    # ABA 1: VISÃO GERAL
    # -------------------------------------------------------------
    def _build_tab_overview(self):
        tab = self.tab_overview

        self.card_status = ctk.CTkFrame(tab, corner_radius=10, fg_color="#212529")
        self.card_status.pack(fill="x", padx=10, pady=10)

        self.lbl_status_icon = ctk.CTkLabel(
            self.card_status,
            text="ℹ️",
            font=ctk.CTkFont(size=32)
        )
        self.lbl_status_icon.pack(side="left", padx=15, pady=15)

        status_text_box = ctk.CTkFrame(self.card_status, fg_color="transparent")
        status_text_box.pack(side="left", fill="both", expand=True, pady=10)

        self.lbl_status_title = ctk.CTkLabel(
            status_text_box,
            text="Aguardando Análise...",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        self.lbl_status_title.pack(fill="x")

        self.lbl_status_desc = ctk.CTkLabel(
            status_text_box,
            text="Clique em 'Analisar Instalação' para verificar as versões e configurações instaladas.",
            font=ctk.CTkFont(size=12),
            text_color="#ced4da",
            anchor="w"
        )
        self.lbl_status_desc.pack(fill="x", pady=(2, 0))

        grid_cards = ctk.CTkFrame(tab, fg_color="transparent")
        grid_cards.pack(fill="x", padx=10, pady=5)
        grid_cards.grid_columnconfigure((0, 1, 2), weight=1, uniform="group1")

        # Card 1: Atual
        card1 = ctk.CTkFrame(grid_cards, corner_radius=10)
        card1.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        ctk.CTkLabel(card1, text="Instalação Atual", font=ctk.CTkFont(size=14, weight="bold"), text_color="#74c0fc").pack(anchor="w", padx=15, pady=(12, 6))
        self.lbl_card1_version = ctk.CTkLabel(card1, text="Versão: --", font=ctk.CTkFont(size=13))
        self.lbl_card1_version.pack(anchor="w", padx=15, pady=2)
        self.lbl_card1_arch = ctk.CTkLabel(card1, text="Arquitetura / TS: --", font=ctk.CTkFont(size=13))
        self.lbl_card1_arch.pack(anchor="w", padx=15, pady=2)
        self.lbl_card1_status = ctk.CTkLabel(card1, text="Ciclo de Vida: --", font=ctk.CTkFont(size=13))
        self.lbl_card1_status.pack(anchor="w", padx=15, pady=2)
        self.lbl_card1_path = ctk.CTkLabel(card1, text="Caminho: --", font=ctk.CTkFont(size=11), text_color="#868e96")
        self.lbl_card1_path.pack(anchor="w", padx=15, pady=(2, 12))

        # Card 2: Mais recente
        card2 = ctk.CTkFrame(grid_cards, corner_radius=10)
        card2.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        ctk.CTkLabel(card2, text="Última Versão Estável", font=ctk.CTkFont(size=14, weight="bold"), text_color="#51cf66").pack(anchor="w", padx=15, pady=(12, 6))
        self.lbl_card2_version = ctk.CTkLabel(card2, text="Versão: --", font=ctk.CTkFont(size=13))
        self.lbl_card2_version.pack(anchor="w", padx=15, pady=2)
        self.lbl_card2_compat = ctk.CTkLabel(card2, text="Compatibilidade: Thread Safe x64", font=ctk.CTkFont(size=13))
        self.lbl_card2_compat.pack(anchor="w", padx=15, pady=2)
        self.lbl_card2_source = ctk.CTkLabel(card2, text="Canal: Oficial Windows PHP", font=ctk.CTkFont(size=13))
        self.lbl_card2_source.pack(anchor="w", padx=15, pady=2)
        self.lbl_card2_diff = ctk.CTkLabel(card2, text="Status: --", font=ctk.CTkFont(size=11), text_color="#868e96")
        self.lbl_card2_diff.pack(anchor="w", padx=15, pady=(2, 12))

        # Card 3: Ambiente
        card3 = ctk.CTkFrame(grid_cards, corner_radius=10)
        card3.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        ctk.CTkLabel(card3, text="Ambiente & Segurança", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffd43b").pack(anchor="w", padx=15, pady=(12, 6))
        self.lbl_card3_type = ctk.CTkLabel(card3, text="Ambiente: --", font=ctk.CTkFont(size=13))
        self.lbl_card3_type.pack(anchor="w", padx=15, pady=2)
        self.lbl_card3_vc = ctk.CTkLabel(card3, text="Visual C++ Runtime: --", font=ctk.CTkFont(size=13))
        self.lbl_card3_vc.pack(anchor="w", padx=15, pady=2)
        self.lbl_card3_procs = ctk.CTkLabel(card3, text="Processos Ativos: Nenhum", font=ctk.CTkFont(size=13))
        self.lbl_card3_procs.pack(anchor="w", padx=15, pady=2)
        self.lbl_card3_ini = ctk.CTkLabel(card3, text="php.ini: --", font=ctk.CTkFont(size=11), text_color="#868e96")
        self.lbl_card3_ini.pack(anchor="w", padx=15, pady=(2, 12))

        quick_action_bar = ctk.CTkFrame(tab, fg_color="transparent")
        quick_action_bar.pack(fill="x", padx=10, pady=(5, 2))

        btn_export_html = ctk.CTkButton(
            quick_action_bar,
            text="📄 Exportar Relatório de Auditoria (.html)",
            fg_color="#343a40",
            hover_color="#495057",
            command=self._on_export_html_clicked
        )
        btn_export_html.pack(side="left")

        self.box_overview_summary = ctk.CTkTextbox(tab, height=170, font=ctk.CTkFont(family="Consolas", size=12))
        self.box_overview_summary.pack(fill="both", expand=True, padx=10, pady=(6, 5))
        self.box_overview_summary.insert("end", "Aguardando execução da análise...\n")
        self.box_overview_summary.configure(state="disabled")

    # -------------------------------------------------------------
    # ABA 2: AUDITORIA
    # -------------------------------------------------------------
    def _build_tab_audit(self):
        tab = self.tab_audit

        sub_tabview = ctk.CTkTabview(tab, corner_radius=8)
        sub_tabview.pack(fill="both", expand=True, padx=10, pady=10)

        sub_tab_ext = sub_tabview.add("📦 Extensões Ativas no php.ini")
        sub_tab_ini = sub_tabview.add("⚙️ Parâmetros Customizados no php.ini")
        sub_tab_tp = sub_tabview.add("🧩 DLLs de Terceiros / Customizadas (ext/)")

        self.txt_audit_ext = ctk.CTkTextbox(sub_tab_ext, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_audit_ext.pack(fill="both", expand=True, padx=5, pady=5)

        self.txt_audit_ini = ctk.CTkTextbox(sub_tab_ini, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_audit_ini.pack(fill="both", expand=True, padx=5, pady=5)

        self.txt_audit_tp = ctk.CTkTextbox(sub_tab_tp, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_audit_tp.pack(fill="both", expand=True, padx=5, pady=5)

    # -------------------------------------------------------------
    # ABA 3: PLANO
    # -------------------------------------------------------------
    def _build_tab_plan(self):
        tab = self.tab_plan

        lbl_plan_header = ctk.CTkLabel(
            tab,
            text="Roteiro Criterioso de Atualização & Salvaguardas de Compatibilidade",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#4dabf7"
        )
        lbl_plan_header.pack(anchor="w", padx=15, pady=(15, 5))

        self.txt_plan = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_plan.pack(fill="both", expand=True, padx=15, pady=10)

    # -------------------------------------------------------------
    # ABA 4: ATUALIZADOR SEGURO
    # -------------------------------------------------------------
    def _build_tab_upgrade(self):
        tab = self.tab_upgrade

        opts_frame = ctk.CTkFrame(tab, corner_radius=10)
        opts_frame.pack(fill="x", padx=10, pady=10)

        row1 = ctk.CTkFrame(opts_frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(row1, text="Versão Alvo a Instalar:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        self.combo_target_version = ctk.CTkComboBox(
            row1,
            values=["PHP 8.4.1 (Thread Safe x64) [Recomendado para XAMPP Apache]", "PHP 8.3.14 (Thread Safe x64)"],
            width=420
        )
        self.combo_target_version.pack(side="left", padx=(0, 20))

        self.upgrade_source_var = tk.StringVar(value="download")
        rb_download = ctk.CTkRadioButton(
            row1,
            text="Download Direto (windows.php.net)",
            variable=self.upgrade_source_var,
            value="download",
            command=self._on_source_mode_changed
        )
        rb_download.pack(side="left", padx=10)

        rb_local_zip = ctk.CTkRadioButton(
            row1,
            text="Usar ZIP Local",
            variable=self.upgrade_source_var,
            value="local_zip",
            command=self._on_source_mode_changed
        )
        rb_local_zip.pack(side="left", padx=10)

        self.row_local_zip = ctk.CTkFrame(opts_frame, fg_color="transparent")
        self.lbl_zip = ctk.CTkLabel(self.row_local_zip, text="Arquivo ZIP Local:", font=ctk.CTkFont(weight="bold"))
        self.lbl_zip.pack(side="left", padx=(0, 10))
        self.entry_local_zip = ctk.CTkEntry(self.row_local_zip, placeholder_text="Selecione o arquivo .zip baixado...", width=500)
        self.entry_local_zip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.btn_browse_zip = ctk.CTkButton(self.row_local_zip, text="Procurar ZIP...", width=120, command=self._on_browse_zip)
        self.btn_browse_zip.pack(side="left")

        checks_frame = ctk.CTkFrame(opts_frame, fg_color="transparent")
        checks_frame.pack(fill="x", padx=15, pady=(6, 12))

        self.chk_backup = ctk.CTkCheckBox(checks_frame, text="Backup Blindado (Pasta + ZIP + Script de Reversão)", state="disabled")
        self.chk_backup.select()
        self.chk_backup.pack(side="left", padx=(0, 15))

        self.chk_migrate_ini = ctk.CTkCheckBox(checks_frame, text="Reativar extensões e migrar diretivas do php.ini")
        self.chk_migrate_ini.select()
        self.chk_migrate_ini.pack(side="left", padx=(0, 15))

        self.chk_migrate_dlls = ctk.CTkCheckBox(checks_frame, text="Preservar DLLs de terceiros em ext/")
        self.chk_migrate_dlls.select()
        self.chk_migrate_dlls.pack(side="left", padx=(0, 15))

        self.chk_update_apache = ctk.CTkCheckBox(checks_frame, text="Sincronizar Apache (httpd-xampp.conf)")
        self.chk_update_apache.select()
        self.chk_update_apache.pack(side="left")

        action_bar = ctk.CTkFrame(tab, corner_radius=10, fg_color="#182234")
        action_bar.pack(fill="x", padx=10, pady=5)

        self.btn_execute_upgrade = ctk.CTkButton(
            action_bar,
            text="🛡️ EXECUTAR ATUALIZAÇÃO SEGURA (COM PRÉ-TESTE & ROLLBACK AUTOMÁTICO)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b8a3e",
            hover_color="#237032",
            height=42,
            command=self._start_upgrade_process
        )
        self.btn_execute_upgrade.pack(side="left", padx=15, pady=10)

        rollback_box = ctk.CTkFrame(action_bar, fg_color="transparent")
        rollback_box.pack(side="right", padx=15, pady=10)

        self.combo_backups = ctk.CTkComboBox(rollback_box, values=["Nenhum backup disponível"], width=240)
        self.combo_backups.pack(side="left", padx=(0, 10))

        self.btn_rollback = ctk.CTkButton(
            rollback_box,
            text="⏪ RESTAURAR BACKUP (1 CLIQUE)",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#d6336c",
            hover_color="#a61e4d",
            height=38,
            command=self._on_rollback_clicked
        )
        self.btn_rollback.pack(side="left")

        prog_frame = ctk.CTkFrame(tab, fg_color="transparent")
        prog_frame.pack(fill="x", padx=10, pady=(2, 2))

        self.progress_bar = ctk.CTkProgressBar(prog_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=10, pady=2)

        self.lbl_progress_status = ctk.CTkLabel(prog_frame, text="Pronto para iniciar.", font=ctk.CTkFont(size=11), text_color="#adb5bd")
        self.lbl_progress_status.pack(anchor="w", padx=10)

        lbl_log_title = ctk.CTkLabel(tab, text="Console de Execução e Auditoria de Segurança:", font=ctk.CTkFont(weight="bold"))
        lbl_log_title.pack(anchor="w", padx=15, pady=(6, 2))

        self.txt_upgrade_log = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11), height=220)
        self.txt_upgrade_log.pack(fill="both", expand=True, padx=10, pady=(2, 10))

    # -------------------------------------------------------------
    # ABA 5: LIMPEZA & ROTAÇÃO DE LOGS DO APACHE
    # -------------------------------------------------------------
    def _build_tab_logs(self):
        tab = self.tab_logs

        # Card de Configuração e Opções
        cfg_frame = ctk.CTkFrame(tab, corner_radius=10)
        cfg_frame.pack(fill="x", padx=10, pady=10)

        # Linha 1: Pasta de Logs
        row1 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(row1, text="Pasta de Logs:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        self.entry_logs_dir = ctk.CTkEntry(row1, placeholder_text=r"Ex: C:\xampp\apache\logs", width=420)
        self.entry_logs_dir.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse_logs = ctk.CTkButton(row1, text="📁 Procurar Logs...", width=120, command=self._on_browse_logs_dir)
        btn_browse_logs.pack(side="left", padx=(0, 8))

        btn_refresh_logs = ctk.CTkButton(row1, text="🔄 Recarregar", width=100, fg_color="#343a40", hover_color="#495057", command=self._refresh_logs_list)
        btn_refresh_logs.pack(side="left")

        # Linha 2: Mês Limite para Compactação e Pasta de Destino
        row2 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=(4, 6))

        ctk.CTkLabel(row2, text="Compactar meses anteriores a:", font=ctk.CTkFont(weight="bold"), text_color="#ffd43b").pack(side="left", padx=(0, 8))
        self.entry_threshold_month = ctk.CTkEntry(row2, width=90, font=ctk.CTkFont(weight="bold"))
        self.entry_threshold_month.insert(0, "09/2026")
        self.entry_threshold_month.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row2, text="Destino do Arquivamento:").pack(side="left", padx=(0, 8))
        self.entry_archived_dir = ctk.CTkEntry(row2, placeholder_text="Subpasta archived_logs (padrão)", width=320)
        self.entry_archived_dir.pack(side="left", fill="x", expand=True)

        # Linha 3: Checkboxes de Controle
        row3 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=(4, 12))

        self.chk_split_months = ctk.CTkCheckBox(row3, text="Mover e separar linhas por arquivos mensais (YYYY-MM)")
        self.chk_split_months.select()
        self.chk_split_months.pack(side="left", padx=(0, 15))

        self.chk_truncate_orig = ctk.CTkCheckBox(row3, text="Remover do original logs anteriores ao mês informado (preserva recentes)")
        self.chk_truncate_orig.select()
        self.chk_truncate_orig.pack(side="left", padx=(0, 15))

        self.chk_compress_old = ctk.CTkCheckBox(row3, text="Compactar em .ZIP meses anteriores ao mês informado")
        self.chk_compress_old.select()
        self.chk_compress_old.pack(side="left")

        # Seção de Seleção de Arquivos de Log
        logs_list_header = ctk.CTkFrame(tab, fg_color="transparent")
        logs_list_header.pack(fill="x", padx=15, pady=(4, 2))

        ctk.CTkLabel(logs_list_header, text="Arquivos de Log Encontrados:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#74c0fc").pack(side="left")

        btn_select_all = ctk.CTkButton(logs_list_header, text="Marcar Todos", width=95, height=24, font=ctk.CTkFont(size=11), command=lambda: self._on_select_all_logs(True))
        btn_select_all.pack(side="right", padx=(5, 0))

        btn_unselect_all = ctk.CTkButton(logs_list_header, text="Desmarcar", width=85, height=24, font=ctk.CTkFont(size=11), fg_color="#343a40", hover_color="#495057", command=lambda: self._on_select_all_logs(False))
        btn_unselect_all.pack(side="right")

        # Frame com scroll para listar os arquivos de log com checkboxes
        self.scroll_logs_frame = ctk.CTkScrollableFrame(tab, height=130, corner_radius=8)
        self.scroll_logs_frame.pack(fill="x", padx=10, pady=(2, 8))

        # Botão de Ação e Barra de Progresso
        action_log_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#182234")
        action_log_frame.pack(fill="x", padx=10, pady=4)

        self.btn_execute_log_clean = ctk.CTkButton(
            action_log_frame,
            text="🧹 EXECUTAR LIMPEZA, SEPARAÇÃO MENSAL E COMPACTAÇÃO DOS LOGS",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0ca678",
            hover_color="#099268",
            height=40,
            command=self._start_log_cleaning_process
        )
        self.btn_execute_log_clean.pack(side="left", padx=(15, 10), pady=8)

        btn_open_archived = ctk.CTkButton(
            action_log_frame,
            text="📂 Abrir Pasta Arquivada",
            width=160,
            height=40,
            fg_color="#343a40",
            hover_color="#495057",
            command=self._on_open_archived_folder
        )
        btn_open_archived.pack(side="left", padx=(0, 15), pady=8)

        self.lbl_logs_summary = ctk.CTkLabel(action_log_frame, text="Nenhum arquivo processado.", font=ctk.CTkFont(size=12))
        self.lbl_logs_summary.pack(side="right", padx=15)

        # Progresso
        prog_log_box = ctk.CTkFrame(tab, fg_color="transparent")
        prog_log_box.pack(fill="x", padx=10, pady=2)

        self.progress_bar_logs = ctk.CTkProgressBar(prog_log_box)
        self.progress_bar_logs.set(0)
        self.progress_bar_logs.pack(fill="x", padx=10, pady=2)

        self.lbl_progress_logs = ctk.CTkLabel(prog_log_box, text="Pronto para limpeza.", font=ctk.CTkFont(size=11), text_color="#adb5bd")
        self.lbl_progress_logs.pack(anchor="w", padx=10)

        # Console de Execução dos Logs
        lbl_console_title = ctk.CTkLabel(tab, text="Console de Execução da Rotação de Logs:", font=ctk.CTkFont(weight="bold"))
        lbl_console_title.pack(anchor="w", padx=15, pady=(6, 2))

        self.txt_logs_console = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11), height=170)
        self.txt_logs_console.pack(fill="both", expand=True, padx=10, pady=(2, 10))

    def _build_footer(self):
        footer = ctk.CTkFrame(self, height=30, fg_color="#1a1a1a")
        footer.pack(fill="x", side="bottom")

        lbl_foot_left = ctk.CTkLabel(
            footer,
            text="XAMPP & PHP Upgrade Suite - Máxima Cautela • Rotação & Compactação de Logs • Reversão 100%",
            font=ctk.CTkFont(size=11),
            text_color="#868e96"
        )
        lbl_foot_left.pack(side="left", padx=15)

        self.lbl_foot_status = ctk.CTkLabel(
            footer,
            text="Status: Pronto",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#4dabf7"
        )
        self.lbl_foot_status.pack(side="right", padx=15)

    def _log_upgrade(self, msg: str):
        self.txt_upgrade_log.insert("end", f"{msg}\n")
        self.txt_upgrade_log.see("end")

    def _log_cleaner(self, msg: str):
        self.txt_logs_console.insert("end", f"{msg}\n")
        self.txt_logs_console.see("end")

    def _on_browse_path(self):
        path = filedialog.askdirectory(title="Selecione o diretório do XAMPP ou PHP")
        if path:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, path)
            self._start_analysis()

    def _on_auto_detect(self):
        detected = XamppAnalyzer.auto_detect_path()
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, str(detected))
        self._start_analysis()

    def _initial_auto_scan(self):
        self._on_auto_detect()
        self._refresh_backups_list()
        self._refresh_logs_list()

    def _on_source_mode_changed(self):
        mode = self.upgrade_source_var.get()
        if mode == "local_zip":
            self.row_local_zip.pack(fill="x", padx=15, pady=(2, 8))
        else:
            self.row_local_zip.pack_forget()

    def _on_browse_zip(self):
        f = filedialog.askopenfilename(
            title="Selecione o arquivo ZIP oficial do PHP para Windows",
            filetypes=[("Arquivos ZIP do PHP", "*.zip")]
        )
        if f:
            self.entry_local_zip.delete(0, "end")
            self.entry_local_zip.insert(0, f)

    def _refresh_backups_list(self):
        target = Path(self.entry_path.get().strip()) if self.entry_path.get().strip() else Path(r"C:\xampp")
        updater = PhpUpdater(target)
        backups = updater.list_backups()
        if backups:
            self.combo_backups.configure(values=[b["name"] for b in backups])
            self.combo_backups.set(backups[0]["name"])
            self.btn_rollback.configure(state="normal")
        else:
            self.combo_backups.configure(values=["Nenhum backup encontrado"])
            self.combo_backups.set("Nenhum backup encontrado")
            self.btn_rollback.configure(state="disabled")

    # -------------------------------------------------------------
    # MÉTODOS DE LIMPEZA DE LOGS
    # -------------------------------------------------------------
    def _on_open_archived_folder(self):
        """Abre a pasta contendo os logs arquivados e zipados no Windows Explorer."""
        custom_arch = self.entry_archived_dir.get().strip()
        base_dir = Path(self.entry_logs_dir.get().strip()) if self.entry_logs_dir.get().strip() else Path(self.entry_path.get().strip())
        out_dir = Path(custom_arch) if custom_arch else (base_dir / "archived_logs")
        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(out_dir)
        except Exception:
            messagebox.showinfo("Pasta de Logs Arquivados", f"Diretório:\n{out_dir}")

    def _on_browse_logs_dir(self):
        p = filedialog.askdirectory(title="Selecione a pasta de logs do Apache / Servidor Web")
        if p:
            self.entry_logs_dir.delete(0, "end")
            self.entry_logs_dir.insert(0, p)
            self._refresh_logs_list()

    def _refresh_logs_list(self):
        """Busca e lista os arquivos de log detectados."""
        logs_path_str = self.entry_logs_dir.get().strip()
        if not logs_path_str:
            # Tentar sugerir baseado no target_path
            base_p = Path(self.entry_path.get().strip()) if self.entry_path.get().strip() else Path(r"C:\xampp")
            if (base_p / "apache" / "logs").exists():
                logs_path_str = str(base_p / "apache" / "logs")
            elif (base_p / "nginx" / "logs").exists():
                logs_path_str = str(base_p / "nginx" / "logs")
            elif (base_p / "logs").exists():
                logs_path_str = str(base_p / "logs")
            else:
                logs_path_str = str(base_p)
            self.entry_logs_dir.delete(0, "end")
            self.entry_logs_dir.insert(0, logs_path_str)

        cleaner = ApacheLogCleaner(Path(logs_path_str), log_callback=self._log_cleaner)
        self.log_cleaner = cleaner
        self.detected_logs = cleaner.locate_log_files()

        # Limpar widgets anteriores do frame de scroll
        for widget in self.scroll_logs_frame.winfo_children():
            widget.destroy()

        self.log_checkboxes.clear()

        if not self.detected_logs:
            lbl_empty = ctk.CTkLabel(
                self.scroll_logs_frame,
                text="Nenhum arquivo .log encontrado na pasta especificada.",
                text_color="#868e96"
            )
            lbl_empty.pack(anchor="w", padx=10, pady=5)
            self.lbl_logs_summary.configure(text="0 arquivos encontrados.")
            return

        total_size = sum(f["size_bytes"] for f in self.detected_logs)
        self.lbl_logs_summary.configure(text=f"{len(self.detected_logs)} arquivos encontrados ({cleaner.format_bytes(total_size)}).")

        for f_info in self.detected_logs:
            p_str = f_info["path"]
            var = tk.BooleanVar(value=True)
            self.log_checkboxes[p_str] = var

            row = ctk.CTkFrame(self.scroll_logs_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)

            chk = ctk.CTkCheckBox(
                row,
                text=f"{f_info['name']}  ({f_info['size_formatted']})",
                variable=var,
                font=ctk.CTkFont(weight="bold")
            )
            chk.pack(side="left", padx=(5, 15))

            lbl_detail = ctk.CTkLabel(
                row,
                text=f"Modificado em: {f_info['last_modified']}  •  {f_info['path']}",
                font=ctk.CTkFont(size=11),
                text_color="#868e96"
            )
            lbl_detail.pack(side="left")

    def _on_select_all_logs(self, select: bool):
        for var in self.log_checkboxes.values():
            var.set(select)

    def _start_log_cleaning_process(self):
        selected_paths = [p for p, var in self.log_checkboxes.items() if var.get()]
        if not selected_paths:
            messagebox.showwarning("Atenção", "Selecione ao menos um arquivo de log para processar.")
            return

        # Validar mês limite (ex: 09/2026 -> 2026-09)
        raw_threshold = self.entry_threshold_month.get().strip()
        ym_threshold = "2026-09"
        if "/" in raw_threshold:
            parts = raw_threshold.split("/")
            if len(parts) == 2:
                mm, yyyy = parts[0].strip().zfill(2), parts[1].strip()
                ym_threshold = f"{yyyy}-{mm}"
        elif "-" in raw_threshold:
            parts = raw_threshold.split("-")
            if len(parts) == 2:
                if len(parts[0]) == 4:
                    ym_threshold = f"{parts[0]}-{parts[1].zfill(2)}"
                else:
                    ym_threshold = f"{parts[1]}-{parts[0].zfill(2)}"

        confirm_msg = (
            f"CONFIRMAÇÃO DE ROTAÇÃO E LIMPEZA DE LOGS\n\n"
            f"• Arquivos selecionados: {len(selected_paths)}\n"
            f"• Mês informado de corte: {raw_threshold} ({ym_threshold})\n"
            f"• Remoção no arquivo original: Remover apenas logs ANTERIORES a {raw_threshold}\n"
            f"• Preservação no original: Todos os logs a partir de {raw_threshold} PERMANECEM no arquivo original\n"
            f"• Compactação em .ZIP: Arquivos de meses < {raw_threshold} serão compactados\n\n"
            "Deseja iniciar a operação agora?"
        )
        if not messagebox.askyesno("Confirmar Limpeza de Logs", confirm_msg):
            return

        self.btn_execute_log_clean.configure(state="disabled")
        self.lbl_progress_logs.configure(text="Iniciando processamento dos logs...")
        self.progress_bar_logs.set(0.05)

        threading.Thread(
            target=self._run_log_cleaning_thread,
            args=(selected_paths, ym_threshold, raw_threshold),
            daemon=True
        ).start()

    def _run_log_cleaning_thread(self, selected_paths: List[str], ym_threshold: str, raw_threshold: str):
        try:
            base_dir = Path(self.entry_logs_dir.get().strip())
            cleaner = ApacheLogCleaner(base_dir, log_callback=self._log_cleaner)

            # Destino de arquivamento customizado ou padrão
            custom_arch = self.entry_archived_dir.get().strip()
            out_dir = Path(custom_arch) if custom_arch else (base_dir / "archived_logs")

            total_files = len(selected_paths)
            total_lines_all = 0
            total_old_all = 0
            total_recent_all = 0
            total_zips_all = 0

            for idx, p_str in enumerate(selected_paths, 1):
                p = Path(p_str)
                self._log_cleaner(f"\n==================================================")
                self._log_cleaner(f"Processando arquivo [{idx}/{total_files}]: {p.name}")
                self._log_cleaner(f"==================================================")

                def prog_cb(ratio, lines, msg):
                    step = (idx - 1) / total_files
                    overall = step + (ratio / total_files)
                    self.after(0, lambda: self.progress_bar_logs.set(overall))
                    self.after(0, lambda: self.lbl_progress_logs.configure(text=f"[{idx}/{total_files}] {p.name}: {msg}"))

                res = cleaner.process_and_clean_log(
                    log_file_path=p,
                    output_dir=out_dir,
                    truncate_original=self.chk_truncate_orig.get(),
                    compression_threshold_ym=ym_threshold,
                    progress_callback=prog_cb
                )

                total_lines_all += res.get("lines_processed", 0)
                total_old_all += res.get("lines_removed_old", 0)
                total_recent_all += res.get("lines_kept_recent", 0)
                total_zips_all += len(res.get("compressed_zips", []))

            self.after(0, lambda: self.progress_bar_logs.set(1.0))
            self.after(0, lambda: self.lbl_progress_logs.configure(text="Limpeza de logs finalizada com sucesso!"))
            self.after(0, lambda: messagebox.showinfo(
                "Limpeza Concluída!",
                f"Operação concluída com respeito ao mês informado ({raw_threshold})!\n\n"
                f"• {total_files} arquivo(s) de log processado(s)\n"
                f"• {total_lines_all:,} linhas analisadas no total\n"
                f"• {total_old_all:,} linhas antigas (< {raw_threshold}) removidas do original e arquivadas\n"
                f"• {total_recent_all:,} linhas recentes (>= {raw_threshold}) mantidas no arquivo original\n"
                f"• {total_zips_all} pacote(s) .ZIP compactado(s)\n\n"
                f"Arquivos arquivados salvos em:\n{out_dir}"
            ))

        except Exception as e:
            err = f"Falha na limpeza de logs: {str(e)}"
            self._log_cleaner(f"[ERRO CRÍTICO] {err}")
            self.after(0, lambda: messagebox.showerror("Erro", err))

        finally:
            self.after(0, lambda: self.btn_execute_log_clean.configure(state="normal"))
            self.after(500, self._refresh_logs_list)

    # -------------------------------------------------------------
    # ANÁLISE E ATUALIZAÇÃO
    # -------------------------------------------------------------
    def _start_analysis(self):
        path_str = self.entry_path.get().strip()
        if not path_str:
            messagebox.showwarning("Atenção", "Por favor, informe o caminho da instalação do XAMPP ou PHP.")
            return

        self.btn_analyze.configure(state="disabled", text="⏳ Analisando...")
        self.lbl_foot_status.configure(text="Status: Analisando instalação...")

        threading.Thread(target=self._run_analysis_thread, args=(path_str,), daemon=True).start()

    def _run_analysis_thread(self, path_str: str):
        analyzer = XamppAnalyzer(path_str)
        report = analyzer.perform_full_analysis()
        self.analyzer = analyzer
        self.analysis_report = report

        versions = PhpUpdater.get_available_versions()
        self.available_versions = versions

        self.after(0, self._apply_analysis_results)

    def _apply_analysis_results(self):
        self.btn_analyze.configure(state="normal", text="🔍 Analisar Instalação")
        self.lbl_foot_status.configure(text="Status: Análise Concluída")

        report = self.analysis_report
        if not report:
            return

        if not report["is_valid_installation"]:
            self.lbl_status_icon.configure(text="❌")
            self.card_status.configure(fg_color="#491217")
            self.lbl_status_title.configure(text="Instalação Não Encontrada ou Inválida")
            self.lbl_status_desc.configure(text="Nenhum executável 'php.exe' detectado no caminho informado.")
            return

        urgency = report["update_urgency"]
        if urgency == "CRITICA":
            self.card_status.configure(fg_color="#491217")
            self.lbl_status_icon.configure(text="🚨")
        elif urgency == "RECOMENDADA":
            self.card_status.configure(fg_color="#4a3800")
            self.lbl_status_icon.configure(text="⚠️")
        elif urgency == "INFO":
            self.card_status.configure(fg_color="#182234")
            self.lbl_status_icon.configure(text="🔔")
        else:
            self.card_status.configure(fg_color="#14361b")
            self.lbl_status_icon.configure(text="✅")

        self.lbl_status_title.configure(text=report["urgency_label"])

        cur = report["current_php"]
        lat = report["latest_php"]

        self.lbl_card1_version.configure(text=f"Versão: PHP {cur.get('version', 'Desconhecida')}")
        self.lbl_card1_arch.configure(text=f"Arquitetura: {cur.get('architecture', 'x64')} ({cur.get('thread_safety', 'TS')})")
        lifecycle_status = report.get("current_lifecycle", {}).get("status", "N/D")
        self.lbl_card1_status.configure(text=f"Ciclo de Vida: {lifecycle_status}")
        self.lbl_card1_path.configure(text=f"Local: {report['php_dir']}")

        self.lbl_card2_version.configure(text=f"Versão: PHP {lat.get('version', '--')}")
        self.lbl_card2_compat.configure(text=f"Recomendado: Thread Safe x64 (VS17)")
        if report["needs_update"]:
            self.lbl_card2_diff.configure(text=f"Status: Atualização Recomendada (+{lat.get('version')})")
        else:
            self.lbl_card2_diff.configure(text="Status: Já está na versão mais recente!")

        env_name = "XAMPP (Apache + PHP)" if report["is_xampp"] else "Servidor PHP Personalizado"
        self.lbl_card3_type.configure(text=f"Ambiente: {env_name}")
        vc = report.get("vc_redist", {})
        vc_txt = "✅ Instalado (v14+)" if vc.get("installed") else "⚠️ Não detectado no Registro"
        self.lbl_card3_vc.configure(text=f"Visual C++ x64: {vc_txt}")

        running = report.get("running_processes", [])
        if running:
            self.lbl_card3_procs.configure(text=f"Processos: ⚠️ {', '.join(running)} rodando!", text_color="#ff8787")
        else:
            self.lbl_card3_procs.configure(text="Processos: Nenhum em execução (OK)", text_color="#69db7c")

        ini_p = Path(report.get("php_ini_path", ""))
        self.lbl_card3_ini.configure(text=f"php.ini: {ini_p.name if ini_p.exists() else 'Não encontrado'}")

        summary_text = (
            f"=== RELATÓRIO DE AUDITORIA & SALVAGUARDAS ===\n\n"
            f"• Diretório Alvo: {report['target_path']}\n"
            f"• Versão Atual do PHP: {cur.get('version')} ({cur.get('thread_safety', 'TS')} {cur.get('architecture', 'x64')})\n"
            f"• Versão Mais Recente Estável: {lat.get('version')} ({lat.get('release_date')})\n"
            f"• Necessita de Atualização: {'SIM' if report['needs_update'] else 'NÃO'}\n"
            f"• Extensões Ativas a Preservar: {len(report['active_extensions'])}\n"
            f"• DLLs de Terceiros Identificadas: {len(report['custom_extensions'])}\n"
            f"• Parâmetros Personalizados no php.ini: {len(report['custom_directives'])}\n"
            f"• Microsoft Visual C++ 2015-2022 Redistributable: {'CONFIRMADO' if vc.get('installed') else 'ATENÇÃO: Requer instalação'}\n"
        )
        if running:
            summary_text += f"\n[AVISO]: Processos em execução detectados ({', '.join(running)}).\n"

        self._update_overview_summary(summary_text)
        self._populate_audit_tab(report)
        self._populate_plan_tab(report)

        combo_vals = []
        for v in self.available_versions:
            combo_vals.append(f"PHP {v['version']} (Thread Safe x64) - {v['channel']}")
        if combo_vals:
            self.combo_target_version.configure(values=combo_vals)
            self.combo_target_version.set(combo_vals[0])

        self._refresh_backups_list()
        self._refresh_logs_list()

    def _update_overview_summary(self, text: str):
        self.box_overview_summary.configure(state="normal")
        self.box_overview_summary.delete("1.0", "end")
        self.box_overview_summary.insert("end", text)
        self.box_overview_summary.configure(state="disabled")

    def _populate_audit_tab(self, report: Dict[str, Any]):
        self.txt_audit_ext.delete("1.0", "end")
        exts = report.get("active_extensions", [])
        self.txt_audit_ext.insert("end", f"=== {len(exts)} EXTENSÕES ATIVAS DETECTADAS NO PHP.INI ===\n\n")
        self.txt_audit_ext.insert("end", "Estas extensões estão ativas e serão 100% REATIVADAS no novo PHP:\n\n")
        for i, ext in enumerate(exts, 1):
            self.txt_audit_ext.insert("end", f"[{i:02d}] {ext['type'].upper()}: {ext['name']}\n")

        self.txt_audit_ini.delete("1.0", "end")
        dirs = report.get("custom_directives", {})
        self.txt_audit_ini.insert("end", f"=== {len(dirs)} PARÂMETROS PERSONALIZADOS DO PHP.INI IDENTIFICADOS ===\n\n")
        self.txt_audit_ini.insert("end", f"{'DIRETIVA':<30} | {'VALOR ATUAL CONFIGURADO':<35}\n")
        self.txt_audit_ini.insert("end", "-" * 70 + "\n")
        for k, v in dirs.items():
            self.txt_audit_ini.insert("end", f"{k:<30} | {v:<35}\n")

        self.txt_audit_tp.delete("1.0", "end")
        tp = report.get("custom_extensions", [])
        self.txt_audit_tp.insert("end", f"=== {len(tp)} DLLs NÃO PADRÃO DETECTADAS NA PASTA EXT/ ===\n\n")
        if not tp:
            self.txt_audit_tp.insert("end", "Nenhuma DLL customizada de terceiros. Todas pertencem ao core oficial do PHP.\n")
        else:
            for item in tp:
                self.txt_audit_tp.insert("end", f"• {item['filename']} ({item['size_bytes'] / 1024:.1f} KB)\n")
                if "known_name" in item:
                    self.txt_audit_tp.insert("end", f"  {item['known_name']} - {item['notes']}\n")
                self.txt_audit_tp.insert("end", "\n")

    def _populate_plan_tab(self, report: Dict[str, Any]):
        self.txt_plan.delete("1.0", "end")
        cur_v = report["current_php"].get("version", "Atual")
        lat_v = report["latest_php"].get("version", "Destino")

        self.txt_plan.insert("end", f"================================================================================\n")
        self.txt_plan.insert("end", f" PLANO CRITERIOSO DE MIGRAÇÃO: PHP {cur_v} -> PHP {lat_v} (Thread Safe x64)\n")
        self.txt_plan.insert("end", f"================================================================================\n\n")

        self.txt_plan.insert("end", "MEDIDAS DE SEGURANÇA E CAUTELA MÁXIMA:\n")
        self.txt_plan.insert("end", "1. Backup Blindado em Pasta Espelho + Arquivo ZIP Compactado.\n")
        self.txt_plan.insert("end", "2. Geração do script 'REVERTER_ULTIMO_BACKUP.bat' para restauração autônoma.\n")
        self.txt_plan.insert("end", "3. Pré-teste isolado antes de qualquer alteração na instalação oficial.\n")
        self.txt_plan.insert("end", "4. Swap atômico com Rollback Automático imediato em caso de anomalia.\n\n")

        self.txt_plan.insert("end", "AÇÕES AUTOMATIZADAS:\n")
        for i, item in enumerate(report.get("action_checklist", []), 1):
            self.txt_plan.insert("end", f"{i}. {item}\n")

    def _on_export_html_clicked(self):
        if not self.analysis_report or not self.analyzer:
            messagebox.showinfo("Aviso", "Execute a análise antes de exportar o relatório.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Salvar Relatório de Auditoria",
            defaultextension=".html",
            filetypes=[("Páginas HTML", "*.html")]
        )
        if save_path:
            out = self.analyzer.generate_html_report(self.analysis_report, Path(save_path))
            messagebox.showinfo("Sucesso", f"Relatório HTML exportado com sucesso em:\n{out}")
            try:
                os.startfile(out)
            except Exception:
                pass

    def _start_upgrade_process(self):
        if not self.analysis_report or not self.analysis_report["is_valid_installation"]:
            messagebox.showwarning("Atenção", "Execute a análise da instalação antes de atualizar.")
            return

        target_v_str = self.combo_target_version.get()
        confirm_msg = (
            f"ATENÇÃO: MÁXIMA CAUTELA E SEGURANÇA ATIVADA\n\n"
            f"Alvo: {target_v_str}\n"
            f"Instalação: {self.analysis_report['target_path']}\n\n"
            "Garantias automáticas ativas:\n"
            "✓ Backup Integral (Pasta + Arquivo ZIP imutável com checksum)\n"
            "✓ Criação do script 'REVERTER_ULTIMO_BACKUP.bat'\n"
            "✓ Pré-validação isolada antes de modificar a produção\n"
            "✓ Reversão automática caso ocorra qualquer erro no teste final\n\n"
            "Deseja prosseguir com a atualização segura?"
        )
        if not messagebox.askyesno("Confirmar Atualização com Salvaguarda", confirm_msg):
            return

        self.is_processing = True
        self.btn_execute_upgrade.configure(state="disabled")
        self.lbl_foot_status.configure(text="Status: Executando atualização com salvaguardas...")
        self.progress_bar.set(0.05)
        self.lbl_progress_status.configure(text="Iniciando fluxo seguro de atualização...")

        threading.Thread(target=self._run_upgrade_thread, daemon=True).start()

    def _run_upgrade_thread(self):
        try:
            target_path = Path(self.analysis_report["target_path"])
            php_dir = Path(self.analysis_report["php_dir"])
            old_ini = Path(self.analysis_report["php_ini_path"]) if self.analysis_report.get("php_ini_path") else None
            apache_dir = Path(self.analysis_report["apache_dir"]) if self.analysis_report.get("apache_dir") else None

            updater = PhpUpdater(target_path, log_callback=self._log_upgrade)
            self.updater = updater

            zip_file_path = None
            source_mode = self.upgrade_source_var.get()

            if source_mode == "local_zip":
                local_path = self.entry_local_zip.get().strip()
                if not local_path or not Path(local_path).exists():
                    raise FileNotFoundError("Arquivo ZIP local não encontrado ou inválido.")
                zip_file_path = Path(local_path)
                self._log_upgrade(f"Utilizando arquivo ZIP local: {zip_file_path.name}")
            else:
                self.lbl_progress_status.configure(text="Baixando versão oficial de windows.php.net...")
                selected_v_text = self.combo_target_version.get()
                download_url = None
                for v in self.available_versions:
                    if v["version"] in selected_v_text:
                        download_url = v["files"].get("ts_x64", {}).get("url")
                        break
                if not download_url:
                    download_url = self.available_versions[0]["files"]["ts_x64"]["url"]

                downloads_dir = Path(__file__).parent / "downloads"

                def on_progress(p, cur_b, tot_b):
                    self.after(0, lambda: self.progress_bar.set(0.1 + (p * 0.4)))
                    self.after(0, lambda: self.lbl_progress_status.configure(
                        text=f"Baixando: {p*100:.1f}% ({cur_b/(1024*1024):.1f}MB de {tot_b/(1024*1024):.1f}MB)"
                    ))

                zip_file_path = updater.download_php_zip(
                    download_url,
                    downloads_dir,
                    progress_callback=on_progress,
                    cancel_check=lambda: self.cancel_download_flag
                )

            self.after(0, lambda: self.progress_bar.set(0.6))
            self.after(0, lambda: self.lbl_progress_status.configure(text="Executando backup blindado e validação atômica..."))

            success, msg, details = updater.execute_cautious_atomic_upgrade(
                zip_path=zip_file_path,
                target_php_dir=php_dir,
                old_php_ini=old_ini,
                apache_dir=apache_dir,
                migrate_custom_dlls=self.chk_migrate_dlls.get()
            )

            self.after(0, lambda: self.progress_bar.set(1.0))
            if success:
                self.after(0, lambda: self.lbl_progress_status.configure(text="Atualização concluída com 100% de sucesso!"))
                self.after(0, lambda: messagebox.showinfo(
                    "Sucesso Absoluto!",
                    f"{msg}\n\nBackup blindado registrado. Script de reversão de emergência criado."
                ))
            else:
                self.after(0, lambda: self.lbl_progress_status.configure(text="Operação revertida com segurança."))
                self.after(0, lambda: messagebox.showwarning("Aviso de Segurança", f"{msg}"))

        except Exception as e:
            err = f"Falha crítica: {str(e)}"
            self._log_upgrade(f"ERRO: {err}")
            self.after(0, lambda: self.lbl_progress_status.configure(text="Falha na atualização."))
            self.after(0, lambda: messagebox.showerror("Erro", err))

        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_execute_upgrade.configure(state="normal"))
            self.after(0, lambda: self.lbl_foot_status.configure(text="Status: Operação Finalizada"))
            self.after(0, self._refresh_backups_list)
            self.after(1000, self._start_analysis)

    def _on_rollback_clicked(self):
        selected_backup = self.combo_backups.get()
        if not selected_backup or selected_backup == "Nenhum backup encontrado":
            messagebox.showinfo("Aviso", "Nenhum backup disponível para restauração.")
            return

        msg = (
            f"REVERSÃO TOTAL DE ESTADO\n\n"
            f"Backup Selecionado: {selected_backup}\n\n"
            "Todos os arquivos da pasta 'php/' e as configurações do Apache voltarão exatamente ao momento em que o backup foi criado.\n\n"
            "Deseja executar a restauração agora?"
        )
        if not messagebox.askyesno("Confirmar Restauração", msg):
            return

        target_path = Path(self.entry_path.get().strip())
        backup_dir = target_path / "backups_php_xampp" / selected_backup

        updater = PhpUpdater(target_path, log_callback=self._log_upgrade)
        success, res_msg = updater.restore_backup(backup_dir)

        if success:
            messagebox.showinfo("Restauração Concluída", res_msg)
            self._start_analysis()
        else:
            messagebox.showerror("Erro na Restauração", res_msg)


if __name__ == "__main__":
    app = XamppPhpUpgradeApp()
    app.mainloop()
