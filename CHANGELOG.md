# Autoscroller v2.0.0 - Notes de version

## Nouvelles fonctionnalités

### ✅ Persistance complète des paramètres
- Tous les paramètres sont maintenant sauvegardés automatiquement dans `autoscroller_settings.json`
- Sauvegarde : vitesse de scroll vertical/horizontal, paramètres du clicker (min/max, CPS, mode), thème choisi, raccourcis clavier
- Les paramètres sont restaurés au démarrage de l'application

### ⌨️ Raccourcis clavier configurables
- **F9** : Toggle scroll vertical (par défaut)
- **F10** : Toggle auto-clicker (par défaut)
- **Clic droit** : Arrêt d'urgence (tout stopper)
- Menu "Paramètres > Configurer raccourcis..." pour personnaliser les touches

### 🟢 Indicateurs visuels d'état
- Les boutons deviennent **verts** quand ils sont actifs
- Indication claire de ce qui est en cours d'exécution
- Compatible avec les thèmes ttkbootstrap et le style standard

### 📊 Compteurs en temps réel
- **Compteur de clicks** : affiche le nombre total de clicks effectués
- **Compteur de scrolls verticaux** : nombre de mouvements de molette verticale
- **Compteur de scrolls horizontaux** : nombre de mouvements de molette horizontale
- Remise à zéro à chaque démarrage de l'application

### ↔️ Scroll horizontal
- Nouveau slider pour contrôler le défilement gauche/droite
- Fonctionne indépendamment du scroll vertical
- Bouton dédié "Start scroll horizontal" / "Stop scroll horizontal"
- Utilise `pyautogui.hscroll()` pour le défilement horizontal

### 💬 Tooltips / Aide contextuelle
- Bulles d'aide sur tous les contrôles principaux
- Explications claires au survol de la souris
- Aide l'utilisateur à comprendre chaque fonctionnalité sans documentation externe

### ℹ️ Menu "À propos"
- Version de l'application affichée : **v2.0.0**
- Liste des fonctionnalités principales
- Raccourcis clavier par défaut documentés
- Accessible via menu "Aide > À propos"

### 📦 Réduction de la taille de l'EXE
- Exclusion des modules inutilisés lors du build PyInstaller
- Modules exclus : matplotlib, numpy, pandas, scipy, pytest, IPython, jupyter, notebook
- **Taille finale** : ~19 MB (au lieu de ~25-30 MB précédemment)

## Améliorations techniques

- Support du clavier global via `pynput.keyboard` pour les hotkeys
- Architecture modulaire avec séparation claire des fonctionnalités
- Gestion robuste des erreurs avec fallbacks multiples
- Compatibilité maintenue avec ou sans dépendances optionnelles

## Fichiers modifiés

- `Autoscroller.py` : version 2.0.0 complète avec toutes les nouvelles fonctionnalités
- `build_release.ps1` : ajout des exclusions de modules pour réduire la taille
- `requirements.txt` : déjà à jour avec toutes les dépendances

## Installation et utilisation

### Pour développement :
```powershell
cd "e:\Developpement\AutoScroller"
python -m pip install -r requirements.txt
python Autoscroller.py
```

### Pour build release :
```powershell
cd "e:\Developpement\AutoScroller"
.\build_release.ps1
```

L'exécutable sera dans `release\Autoscroller.exe` (~19 MB, standalone, aucune installation requise).

## Migration depuis v1

- Les anciens paramètres `autoscroller_settings.json` (v1) sont compatibles
- Nouveaux champs ajoutés automatiquement avec valeurs par défaut
- Pas de perte de configuration lors de la mise à jour

## Notes importantes

- Les compteurs sont remis à zéro à chaque démarrage (pas de persistance des stats)
- Le scroll horizontal nécessite que l'application ciblée supporte `hscroll` (pas universel)
- Les raccourcis globaux nécessitent `pynput` installé (sinon, raccourcis locaux uniquement)

---

**Version** : 2.0.0  
**Date** : 21 novembre 2025  
**Compatibilité** : Windows 10/11, Python 3.13+
