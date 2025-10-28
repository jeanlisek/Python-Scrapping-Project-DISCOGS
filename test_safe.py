import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup
import time
import csv
import html
import re
import random  # AJOUTÉ

# -----------------------------------------------------------------------------
# CODE DE BASE AVEC SYSTÈME DE RETRY - MODIFIÉ ANTI-DÉTECTION
# -----------------------------------------------------------------------------

def crawl_get(url: str, wait_for_selector: str = "body", max_retries: int = 3):
    
    # Fonction de crawling avec retry simple en cas d'erreur - VERSION ANTI-DÉTECTION
    
    async def _run():
        for tentative in range(max_retries):
            try:
                # Délai progressif entre les tentatives
                if tentative > 0:
                    delai = 10 * tentative  # 10s, 20s, 30s
                    print(f"    Attente {delai}s avant nouvelle tentative...")
                    await asyncio.sleep(delai)
                
                browser_config = BrowserConfig(
                    headless=True,
                    verbose=False,
                    # User agent réaliste
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    ignore_https_errors=True,
                    # Headers additionnels
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1"
                    }
                )
                
                crawler_config = CrawlerRunConfig(
                    wait_for=wait_for_selector,
                    delay_before_return_html=5.0,  # Augmenté à 5 secondes
                    page_timeout=90000,  # Augmenté à 90 secondes
                    wait_until="networkidle",  # Attendre que le réseau soit calme
                    simulate_user=True,  # Simuler des mouvements de souris
                    override_navigator=True,  # Masquer les propriétés de bot
                    magic=True  # Gestion automatique des popups
                )
                
                async with AsyncWebCrawler(config=browser_config) as crawler:
                    result = await crawler.arun(url=url, config=crawler_config)
                    
                    # Vérifier que le contenu est valide
                    if result and result.html and len(result.html) > 500:
                        return result
                    else:
                        raise Exception("Contenu invalide ou vide")
            
            except Exception as e:
                print(f"    Tentative {tentative + 1}/{max_retries} échouée: {str(e)[:60]}...")
                
                # Si c'est la dernière tentative, on lève l'erreur
                if tentative == max_retries - 1:
                    print(f"    Échec définitif après {max_retries} tentatives")
                    raise e
        
        return None
    
    return asyncio.run(_run())

# -----------------------------------------------------------------------------
# NETTOYAGE DES DONNÉES
# -----------------------------------------------------------------------------

def nettoyer_artiste(artiste):
    """
    Nettoie le nom de l'artiste en supprimant les numéros entre parenthèses
    Exemple : Justice (3) devient Justice
    """
    if not artiste:
        return artiste
    
    # Décoder les entités HTML d'abord
    artiste = html.unescape(artiste)
    
    # Supprimer les guillemets indésirables
    artiste = artiste.replace('"', '').replace('"', '').replace('"', '')
    
    # Supprimer les patterns comme (3), (12), etc. à la fin
    artiste = re.sub(r'\s*\(\d+\)$', '', artiste)
    
    return artiste.strip()

def nettoyer_album(album):
    
    # Nettoie le titre de l'album en décodant les entités HTML
    # Exemple : She&#39;s So Unusual devient She's So Unusual
    
    if not album:
        return album
    
    # Décoder les entités HTML
    album = html.unescape(album)
    
    # Supprimer les guillemets indésirables (mais garder les apostrophes)
    album = album.replace('"', '').replace('"', '').replace('"', '')
    
    # Nettoyer les doubles espaces
    album = re.sub(r'\s+', ' ', album)
    
    return album.strip()

def nettoyer_label(label_str):
    
    # Nettoie les labels en limitant à 3 principaux, supprimant les doublons 
    # ET en retirant les numéros entre parenthèses
    # Exemple : "Parlophone, Warner Music Group, GEM (6)" => "Parlophone, Warner Music Group, GEM"
    
    if not label_str:
        return ""
    
    # Séparer les labels
    labels = [l.strip() for l in label_str.split(',')]
    
    # Nettoyer chaque label individuellement
    labels_nettoyes = []
    for label in labels:
        if label:
            # Supprimer les numéros entre parenthèses à la fin : (6), (12), etc.
            label_propre = re.sub(r'\s*\(\d+\)$', '', label.strip())
            
            # Ajouter seulement si pas déjà présent (supprimer doublons)
            if label_propre and label_propre not in labels_nettoyes:
                labels_nettoyes.append(label_propre)
    
    # Limiter à 3 labels principaux
    return ', '.join(labels_nettoyes[:3])

