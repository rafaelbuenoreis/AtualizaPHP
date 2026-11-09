"""
main.py - Ponto de entrada principal do XAMPP & PHP Upgrade Master.
"""

import sys
import os

# Adiciona o diretório atual ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import XamppPhpUpgradeApp

def main():
    app = XamppPhpUpgradeApp()
    app.mainloop()

if __name__ == "__main__":
    main()
