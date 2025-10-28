# Python-Scrapping-Project-DISCOGS
# 🎵 Discogs Scraper - Albums les plus populaires

Scraper Python permettant d'extraire les informations des albums les plus collectionnés sur Discogs avec leurs statistiques complètes.

## Description

Ce projet scrape automatiquement le catalogue Discogs (trié par popularité) et extrait :
- **Étape 1** : Artiste, Album, URL de chaque album
- **Étape 2** : Statistiques détaillées (labels, formats, notes, prix, etc.)

## Fonctionnalités

### Données extraites

**Informations de base :**
- Nom de l'artiste (nettoyé)
- Titre de l'album (nettoyé)
- URL de la page album

**Statistiques détaillées :**
- Label(s) de production
- Format(s) : Vinyl, CD, Cassette, etc.
- Pays de sortie
- Date de sortie et année
- Genre(s) musicaux
- Nombre de collections
- Nombre de wantlists
- Note moyenne et nombre de notes
- Date de dernière vente
- Prix : Faible, Moyen, Élevé

### Nettoyage automatique des données

Le scraper applique un nettoyage avancé sur toutes les données :
- Suppression des numéros entre parenthèses (ex: "Justice (3)" → "Justice")
- Décodage des entités HTML (ex: "&#39;" → "'")
- Formatage des dates au format JJ/MM/AAAA pour Excel
- Conversion des prix (virgules → points)
- Suppression des doublons dans les listes
- Nettoyage des caractères spéciaux (&, guillemets indésirables, etc.)

## Installation

### Prérequis

- Python 3.8+
- pip

### Dépendances

```bash
pip install crawl4ai beautifulsoup4
```

**Librairies utilisées :**
- `crawl4ai` : Navigation web asynchrone avec gestion du JavaScript
- `beautifulsoup4` : Parsing HTML
- `asyncio` : Gestion asynchrone
- `time` : Pauses entre requêtes et mesure du temps d'exécution
- `csv` : Export des données
- `re` : Expressions régulières pour le nettoyage
- `html` : Décodage des entités HTML
- `random` : Délais aléatoires entre requêtes (anti-détection)

## Utilisation

### Lancement du script

```bash
python3 main.py
```

### Configuration interactive

Le script propose un mode interactif au démarrage :

```
Scraper 200 pages du catalogue ? (oui/non) :
```

- **oui** : Scrape les 200 premières pages (~10 000 albums)
- **non** : Mode TEST - choix personnalisé des pages

### Mode TEST

Si vous choisissez "non", vous pourrez définir :
```
Page de début (défaut=1) : 1
Page de fin (défaut=2) : 5
```

### Enrichissement des données

Après l'étape 1, le script demande :
```
Enrichir avec l'étape 2 ? (oui/non) :
```

- **oui** : Visite chaque page album pour extraire toutes les statistiques (~13s par album)
- **non** : Conserve uniquement les données de base (artiste, album, URL)

## Fichiers générés

### Fichiers CSV

| Fichier | Contenu | Moment de création |
|---------|---------|-------------------|
| `discogs_albums_etape1.csv` | Données du catalogue (artiste, album, URL) | Après étape 1 |
| `discogs_albums_final.csv` | Données finales (avec ou sans enrichissement) | À la fin |
| `discogs_enrichi_backup_X.csv` | Sauvegardes intermédiaires tous les 50 albums | Pendant étape 2 |

### Fichier texte

- `discogs_urls.txt` : Liste simple de toutes les URLs extraites

## Structure des données CSV

### Étape 1 (base)
```csv
artiste,album,url
Pink Floyd,The Dark Side Of The Moon,https://www.discogs.com/release/...
```

### Étape 2 (enrichi)
```csv
artiste,album,url,label,format,pays,date_sortie,annee,genres,en_collection,en_wantlist,note_moyenne,nombre_notes,derniere_vente,prix_faible,prix_moyen,prix_eleve
Pink Floyd,The Dark Side Of The Moon,https://...,Harvest,Vinyl,UK,01/03/1973,1973,"Progressive Rock, Psychedelic Rock",128456,45789,4.65,12345,15/10/2025,25.00,85.50,450.00
```

## Fonctionnalités techniques

### Système de retry

Le scraper intègre un système de tentatives automatiques :
- **3 tentatives maximum** par page
- Pause de 5 secondes entre chaque tentative
- Validation du contenu (minimum 500 caractères)

### Pauses et rate limiting

- **1 seconde** entre chaque page du catalogue
- **1,5 seconde** entre chaque page album (étape 2)
- **5 secondes** en cas d'erreur avant retry

### Sauvegardes automatiques

- Sauvegarde immédiate après l'étape 1
- Sauvegardes intermédiaires **tous les 50 albums** en étape 2
- Protection contre la perte de données en cas d'interruption