def nettoyer_format(format_str):
    
    # Nettoie les formats en supprimant "Tout format" et les doublons
    
    if not format_str:
        return ""
    
    # Séparer les formats
    formats = [f.strip() for f in format_str.split(',')]
    
    # Supprimer "Tout format" et les doublons
    formats_clean = []
    for fmt in formats:
        if fmt and fmt != "Tout format" and fmt not in formats_clean:
            formats_clean.append(fmt)
    
    return ', '.join(formats_clean)

def nettoyer_genres(genres_str):
    
    # Nettoie les genres en supprimant les doublons ET les "&" 
    # SAUF pour "Stage & Screen" qui est un genre spécifique
    # Exemples :
    # - "Pop, Folk, World, & Country" => "Pop, Folk, World, Country"
    # - "Rock, Funk / Soul, Pop, Stage & Screen" => "Rock, Funk / Soul, Pop, Stage & Screen"
    
    if not genres_str:
        return ""
    
    # Décoder HTML
    genres = html.unescape(genres_str)
    
    # Protéger "Stage & Screen" en le remplaçant temporairement
    placeholder = "___STAGE_AND_SCREEN___"
    genres = genres.replace("Stage & Screen", placeholder)
    
    # Maintenant supprimer tous les autres "&"
    genres = genres.replace(' & ', ', ')
    genres = genres.replace('&', ',')
    
    # Restaurer "Stage & Screen"
    genres = genres.replace(placeholder, "Stage & Screen")
    
    # Séparer les genres pour supprimer les doublons
    genres_list = [g.strip() for g in genres.split(',')]
    
    # Supprimer les doublons tout en gardant l'ordre
    genres_uniques = []
    for genre in genres_list:
        if genre and genre not in genres_uniques:
            genres_uniques.append(genre)
    
    return ', '.join(genres_uniques)

def nettoyer_prix(prix_str):
    
    # Version simple : convertit toutes les virgules en points pour Excel
    
    if not prix_str:
        return ""
    
    # Décoder les entités HTML
    prix = html.unescape(prix_str)
    
    # Remplacer les espaces insécables par des espaces normaux
    prix = prix.replace('\u00a0', ' ').replace('\xa0', ' ')
    
    # Supprimer le symbole € et autres devises
    prix = prix.replace('€', '').replace('$', '').replace('£', '')
    
    # Supprimer tous les espaces
    prix = re.sub(r'\s+', '', prix)
    
    # Convertir TOUTES les virgules en points
    prix = prix.replace(',', '.')
    
    return prix.strip()

def nettoyer_nombre(nombre_str):
    
    # Nettoie les nombres en supprimant les espaces et en gardant seulement les chiffres
    # Exemple : "76 309" devient "76309"
    
    if not nombre_str:
        return ""
    
    # Supprimer tous les espaces et caractères non numériques sauf le point et la virgule
    nombre = re.sub(r'[^\d.,]', '', nombre_str.strip())
    
    return nombre

def nettoyer_pays(pays_str):
    
    # Nettoie les pays en supprimant les espaces en trop ET les "&"
    # Exemple : "UK, Europe & US" → "UK, Europe, US"
    
    if not pays_str:
        return ""
    
    # Décoder HTML et nettoyer
    pays = html.unescape(pays_str)
    
    # Supprimer tous les "&" et les remplacer par des virgules
    pays = pays.replace(' & ', ', ')
    pays = pays.replace('&', ',')
    
    # Nettoyer les virgules multiples et espaces
    pays = re.sub(r',\s*,+', ',', pays)  # Supprimer virgules multiples
    pays = re.sub(r'\s+', ' ', pays)     # Espaces multiples
    pays = pays.strip().strip(',')       # Espaces et virgules en début/fin
    
    return pays

