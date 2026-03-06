# FlowScroll — Build & Multiprocessing Notes

Ce dépôt contient l'application FlowScroll (interface PyQt6) ainsi que des utilitaires de test et benchmark.

Ce document explique comment créer une build Windows avec PyInstaller, les considérations liées au multiprocessing sur Windows, et comment exécuter les tests/benchmarks fournis.

## Pré-requis

- Python 3.10+ (ou 3.11/3.12/3.13) installé
- pip
- Powershell (Windows)
- (optionnel) `pyautogui`, `pynput`, `ttkbootstrap` pour certaines fonctionnalités d'automatisation et thème

## Build (création d'un .exe)

Le script `build_release.ps1` automatise la création d'une build unique (`--onefile`) via PyInstaller.

Important (multiprocessing et PyInstaller sur Windows)
- Le module `multiprocessing` sur Windows utilise le mode `spawn`. Pour que les processus enfants démarrent correctement dans un exécutable créé par PyInstaller, le module principal doit appeler `multiprocessing.freeze_support()` dans le bloc `if __name__ == '__main__':`.
- Le fichier `src/main.py` contient déjà un `multiprocessing.freeze_support()` dans son point d'entrée.
- Le script de build ajoute les `--hidden-import "multiprocessing"` et `--hidden-import "multiprocessing.spawn"` pour éviter des problèmes d'import manquant lors du freeze.

Étapes (PowerShell) :

```powershell
# Ouvrir PowerShell dans le dossier du projet
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; .\build_release.ps1
```

Le binaire final est copié dans le dossier `release\FlowScroll.exe` si la construction réussit.

## Tests et benchmark

Fichiers utiles :
- `tests/test_run_flowscroll_pytest.py` : test automatisé UI qui injecte un faux `pyautogui` et vérifie que le clicker s'exécute via un `ThreadPoolExecutor` pour ne pas bloquer la boucle GUI.
- `tests/benchmark_multicore.py` : benchmark simple comparant exécution séquentielle, `ProcessPoolExecutor` et `ThreadPoolExecutor` sur une tâche CPU simulée (voir `workers.heavy_work`).

Pour lancer le benchmark :

```powershell
python .\tests\benchmark_multicore.py
```

Remarques :
- Les gains du `ProcessPoolExecutor` apparaissent surtout pour des tâches CPU lourdes. Pour des tâches très rapides le surcoût de création/communication de processus peut annuler le gain.
- Le `ThreadPoolExecutor` aide pour I/O, mouvements souris/clics (pyautogui), et pour garder la boucle UI réactive.

## Intégration multiprocessing dans l'application

- `src/main.py` et le moteur exposent des `ThreadPoolExecutor` pour les tâches bloquantes.
- Les callbacks fournis seront exécutés sur le thread principal pour garantir la sécurité avec l'UI.
- Les opérations bloquantes liées à `pyautogui` (move, click, mouseDown/mouseUp) ont été déplacées vers un `ThreadPoolExecutor` pour éviter que la boucle GUI ne soit bloquée.

## Packaging & PyInstaller tips

- Si vous ajoutez d'autres modules qui utilisent multiprocessing ou spawn, assurez-vous que le point d'entrée appelle `freeze_support()`.
- Si vous rencontrez des erreurs liées à des imports manquants, relancez PyInstaller en ajoutant `--hidden-import` pour les modules en question.
- Testez l'exécutable sur une machine cible (même version de Windows) et vérifiez les permissions (par ex. déplacement de la souris peut être bloqué par l'OS/antivirus).

## Que faire si l'icône n'est pas mise à jour

Windows peut cacher les icônes dans son cache. Si l'icône de `release\Autoscroller.exe` n'est pas la bonne :

- Fermez l'Explorateur, supprimez le cache d'icônes et redémarrez l'explorateur (script PowerShell utilisé par le projet) :

```powershell
taskkill /F /IM explorer.exe 2>$null; Start-Sleep -Seconds 1; Remove-Item "$env:LOCALAPPDATA\IconCache.db" -Force -ErrorAction SilentlyContinue; Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\iconcache*.db" -Force -ErrorAction SilentlyContinue; Start-Process explorer.exe
```

## Prochaine étape

Si vous avez des fonctions CPU‑bound réelles à paralléliser (ex : traitement d'images, conversions, calculs), indiquez leurs signatures. Je peux :

- les déplacer dans `workers.py` et adapter l'appel depuis l'UI via `submit_cpu_task`,
- ajouter des tests pour vérifier la scalabilité (nombre de coeurs utilisé),
- et ajuster le script de build si nécessaire.

---

Si vous voulez que je mette à jour le script de build avec des ajustements supplémentaires (par ex. options PyInstaller pour inclure des fichiers binaires externes, exclusions, etc.), dites‑moi lesquels et je les intègre.