## Performances

### Temps estimés

| Action | Temps | Albums |
|--------|-------|--------|
| 1 page catalogue | ~15s | ~50 albums |
| 1 album enrichi | ~13s | 1 album |
| 200 pages complètes | ~36h | ~10 000 albums |
| 200 pages (étape 1 seulement) | ~30min | ~10 000 albums |

### Vitesse moyenne

- **Étape 1** : ~150-200 albums/minute
- **Étape 2** : ~40 albums/minute

## Personnalisation

### Modifier le nombre de pages

Dans le code, changez les valeurs par défaut :
```python
page_debut = 1
page_fin = 200  # Modifiez ici
```

### Modifier la fréquence des sauvegardes

```python
enrichir_avec_details(albums, sauvegarder_tous_les=50)  # Toutes les 50
```

### Ajuster les délais

```python
time.sleep(1)    # Entre pages catalogue
time.sleep(1.5)  # Entre albums enrichis
```

## Version alternative pour IP red-flagged

### test_safe.py - Version avec protection renforcée

Si votre adresse IP est signalée par Discogs (trop de requêtes, blocages temporaires), utilisez la version alternative du code qui inclut :

**Améliorations de sécurité :**
- **Délais aléatoires** : Temps d'attente variables entre 2-5 secondes (au lieu de fixes)
- **Retry amélioré** : Jusqu'à 5 tentatives (au lieu de 3) avec backoff exponentiel
- **Timeout augmenté** : 60 secondes max par page (au lieu de 30)
- **Délai de chargement aléatoire** : Entre 3 et 8 secondes avant de récupérer le HTML
- **Validation stricte** : Vérification du contenu minimum à 1000 caractères

**Exemple d'utilisation :**
```bash
python test_5_safe.py
```

**Configuration des délais dans la version safe :**
```python
# Délais aléatoires entre pages
import random
time.sleep(random.uniform(2, 5))  # Entre 2 et 5 secondes

# Délai de chargement plus long et aléatoire
delay_before_return_html=random.uniform(3.0, 8.0)

# Plus de tentatives
max_retries = 5
```

**Quand utiliser cette version :**
- ✅ Après avoir reçu des erreurs 429 (Too Many Requests)
- ✅ Si les pages ne se chargent pas correctement
- ✅ Lorsque vous scrapiez de grandes quantités de données
- ✅ Pour éviter d'être détecté comme un bot
- ✅ Si vous rencontrez des timeouts fréquents

> **Note** : La version safe est environ 2-3x plus lente que la version standard, mais réduit considérablement les risques de blocage.

## Limitations et considérations

### Respect du site

- Le scraper respecte des délais raisonnables entre requêtes
- Il ne surcharge pas les serveurs Discogs
- Utilisez-le de manière responsable

### Données

- Les prix peuvent varier selon la devise de votre compte Discogs
- Certaines pages peuvent ne pas contenir toutes les informations
- Le scraper gère les erreurs et continue avec les données disponibles

### Légalité

- Ce scraper est fourni à des fins éducatives
- Vérifiez les conditions d'utilisation de Discogs
- N'utilisez pas les données à des fins commerciales sans autorisation

## Gestion des erreurs

Le scraper gère automatiquement :
- Pages non chargées (retry automatique)
- Données manquantes (valeurs par défaut)
- Interruptions (sauvegardes intermédiaires)
- Timeouts (30 secondes max par page)

## Exemples de sortie

### Console
``````````````````````````````````````````````````````````````````````````````
======================================================================
ÉTAPE 1 : RÉCUPÉRATION DEPUIS LE CATALOGUE
======================================================================
Page 1/200
URL: https://www.discogs.com/fr/search/?sort=have%2Cdesc&type=release&page=1
  → 50 albums trouvés
  50 albums extraits
  Total cumulé : 50 albums
  Exemple : Pink Floyd - The Dark Side Of The Moon
``````````````````````````````````````````````````````````````````````````````

### CSV enrichi
```csv
artiste,album,label,annee,note_moyenne,en_collection
Pink Floyd,The Dark Side Of The Moon,"Harvest, EMI",1973,4.65,128456
Michael Jackson,Thriller,"Epic, CBS",1982,4.58,95234
```

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer des améliorations
- Ajouter de nouvelles fonctionnalités

## Licence

Ce projet est fourni tel quel, à des fins éducatives uniquement.

## Liens utiles

- [Discogs.com](https://www.discogs.com)
- [Documentation Crawl4AI](https://github.com/unclecode/crawl4ai)
- [Beautiful Soup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Echo - Projet Business](https://echo-pulse-matrix.lovable.app)

---

**Note** : Ce scraper n'est pas affilié à Discogs et n'utilise pas leur API officielle. Utilisez-le de manière responsable et respectueuse.