def formater_date_pour_excel(date_str):
    
    # Convertit TOUTES les dates au format JJ/MM/AAAA pour Excel
    
    if not date_str:
        return ""
    
    try:
        date_str = date_str.strip()
        
        # Si c'est juste une année (4 chiffres)
        if re.match(r'^\d{4}$', date_str):
            return f"01/01/{date_str}"
        
        # Si c'est déjà au bon format JJ/MM/AAAA
        if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
            return date_str
        
        # Dictionnaire des mois français ET anglais
        mois_dict = {
            # Français
            'janv': '01', 'janvier': '01',
            'févr': '02', 'février': '02', 'fevrier': '02',
            'mars': '03',
            'avr': '04', 'avril': '04',
            'mai': '05',
            'juin': '06',
            'juil': '07', 'juillet': '07',
            'août': '08', 'aout': '08',
            'sept': '09', 'septembre': '09',
            'oct': '10', 'octobre': '10',
            'nov': '11', 'novembre': '11',
            'déc': '12', 'décembre': '12', 'decembre': '12',
        }
        
        # Pattern pour "22 oct. 2012" ou "4 nov. 2016" ou "15 Dec 2023"
        match_jour_mois_annee = re.search(r'(\d{1,2})\s+(\w+)\.?\s+(\d{4})', date_str, re.IGNORECASE)
        if match_jour_mois_annee:
            jour = match_jour_mois_annee.group(1).zfill(2)
            mois_txt = match_jour_mois_annee.group(2).lower().rstrip('.')
            annee = match_jour_mois_annee.group(3)
            
            if mois_txt in mois_dict:
                return f"{jour}/{mois_dict[mois_txt]}/{annee}"
        
        # Pattern pour "oct. 2012" ou "nov 2016" (sans jour)
        match_mois_annee = re.search(r'(\w+)\.?\s+(\d{4})', date_str, re.IGNORECASE)
        if match_mois_annee:
            mois_txt = match_mois_annee.group(1).lower().rstrip('.')
            annee = match_mois_annee.group(2)
            
            if mois_txt in mois_dict:
                return f"01/{mois_dict[mois_txt]}/{annee}"
        
        # Pattern pour format ISO "2023-05-15"
        match_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if match_iso:
            annee = match_iso.group(1)
            mois = match_iso.group(2)
            jour = match_iso.group(3)
            return f"{jour}/{mois}/{annee}"
        
        # Si rien ne marche, retourner tel quel
        return date_str
    
    except Exception as e:
        return date_str

def formater_derniere_vente(date_str):
    
    # Formate spécifiquement les dates de dernière vente
    # Exemple : "il y a 3 jours" => date calculée, "Dec 2023" => "01/12/2023"
    
    if not date_str:
        return ""
    
    date_str = date_str.strip().lower()
    
    # Gérer les dates relatives
    if 'il y a' in date_str or 'ago' in date_str:
        from datetime import datetime, timedelta
        aujourd_hui = datetime.now()
        
        # "il y a X jours"
        match_jours = re.search(r'(\d+)\s*(jour|day)', date_str)
        if match_jours:
            jours = int(match_jours.group(1))
            date_vente = aujourd_hui - timedelta(days=jours)
            return date_vente.strftime("%d/%m/%Y")
        
        # "il y a X mois"
        match_mois = re.search(r'(\d+)\s*(mois|month)', date_str)
        if match_mois:
            mois = int(match_mois.group(1))
            # Approximation : 1 mois = 30 jours
            date_vente = aujourd_hui - timedelta(days=mois*30)
            return date_vente.strftime("%d/%m/%Y")
    
    # Sinon utiliser la fonction générale
    return formater_date_pour_excel(date_str)

# -----------------------------------------------------------------------------
# ÉTAPE 1 : RÉCUPÉRER URLs + Artiste + Album DEPUIS LE CATALOGUE
# -----------------------------------------------------------------------------

