# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 11:47:31 2026
    IGNORE_DIRS = {'.git', '__pycache__', '.venv', 'venv', '.vscode', '.idea', 'out', '.pytest_cache', 'htmlcov'}
@author: CBUEHRING
"""

import os
import zipfile
from pathlib import Path

def get_next_version_name(base_name, target_folder):
    """Sucht im Zielordner nach der nächsten freien Vxx-Nummer."""
    version = 1
    while True:
        current_name = target_folder / f"{base_name}_V{version:02d}.zip"
        if not current_name.exists():
            return current_name
        version += 1

def backup_with_filters():
    # --- KONFIGURATION ---
    EBENEN_HOCH = 1  # Wie viele Ebenen über dem Skript liegt das Projekt-Root?
    
    # Erlaubte Dateiendungen
    EXTENSIONS = ('.py', '.md', '.json', '.yaml', '.txt', '.html', '.css')
    
    # Ordner, die komplett ignoriert werden
    IGNORE_DIRS = {'.git', '__pycache__', '.venv', 'venv', '.vscode', '.idea', 'out', '.pytest_cache', 'htmlcov'}
    
    # Spezifische Dateinamen, die ignoriert werden
    IGNORE_FILES = {'.DS_Store', 'report.html', '.env', 'geheim.txt'}
    # ---------------------

    script_dir = Path.cwd()
    
    # Root-Verzeichnis bestimmen
    root_dir = script_dir
    for _ in range(EBENEN_HOCH):
        root_dir = root_dir.parent

    # Zielverzeichnis: "versionen" Ordner auf der gleichen Ebene wie root_dir
    versions_dir = root_dir.parent / "versionen"
    versions_dir.mkdir(exist_ok=True)

    folder_name = root_dir.name
    zip_path = get_next_version_name(folder_name, versions_dir)
    
    files_to_add = []

    print(f"--- Backup-Vorgang gestartet ---")
    print(f"Projekt-Root: {root_dir}")
    print(f"Ziel-Archiv:  {zip_path.name}")

    # Dateien sammeln
    for root, dirs, files in os.walk(root_dir):
        # 1. Verzeichnisse filtern
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            # 2. Prüfen, ob Dateiname auf der Ignore-Liste steht
            if file in IGNORE_FILES:
                continue
                
            # 3. Prüfen, ob die Endung erlaubt ist
            if file.lower().endswith(EXTENSIONS):
                full_path = Path(root) / file
                
                # Sicherheitscheck: Das Skript packt nicht das Archiv selbst ein, 
                # falls es im Suchpfad liegen sollte
                if full_path != zip_path:
                    files_to_add.append(full_path)

    if not files_to_add:
        print("\nKeine passenden Dateien zum Sichern gefunden.")
        return

    # Archiv erstellen
    print(f"\nPacke {len(files_to_add)} Dateien...")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files_to_add:
                arcname = file.relative_to(root_dir)
                zipf.write(file, arcname=arcname)
                    
        print(f"\nERFOLG!")
        print(f"Archiv erstellt in: {zip_path}")
        
    except Exception as e:
        print(f"\nFEHLER beim Erstellen des Backups: {e}")

if __name__ == "__main__":
    backup_with_filters()