def extraire_infos_catalogue(html_content):
    
    # Extrait URLs, artistes et albums depuis la page de catalogue
    
    soup = BeautifulSoup(html_content, 'html.parser')
    albums = []
    
    # Chercher toutes les div avec la classe card-release-title
    titres_divs = soup.find_all('div', class_='card-release-title')
    
    print(f"  → {len(titres_divs)} albums trouvés")
    
    for titre_div in titres_divs:
        try:
            # Extraire le lien et le titre de l'album
            lien_titre = titre_div.find('a', class_='search_result_title')
            if not lien_titre:
                continue
            
            # Récupérer le titre de l'album
            album = lien_titre.get('title', lien_titre.get_text(strip=True))
            
            # Récupérer le href et construire l'URL complète
            href = lien_titre.get('href', '')
            if not href:
                continue
            url_album = f"https://www.discogs.com{href}"
            
            # Trouver la div de l'artiste (juste après)
            artiste_div = titre_div.find_next_sibling('div', class_='card-artist-name')
            
            if artiste_div:
                # Chercher le lien de l'artiste
                lien_artiste = artiste_div.find('a')
                if lien_artiste:
                    artiste = lien_artiste.get('title', lien_artiste.get_text(strip=True))
                else:
                    # Si pas de lien, prendre le texte du span
                    span = artiste_div.find('span')
                    artiste = span.get('title', span.get_text(strip=True)) if span else "Inconnu"
            else:
                artiste = "Inconnu"
            
            # Ajouter à la liste avec nettoyage
            albums.append({
                'artiste': nettoyer_artiste(artiste.strip()),
                'album': nettoyer_album(album.strip()),
                'url': url_album
            })
        
        except Exception as e:
            continue
    
    return albums

def recuperer_infos_catalogue(page_debut=1, page_fin=200):
    
    # Récupère URLs, artistes et albums depuis les pages de catalogue avec retry
    
    tous_les_albums = []  
    
    print("="*70)
    print("ÉTAPE 1 : RÉCUPÉRATION DEPUIS LE CATALOGUE")
    print("="*70)
    print(f"Catalogue : Albums triés par popularité (have desc)")
    print(f"Pages à scraper : {page_debut} à {page_fin}\n")
    
    for page in range(page_debut, page_fin + 1):
        print(f"{'='*70}")
        print(f"Page {page}/{page_fin}")
        print(f"{'='*70}")
        
        url = f"https://www.discogs.com/fr/search/?sort=have%2Cdesc&type=release&page={page}"
        print(f"URL: {url}")
        
        try:
            # Tentative avec retry automatique
            response = crawl_get(url, wait_for_selector="div.card-release-title", max_retries=3)
            
            # Extraire les infos
            albums = extraire_infos_catalogue(response.html)
            
            if not albums:
                print(f"  Aucun album trouvé sur la page {page}")
                time.sleep(random.uniform(2, 4))  # MODIFIÉ: délai aléatoire
                continue
            
            tous_les_albums.extend(albums)
            print(f"  {len(albums)} albums extraits")
            print(f"  Total cumulé : {len(tous_les_albums)} albums")
            
            # Afficher un exemple
            if albums:
                exemple = albums[0]
                print(f"  Exemple : {exemple['artiste']} - {exemple['album']}")
            
            # MODIFIÉ: Pause aléatoire entre les pages (3-7 secondes)
            delai = random.uniform(3, 7)
            print(f"  ⏸️  Pause de {delai:.1f}s avant la page suivante...")
            time.sleep(delai)
        
        except Exception as e:
            print(f"  Page {page} ignorée après échec des tentatives: {e}")
            time.sleep(random.uniform(5, 10))  # MODIFIÉ: délai aléatoire plus long
            continue
    
    return tous_les_albums

# -----------------------------------------------------------------------------
# ÉTAPE 2 : ENRICHIR AVEC STATISTIQUES DE LA PAGE ALBUM
# -----------------------------------------------------------------------------

def extraire_infos_completes_album(html_content, url):
    
    # Extrait TOUTES les informations de la page album avec nettoyage AMÉLIORÉ
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialiser avec des valeurs par défaut
    infos = {
        'url': url,
        'label': '',
        'format': '',
        'pays': '',
        'date_sortie': '',
        'annee': '',
        'genres': '',
        'en_collection': '',
        'en_wantlist': '',
        'note_moyenne': '',
        'nombre_notes': '',
        'derniere_vente': '',
        'prix_faible': '',
        'prix_moyen': '',
        'prix_eleve': ''
    }
    
    try:
        # LABEL 
        labels = []
        label_links = soup.find_all('a', href=lambda x: x and '/label/' in x)
        for link in label_links:
            label_text = link.get_text(strip=True)
            if label_text and label_text not in labels:
                labels.append(label_text)
        infos['label'] = nettoyer_label(', '.join(labels))
        
        # FORMAT 
        formats = []
        format_links = soup.find_all('a', href=lambda x: x and 'format_exact=' in x)
        for link in format_links:
            format_text = link.get_text(strip=True)
            if format_text and format_text not in formats:
                formats.append(format_text)
        infos['format'] = nettoyer_format(', '.join(formats))
        
        # PAYS
        country_link = soup.find('a', href=lambda x: x and 'country=' in x)
        if country_link:
            infos['pays'] = nettoyer_pays(country_link.get_text(strip=True))  
        
        # DATE DE SORTIE ET ANNÉE
        time_tag = soup.find('time', datetime=True)
        if time_tag:
            date_brute = time_tag.get_text(strip=True)
            infos['date_sortie'] = formater_date_pour_excel(date_brute)
            datetime_value = time_tag.get('datetime', '')
            if datetime_value:
                infos['annee'] = datetime_value[:4]
        
        # GENRES
        genres = []
        genre_links = soup.find_all('a', href=lambda x: x and '/genre/' in x)
        for link in genre_links:
            genre_text = link.get_text(strip=True)
            if genre_text and genre_text not in genres:
                genres.append(genre_text)
        infos['genres'] = nettoyer_genres(', '.join(genres))  
        
        # STATISTIQUES 
        section_stats = soup.find('section', id='release-stats')
        if section_stats:
            items = section_stats.find_all('li')
            
            for item in items:
                try:
                    span_name = item.find('span', class_='name_qjn4_')
                    if not span_name:
                        continue
                    
                    nom_stat = span_name.get_text(strip=True).lower()
                    
                    # En Collection
                    if 'collection' in nom_stat:
                        link = item.find('a', class_='link_wXY7O')
                        if link:
                            infos['en_collection'] = nettoyer_nombre(link.get_text(strip=True))
                    
                    # En Wantlist
                    elif 'wantlist' in nom_stat:
                        link = item.find('a', class_='link_wXY7O')
                        if link:
                            infos['en_wantlist'] = nettoyer_nombre(link.get_text(strip=True))
                    
                    # Note Moyenne
                    elif 'note moyenne' in nom_stat or 'moyenne' in nom_stat:
                        spans = item.find_all('span')
                        for span in spans:
                            if span != span_name and '/' in span.get_text():
                                note_text = span.get_text(strip=True)
                                match = re.search(r'(\d+[.,]\d+)', note_text)
                                if match:
                                    infos['note_moyenne'] = match.group(1).replace(',', '.')
                                break
                    
                    # Nombre de Notes
                    elif 'notes:' in nom_stat or nom_stat == 'notes':
                        link = item.find('a', class_='link_wXY7O')
                        if link:
                            infos['nombre_notes'] = nettoyer_nombre(link.get_text(strip=True))
                    
                    # Dernière vente (MODIFIÉ)
                    elif 'dernière vente' in nom_stat or 'derniere vente' in nom_stat:
                        time_elem = item.find('time')
                        if time_elem:
                            date_brute = time_elem.get_text(strip=True)
                            infos['derniere_vente'] = formater_derniere_vente(date_brute)
                    
                    # Prix Faible (MODIFIÉ)
                    elif 'faible' in nom_stat:
                        spans = item.find_all('span')
                        for span in spans:
                            if span != span_name and ('€' in span.get_text() or '$' in span.get_text()):
                                infos['prix_faible'] = nettoyer_prix(span.get_text(strip=True))
                                break
                    
                    # Prix Moyen (MODIFIÉ)
                    elif 'prix moyen' in nom_stat or 'moyen' in nom_stat:
                        spans = item.find_all('span')
                        for span in spans:
                            if span != span_name and ('€' in span.get_text() or '$' in span.get_text()):
                                infos['prix_moyen'] = nettoyer_prix(span.get_text(strip=True))
                                break
                    
                    # Prix Élevé (MODIFIÉ)
                    elif 'élevée' in nom_stat or 'elevee' in nom_stat or 'élevé' in nom_stat:
                        spans = item.find_all('span')
                        for span in spans:
                            if span != span_name and ('€' in span.get_text() or '$' in span.get_text()):
                                infos['prix_eleve'] = nettoyer_prix(span.get_text(strip=True))
                                break
                
                except Exception as e:
                    continue
        
        return infos
    
    except Exception as e:
        print(f"    Erreur extraction : {e}")
        return infos

def enrichir_avec_details(albums, sauvegarder_tous_les=50):
    
    # Visite chaque URL d'album pour ajouter toutes les informations
    
    albums_enrichis = []
    total = len(albums)
    
    print("\n" + "="*70)
    print("ÉTAPE 2 : ENRICHISSEMENT COMPLET")
    print("="*70)
    print(f"\nTotal d'albums à enrichir : {total}")
    print("Cette étape peut prendre du temps (~3s par album)\n")
    
    for i, album in enumerate(albums, 1):
        print(f"[{i}/{total}] {album['artiste']} - {album['album']}")
        
        try:
            # Scraper la page de l'album
            response = crawl_get(album['url'])
            
            # Extraire TOUTES les informations
            infos = extraire_infos_completes_album(response.html, album['url'])
            
            # Fusionner avec les infos existantes
            album_enrichi = {**album, **infos}
            albums_enrichis.append(album_enrichi)
            
            print(f"  ✓ Label: {infos.get('label', 'N/A')[:40]}")
            print(f"    Format: {infos.get('format', 'N/A')}")
            print(f"    Année: {infos.get('annee', 'N/A')} | Genres: {infos.get('genres', 'N/A')[:30]}")
            print(f"    Collection: {infos.get('en_collection', 'N/A')} | Note: {infos.get('note_moyenne', 'N/A')}")
            
            # Sauvegardes périodiques
            if i % sauvegarder_tous_les == 0:
                print(f"\n  Sauvegarde intermédiaire ({i} albums)...")
                sauvegarder_csv_enrichi(albums_enrichis, f'discogs_enrichi_backup_{i}.csv')
                print()
            
            # MODIFIÉ: Pause aléatoire entre les albums (2-5 secondes)
            delai = random.uniform(2, 5)
            time.sleep(delai)
        
        except Exception as e:
            print(f"  Erreur : {e}")
            albums_enrichis.append(album)
            time.sleep(random.uniform(5, 10))  # MODIFIÉ: délai aléatoire plus long en cas d'erreur
            continue
    
    return albums_enrichis

# -----------------------------------------------------------------------------
# SAUVEGARDE
# -----------------------------------------------------------------------------

def sauvegarder_csv(albums, nom_fichier='discogs_albums.csv'):
    if not albums:
        return
    
    with open(nom_fichier, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['artiste', 'album', 'url']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(albums)
    
    print(f"  ✓ {len(albums)} albums sauvegardés dans '{nom_fichier}'")

def sauvegarder_csv_enrichi(albums, nom_fichier='discogs_albums_enrichi.csv'):
    """Sauvegarde avec toutes les colonnes enrichies"""
    if not albums:
        return
    
    with open(nom_fichier, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['artiste', 'album', 'url', 
                     'label', 'format', 'pays', 'date_sortie', 'annee', 'genres',
                     'en_collection', 'en_wantlist', 'note_moyenne', 'nombre_notes', 
                     'derniere_vente', 'prix_faible', 'prix_moyen', 'prix_eleve']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(albums)
    
    print(f"  ✓ {len(albums)} albums sauvegardés dans '{nom_fichier}'")

def sauvegarder_urls(urls, nom_fichier='discogs_urls.txt'):
    with open(nom_fichier, 'w', encoding='utf-8') as f:
        for item in urls:
            if isinstance(item, dict):
                f.write(item['url'] + '\n')
            else:
                f.write(item + '\n')
    print(f"✓ {len(urls)} URLs sauvegardées dans '{nom_fichier}'")

# -----------------------------------------------------------------------------
# EXÉCUTION PRINCIPALE
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SCRAPER DISCOGS - Albums les plus populaires")
    print("="*70)
    print("\nCatalogue utilisé : Most Collected")
    print("="*70)
    print("\nÉtape 1 : Récupération Artiste + Album + URL")
    print("Étape 2 : Enrichissement avec statistiques complètes")
    
    # Configuration
    choix = input("\nScraper 200 pages du catalogue ? (oui/non) : ").strip().lower()
    
    if choix not in ['oui', 'o', 'yes', 'y']:
        print("\nMode TEST")
        page_debut = int(input("Page de début (défaut=1) : ").strip() or "1")
        page_fin = int(input("Page de fin (défaut=2) : ").strip() or "2")
    else:
        page_debut = 1
        page_fin = 200
    
    print(f"\nDémarrage...\n")
    debut_total = time.time()
    
    # ÉTAPE 1 : Récupérer toutes les infos depuis le catalogue
    albums = recuperer_infos_catalogue(page_debut=page_debut, page_fin=page_fin)
    
    if not albums:
        print("\nAucun album récupéré. Arrêt.")
        exit()
    
    print(f"\n{'='*70}")
    print(f"ÉTAPE 1 TERMINÉE : {len(albums)} albums récupérés")
    print(f"{'='*70}")
    
    # Sauvegarder immédiatement
    sauvegarder_csv(albums, 'discogs_albums_etape1.csv')
    sauvegarder_urls(albums, 'discogs_urls.txt')
    
    # Demander si on veut enrichir avec l'étape 2
    print(f"\n{'='*70}")
    print("OPTIONS")
    print(f"{'='*70}")
    print("\nVous avez déjà toutes les infos de base :")
    print("  - Artiste, Album, URL")
    print("\nL'étape 2 ajoute les statistiques :")
    print("  - En Collection, En Wantlist")
    print("  - Note moyenne, Nombre de notes")
    print("  - Dernière vente")
    print("  - Prix : Faible, Moyen, Élevé")
    print(f"\nTemps estimé : ~{len(albums)*3/60:.0f} minutes pour {len(albums)} albums")
    
    enrichir = input("\nEnrichir avec l'étape 2 ? (oui/non) : ").strip().lower()
    
    if enrichir in ['oui', 'o', 'yes', 'y']:
        # ÉTAPE 2 : Enrichir
        albums_enrichis = enrichir_avec_details(albums, sauvegarder_tous_les=50)
    else:
        albums_enrichis = albums
        print("\n✓ Étape 2 ignorée")
    
    duree_totale = time.time() - debut_total
    
    # RÉSULTATS FINAUX
    print(f"\n{'='*70}")
    print(f"SCRAPING TERMINÉ !")
    print(f"{'='*70}")
    print(f"Albums récupérés : {len(albums_enrichis)}")
    print(f"Temps total : {duree_totale/60:.2f} minutes")
    print(f"Vitesse : {len(albums_enrichis)/(duree_totale/60):.1f} albums/minute")
    
    if albums_enrichis:
        print(f"\nAperçu des 10 premiers résultats :")
        print("-"*70)
        for i, album in enumerate(albums_enrichis[:10], 1):
            print(f"{i:3d}. {album['artiste'][:30]:30s} - {album['album'][:35]}")
            if 'note_moyenne' in album:
                print(f"     Note: {album.get('note_moyenne', 'N/A')} | Collection: {album.get('en_collection', 'N/A')}")
        
        if len(albums_enrichis) > 10:
            print(f"\n... et {len(albums_enrichis) - 10} autres")
        
        # Sauvegarde finale
        if enrichir in ['oui', 'o', 'yes', 'y']:
            sauvegarder_csv_enrichi(albums_enrichis, 'discogs_albums_final.csv')
        else:
            sauvegarder_csv(albums_enrichis, 'discogs_albums_final.csv')
        
        print(f"\n{'='*70}")
        print("LE SCRAPING EST GOOD !")
        print(f"{'='*70}")
        print(f"\nFichiers créés :")
        print(f"  - discogs_albums_etape1.csv : Données du catalogue")
        print(f"  - discogs_albums_final.csv : Données finales")
        print(f"  - discogs_urls.txt : Liste des URLs")
        if enrichir in ['oui', 'o', 'yes', 'y']:
            print(f"  - discogs_enrichi_backup_X.csv : Sauvegardes intermédiaires")