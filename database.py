"""
Module de gestion de la base de données SQLite
Gère le stockage des factures, lignes de produits, catalogue et stocks.
"""

import sqlite3
import os
from datetime import datetime
from app_path import app_path

DB_PATH = app_path("facturation.db")


def get_connection():
    """Retourne une connexion à la base de données."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise la base de données et crée les tables si elles n'existent pas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # ── Familles d'articles ────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS familles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            couleur TEXT DEFAULT '#1a56db',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table des factures
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_facture TEXT UNIQUE NOT NULL,
            client TEXT NOT NULL,
            telephone TEXT,
            date_facture TEXT NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table des lignes de facture
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lignes_facture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facture_id INTEGER NOT NULL,
            designation TEXT NOT NULL,
            quantite REAL NOT NULL,
            prix_unitaire REAL NOT NULL,
            montant REAL NOT NULL,
            FOREIGN KEY (facture_id) REFERENCES factures(id)
        )
    """)

    # Table du catalogue de produits
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalogue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT DEFAULT '',
            designation TEXT NOT NULL,
            prix_achat REAL NOT NULL DEFAULT 0,
            prix_unitaire REAL NOT NULL,
            description TEXT DEFAULT '',
            code_barre TEXT DEFAULT '',
            famille_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (famille_id) REFERENCES familles(id) ON DELETE SET NULL
        )
    """)

    # ── STOCK : niveau actuel par produit du catalogue ─────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalogue_id INTEGER NOT NULL UNIQUE,
            stock_actuel REAL NOT NULL DEFAULT 0,
            seuil_alerte REAL NOT NULL DEFAULT 5,
            FOREIGN KEY (catalogue_id) REFERENCES catalogue(id) ON DELETE CASCADE
        )
    """)

    # ── STOCK : historique des mouvements ────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_mouvements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalogue_id INTEGER NOT NULL,
            type_mouvement TEXT NOT NULL,
            quantite REAL NOT NULL,
            stock_avant REAL NOT NULL,
            stock_apres REAL NOT NULL,
            note TEXT DEFAULT '',
            date_mouvement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (catalogue_id) REFERENCES catalogue(id)
        )
    """)

    # ── Sessions de caisse ────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS caisses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_ouverture TIMESTAMP NOT NULL,
            date_cloture TIMESTAMP DEFAULT NULL,
            montant_ouverture REAL NOT NULL DEFAULT 0,
            montant_cloture_theorique REAL DEFAULT NULL,
            montant_cloture_reel REAL DEFAULT NULL,
            ecart REAL DEFAULT NULL,
            note_cloture TEXT DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'ouverte',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Mouvements de caisse ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mouvements_caisse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caisse_id INTEGER NOT NULL,
            type_mouvement TEXT NOT NULL,
            montant REAL NOT NULL,
            libelle TEXT DEFAULT '',
            reference TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (caisse_id) REFERENCES caisses(id)
        )
    """)

    # ── Méthodes de paiement ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS methodes_paiement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            actif INTEGER NOT NULL DEFAULT 1,
            ordre INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Migrations pour bases existantes ──────────────────────────────────────
    for col, ddl in [
        ("code_barre",  "ALTER TABLE catalogue ADD COLUMN code_barre TEXT DEFAULT ''"),
        ("reference",   "ALTER TABLE catalogue ADD COLUMN reference TEXT DEFAULT ''"),
        ("famille_id",  "ALTER TABLE catalogue ADD COLUMN famille_id INTEGER DEFAULT NULL"),
        ("prix_achat",  "ALTER TABLE catalogue ADD COLUMN prix_achat REAL NOT NULL DEFAULT 0"),
        ("methode_paiement", "ALTER TABLE factures ADD COLUMN methode_paiement TEXT DEFAULT ''"),
        ("type_document",    "ALTER TABLE factures ADD COLUMN type_document TEXT DEFAULT 'facture'"),
    ]:
        try:
            cursor.execute(ddl)
        except Exception:
            pass

    # Méthodes de paiement par défaut si table vide
    cursor.execute("SELECT COUNT(*) as n FROM methodes_paiement")
    if cursor.fetchone()["n"] == 0:
        for i, nom in enumerate(["Espèces"]):
            cursor.execute(
                "INSERT INTO methodes_paiement (nom, actif, ordre) VALUES (?, 1, ?)",
                (nom, i)
            )

    conn.commit()
    conn.close()


# ─── FAMILLES D'ARTICLES ───────────────────────────────────────────────────────

def get_familles() -> list:
    """Retourne toutes les familles triées par nom."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM familles ORDER BY nom COLLATE NOCASE")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_famille(nom: str, description: str = "", couleur: str = "#1a56db") -> int:
    """Crée une nouvelle famille. Retourne l'ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO familles (nom, description, couleur) VALUES (?, ?, ?)",
        (nom.strip(), description.strip(), couleur)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_famille(famille_id: int, nom: str, description: str = "", couleur: str = "#1a56db"):
    """Met à jour une famille."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE familles SET nom=?, description=?, couleur=? WHERE id=?",
        (nom.strip(), description.strip(), couleur, famille_id)
    )
    conn.commit()
    conn.close()


def delete_famille(famille_id: int):
    """Supprime une famille (les articles liés passent à famille_id=NULL)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("UPDATE catalogue SET famille_id=NULL WHERE famille_id=?", (famille_id,))
    cursor.execute("DELETE FROM familles WHERE id=?", (famille_id,))
    conn.commit()
    conn.close()


def get_next_reference() -> str:
    """Génère la prochaine référence article au format ART-XXXX."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reference FROM catalogue WHERE reference LIKE 'ART-%' ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if row and row["reference"]:
        try:
            num = int(row["reference"].split("-")[-1])
            return f"ART-{num + 1:04d}"
        except Exception:
            pass
    return "ART-0001"


# ─── CATALOGUE PRODUITS ────────────────────────────────────────────────────────

def get_catalogue(famille_id=None) -> list:
    """Retourne les produits du catalogue avec leur famille, filtrés si famille_id fourni."""
    conn = get_connection()
    cursor = conn.cursor()
    if famille_id is not None:
        cursor.execute("""
            SELECT c.*, f.nom as famille_nom, f.couleur as famille_couleur
            FROM catalogue c
            LEFT JOIN familles f ON f.id = c.famille_id
            WHERE c.famille_id = ?
            ORDER BY c.designation COLLATE NOCASE
        """, (famille_id,))
    else:
        cursor.execute("""
            SELECT c.*, f.nom as famille_nom, f.couleur as famille_couleur
            FROM catalogue c
            LEFT JOIN familles f ON f.id = c.famille_id
            ORDER BY c.designation COLLATE NOCASE
        """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_catalogue_product(designation, prix_unitaire, description="", code_barre="",
                           reference="", famille_id=None, prix_achat=0.0):
    """Ajoute un produit au catalogue. Retourne l'ID créé."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO catalogue
           (reference, designation, prix_achat, prix_unitaire, description, code_barre, famille_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (reference.strip(), designation, float(prix_achat),
         prix_unitaire, description, code_barre.strip(), famille_id)
    )
    new_id = cursor.lastrowid
    cursor.execute(
        "INSERT OR IGNORE INTO stock (catalogue_id, stock_actuel, seuil_alerte) VALUES (?, 0, 5)",
        (new_id,)
    )
    conn.commit()
    conn.close()
    return new_id


def update_catalogue_product(product_id, designation, prix_unitaire, description="",
                              code_barre="", reference="", famille_id=None, prix_achat=0.0):
    """Met à jour un produit du catalogue."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE catalogue
           SET reference=?, designation=?, prix_achat=?, prix_unitaire=?,
               description=?, code_barre=?, famille_id=?
           WHERE id=?""",
        (reference.strip(), designation, float(prix_achat), prix_unitaire,
         description, code_barre.strip(), famille_id, product_id)
    )
    cursor.execute(
        "INSERT OR IGNORE INTO stock (catalogue_id, stock_actuel, seuil_alerte) VALUES (?, 0, 5)",
        (product_id,)
    )
    conn.commit()
    conn.close()


def delete_catalogue_product(product_id):
    """Supprime un produit du catalogue (et son stock via CASCADE)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM catalogue WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


def search_catalogue(query, famille_id=None) -> list:
    """Recherche dans le catalogue par référence, désignation, description ou code-barres."""
    conn = get_connection()
    cursor = conn.cursor()
    like = f"%{query}%"
    if famille_id is not None:
        cursor.execute("""
            SELECT c.*, f.nom as famille_nom, f.couleur as famille_couleur
            FROM catalogue c
            LEFT JOIN familles f ON f.id = c.famille_id
            WHERE c.famille_id = ?
              AND (c.reference LIKE ? OR c.designation LIKE ?
                   OR c.description LIKE ? OR c.code_barre LIKE ?)
            ORDER BY c.designation COLLATE NOCASE
        """, (famille_id, like, like, like, like))
    else:
        cursor.execute("""
            SELECT c.*, f.nom as famille_nom, f.couleur as famille_couleur
            FROM catalogue c
            LEFT JOIN familles f ON f.id = c.famille_id
            WHERE c.reference LIKE ? OR c.designation LIKE ?
               OR c.description LIKE ? OR c.code_barre LIKE ?
            ORDER BY c.designation COLLATE NOCASE
        """, (like, like, like, like))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product_by_barcode(code_barre: str):
    """Recherche exacte par code-barres."""
    if not code_barre:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, f.nom as famille_nom, f.couleur as famille_couleur
        FROM catalogue c
        LEFT JOIN familles f ON f.id = c.famille_id
        WHERE c.code_barre = ? COLLATE NOCASE
    """, (code_barre.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_product_by_reference(reference: str):
    """Recherche exacte par référence article."""
    if not reference:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, f.nom as famille_nom, f.couleur as famille_couleur
        FROM catalogue c
        LEFT JOIN familles f ON f.id = c.famille_id
        WHERE c.reference = ? COLLATE NOCASE
    """, (reference.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# ─── STOCK ────────────────────────────────────────────────────────────────────

def _ensure_stock_rows():
    """Crée les lignes stock manquantes pour les produits du catalogue."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO stock (catalogue_id, stock_actuel, seuil_alerte)
        SELECT id, 0, 5 FROM catalogue
    """)
    conn.commit()
    conn.close()


def get_all_stock():
    """Retourne le stock de tous les produits du catalogue (avec désignation et prix)."""
    _ensure_stock_rows()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.catalogue_id, s.stock_actuel, s.seuil_alerte,
               c.designation, c.prix_unitaire
        FROM stock s
        JOIN catalogue c ON c.id = s.catalogue_id
        ORDER BY c.designation COLLATE NOCASE
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stock_produit(catalogue_id):
    """Retourne le stock actuel d'un produit."""
    _ensure_stock_rows()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stock_actuel FROM stock WHERE catalogue_id=?", (catalogue_id,))
    row = cursor.fetchone()
    conn.close()
    return row["stock_actuel"] if row else 0.0


def get_seuil_alerte(catalogue_id):
    """Retourne le seuil d'alerte d'un produit."""
    _ensure_stock_rows()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT seuil_alerte FROM stock WHERE catalogue_id=?", (catalogue_id,))
    row = cursor.fetchone()
    conn.close()
    return row["seuil_alerte"] if row else 5.0


def set_seuil_alerte(catalogue_id, seuil):
    """Met à jour le seuil d'alerte d'un produit."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE stock SET seuil_alerte=? WHERE catalogue_id=?",
        (seuil, catalogue_id)
    )
    conn.commit()
    conn.close()


class StockInsuffisantError(Exception):
    """Levée quand une sortie de stock ferait passer le niveau sous 0."""
    def __init__(self, catalogue_id: int, stock_disponible: float,
                 quantite_demandee: float):
        self.catalogue_id       = catalogue_id
        self.stock_disponible   = stock_disponible
        self.quantite_demandee  = quantite_demandee
        super().__init__(
            f"Stock insuffisant : disponible={stock_disponible:g}, "
            f"demandé={quantite_demandee:g}"
        )


def ajouter_mouvement_stock(catalogue_id, type_mouvement, quantite, note=""):
    """
    Enregistre un mouvement de stock (entrée, sortie ou facture).
    Pour les sorties, lève StockInsuffisantError si le stock passerait sous 0.

    Args:
        catalogue_id : ID du produit dans le catalogue
        type_mouvement : 'entree' | 'sortie' | 'facture'
        quantite : quantité (toujours positive)
        note : commentaire optionnel
    """
    _ensure_stock_rows()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT stock_actuel FROM stock WHERE catalogue_id=?", (catalogue_id,))
        row = cursor.fetchone()
        stock_avant = row["stock_actuel"] if row else 0.0

        if type_mouvement == "entree":
            stock_apres = stock_avant + quantite
        else:  # sortie ou facture
            stock_apres = stock_avant - quantite
            # ── Plancher à 0 : jamais en dessous ─────────────────────────────
            if stock_apres < 0:
                conn.close()
                raise StockInsuffisantError(
                    catalogue_id=catalogue_id,
                    stock_disponible=stock_avant,
                    quantite_demandee=quantite,
                )

        cursor.execute(
            "UPDATE stock SET stock_actuel=? WHERE catalogue_id=?",
            (stock_apres, catalogue_id)
        )
        cursor.execute("""
            INSERT INTO stock_mouvements
                (catalogue_id, type_mouvement, quantite, stock_avant, stock_apres, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (catalogue_id, type_mouvement, quantite, stock_avant, stock_apres, note))

        conn.commit()
    except StockInsuffisantError:
        raise
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_stock_mouvements(catalogue_id=None, limit=200):
    """Retourne l'historique des mouvements de stock (récents en premier)."""
    conn = get_connection()
    cursor = conn.cursor()
    if catalogue_id:
        cursor.execute("""
            SELECT m.*, c.designation
            FROM stock_mouvements m
            JOIN catalogue c ON c.id = m.catalogue_id
            WHERE m.catalogue_id = ?
            ORDER BY m.date_mouvement DESC LIMIT ?
        """, (catalogue_id, limit))
    else:
        cursor.execute("""
            SELECT m.*, c.designation
            FROM stock_mouvements m
            JOIN catalogue c ON c.id = m.catalogue_id
            ORDER BY m.date_mouvement DESC LIMIT ?
        """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stock_alerts():
    """Retourne les produits en rupture ou en stock bas."""
    _ensure_stock_rows()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.stock_actuel, s.seuil_alerte, c.designation
        FROM stock s
        JOIN catalogue c ON c.id = s.catalogue_id
        WHERE s.stock_actuel <= s.seuil_alerte
        ORDER BY s.stock_actuel ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def deduire_stock_article(catalogue_id: int, quantite: float, note: str = "Vente"):
    """
    Déduit le stock d'un article spécifique immédiatement (à l'ajout d'une ligne).
    """
    if catalogue_id and catalogue_id > 0:
        ajouter_mouvement_stock(catalogue_id, "sortie", quantite, note)


def restituer_stock_article(catalogue_id: int, quantite: float, note: str = "Annulation ligne"):
    """
    Restitue le stock quand une ligne est supprimée de la facture en cours.
    """
    if catalogue_id and catalogue_id > 0:
        ajouter_mouvement_stock(catalogue_id, "entree", quantite, note)


def deduire_stock_facture(lignes_facture, numero_facture=""):
    """
    Déduit automatiquement le stock pour chaque ligne d'une facture.
    Tente de trouver le produit catalogue par désignation exacte.
    Retourne la liste des produits non trouvés dans le catalogue.
    """
    non_trouves = []
    conn = get_connection()
    cursor = conn.cursor()

    for ligne in lignes_facture:
        designation = ligne[0] if isinstance(ligne, (list, tuple)) else ligne.get("designation", "")
        quantite    = ligne[1] if isinstance(ligne, (list, tuple)) else ligne.get("quantite", 0)

        # Chercher le produit dans le catalogue par désignation exacte
        cursor.execute(
            "SELECT id FROM catalogue WHERE designation = ? COLLATE NOCASE",
            (designation,)
        )
        row = cursor.fetchone()
        if row:
            cat_id = row["id"]
            conn.close()
            note = f"Facture {numero_facture}" if numero_facture else "Vente"
            ajouter_mouvement_stock(cat_id, "facture", quantite, note)
            conn = get_connection()
            cursor = conn.cursor()
        else:
            non_trouves.append(designation)

    conn.close()
    return non_trouves


# ─── FACTURES ─────────────────────────────────────────────────────────────────

def get_next_invoice_number():
    """
    Génère le prochain numéro de facture au format FAC-AAAA-XXXX.
    Réinitialise le compteur à chaque nouvelle année.
    """
    conn = get_connection()
    cursor = conn.cursor()
    current_year = datetime.now().year

    cursor.execute("""
        SELECT numero_facture FROM factures
        WHERE numero_facture LIKE ?
        ORDER BY id DESC LIMIT 1
    """, (f"FAC-{current_year}-%",))

    row = cursor.fetchone()
    conn.close()

    if row:
        last_num = int(row["numero_facture"].split("-")[-1])
        return f"FAC-{current_year}-{last_num + 1:04d}"
    else:
        return f"FAC-{current_year}-0001"


def save_invoice(numero, client, telephone, date_facture, total, lignes):
    """
    Enregistre une facture et ses lignes dans la base de données.
    Le stock est déjà déduit au moment de l'ajout des articles (pas ici).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO factures (numero_facture, client, telephone, date_facture, total)
            VALUES (?, ?, ?, ?, ?)
        """, (numero, client, telephone, date_facture, total))
        facture_id = cursor.lastrowid
        for ligne in lignes:
            cursor.execute("""
                INSERT INTO lignes_facture (facture_id, designation, quantite, prix_unitaire, montant)
                VALUES (?, ?, ?, ?, ?)
            """, (facture_id, ligne[0], ligne[1], ligne[2], ligne[3]))
        conn.commit()
        return facture_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_all_invoices():
    """Retourne toutes les factures triées par date décroissante."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM factures ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_invoice_lines(facture_id):
    """Retourne les lignes d'une facture spécifique."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lignes_facture WHERE facture_id = ?", (facture_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_invoices(query):
    """Recherche des factures par numéro ou nom de client."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM factures
        WHERE numero_facture LIKE ? OR client LIKE ?
        ORDER BY created_at DESC
    """, (f"%{query}%", f"%{query}%"))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_statistics():
    """Retourne des statistiques simples sur les factures."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total_factures, SUM(total) as chiffre_affaires FROM factures")
    stats = dict(cursor.fetchone())

    current_month = datetime.now().strftime("%Y-%m")
    cursor.execute("""
        SELECT COUNT(*) as factures_mois, SUM(total) as ca_mois
        FROM factures WHERE date_facture LIKE ?
    """, (f"{current_month}%",))
    month_stats = dict(cursor.fetchone())

    conn.close()
    return {**stats, **month_stats}


# ─── CAISSE ───────────────────────────────────────────────────────────────────

def get_session_ouverte():
    """Retourne la session de caisse actuellement ouverte, ou None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM caisses WHERE statut='ouverte' ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def ouvrir_session_caisse(montant_ouverture: float, note: str = "") -> int:
    """Ouvre une nouvelle session de caisse. Retourne l'ID."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """INSERT INTO caisses (date_ouverture, montant_ouverture, statut, note_cloture)
           VALUES (?, ?, 'ouverte', ?)""",
        (now, montant_ouverture, note)
    )
    new_id = cursor.lastrowid
    # Enregistrer le fond de caisse comme mouvement d'entrée
    if montant_ouverture > 0:
        cursor.execute(
            """INSERT INTO mouvements_caisse (caisse_id, type_mouvement, montant, libelle)
               VALUES (?, 'entree', ?, 'Fond de caisse ouverture')""",
            (new_id, montant_ouverture)
        )
    conn.commit()
    conn.close()
    return new_id


def cloturer_session_caisse(caisse_id: int, montant_reel: float, note: str = ""):
    """Clôture une session de caisse et calcule l'écart."""
    conn = get_connection()
    cursor = conn.cursor()
    # Calcul du montant théorique : fond + toutes les entrées - toutes les sorties
    cursor.execute("""
        SELECT COALESCE(SUM(CASE WHEN type_mouvement='entree' THEN montant
                               WHEN type_mouvement='sortie' THEN -montant
                               ELSE 0 END), 0) as theorique
        FROM mouvements_caisse WHERE caisse_id=?
    """, (caisse_id,))
    theorique = cursor.fetchone()["theorique"]
    ecart = montant_reel - theorique
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE caisses SET statut='cloturee', date_cloture=?,
            montant_cloture_theorique=?, montant_cloture_reel=?,
            ecart=?, note_cloture=?
        WHERE id=?
    """, (now, theorique, montant_reel, ecart, note, caisse_id))
    conn.commit()
    conn.close()
    return {"theorique": theorique, "reel": montant_reel, "ecart": ecart}


def ajouter_mouvement_caisse(caisse_id: int, type_mouvement: str,
                              montant: float, libelle: str = "", reference: str = ""):
    """Ajoute un mouvement (entree/sortie) dans la session de caisse."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO mouvements_caisse
           (caisse_id, type_mouvement, montant, libelle, reference)
           VALUES (?, ?, ?, ?, ?)""",
        (caisse_id, type_mouvement, montant, libelle, reference)
    )
    conn.commit()
    conn.close()


def get_mouvements_caisse(caisse_id: int) -> list:
    """Retourne tous les mouvements d'une session (récents en premier)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM mouvements_caisse WHERE caisse_id=?
           ORDER BY created_at ASC""",
        (caisse_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_solde_caisse(caisse_id: int) -> float:
    """Calcule le solde théorique actuel de la caisse."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(CASE WHEN type_mouvement='entree' THEN montant
                               WHEN type_mouvement='sortie' THEN -montant
                               ELSE 0 END), 0) as solde
        FROM mouvements_caisse WHERE caisse_id=?
    """, (caisse_id,))
    row = cursor.fetchone()
    conn.close()
    return row["solde"] if row else 0.0


def get_all_sessions_caisse() -> list:
    """Retourne toutes les sessions de caisse (récentes en premier)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM caisses ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def enregistrer_vente_en_caisse(caisse_id: int, numero_facture: str, montant: float):
    """Enregistre une vente comme entrée de caisse automatiquement."""
    ajouter_mouvement_caisse(
        caisse_id, "entree", montant,
        libelle=f"Vente facture {numero_facture}",
        reference=numero_facture
    )


def get_rapport_ventes_jour(date_str: str) -> dict:
    """
    Retourne le rapport complet des ventes pour une date donnée (format DD/MM/YYYY ou YYYY-MM-DD).
    Inclut : liste des produits vendus, quantités, montants, total.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Normaliser la date en DD/MM/YYYY (format stocké dans factures)
    if "-" in date_str and date_str.index("-") == 4:
        # Format YYYY-MM-DD → DD/MM/YYYY
        from datetime import datetime as dt
        d = dt.strptime(date_str, "%Y-%m-%d")
        date_fmt = d.strftime("%d/%m/%Y")
    else:
        date_fmt = date_str

    # Factures du jour
    cursor.execute(
        "SELECT * FROM factures WHERE date_facture=? ORDER BY created_at",
        (date_fmt,)
    )
    factures = [dict(r) for r in cursor.fetchall()]

    if not factures:
        conn.close()
        return {
            "date": date_fmt, "factures": [], "produits": [],
            "nb_factures": 0, "total_jour": 0.0
        }

    facture_ids = [f["id"] for f in factures]

    # Agrégation par produit
    placeholders = ",".join("?" * len(facture_ids))
    cursor.execute(f"""
        SELECT designation,
               SUM(quantite) as quantite_totale,
               AVG(prix_unitaire) as prix_moyen,
               SUM(montant) as montant_total
        FROM lignes_facture
        WHERE facture_id IN ({placeholders})
        GROUP BY designation
        ORDER BY montant_total DESC
    """, facture_ids)
    produits = [dict(r) for r in cursor.fetchall()]

    total_jour = sum(f["total"] for f in factures)
    conn.close()

    return {
        "date":        date_fmt,
        "factures":    factures,
        "produits":    produits,
        "nb_factures": len(factures),
        "total_jour":  total_jour,
    }


# ─── MÉTHODES DE PAIEMENT ─────────────────────────────────────────────────────

def get_methodes_paiement(actif_seulement=True) -> list:
    """Retourne les méthodes de paiement triées par ordre."""
    conn = get_connection()
    cursor = conn.cursor()
    if actif_seulement:
        cursor.execute(
            "SELECT * FROM methodes_paiement WHERE actif=1 ORDER BY ordre, nom COLLATE NOCASE"
        )
    else:
        cursor.execute(
            "SELECT * FROM methodes_paiement ORDER BY ordre, nom COLLATE NOCASE"
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_methode_paiement(nom: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(ordre),0)+1 as next_ordre FROM methodes_paiement")
    ordre = cursor.fetchone()["next_ordre"]
    cursor.execute(
        "INSERT INTO methodes_paiement (nom, actif, ordre) VALUES (?, 1, ?)",
        (nom.strip(), ordre)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_methode_paiement(mid: int, nom: str, actif: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE methodes_paiement SET nom=?, actif=? WHERE id=?",
        (nom.strip(), 1 if actif else 0, mid)
    )
    conn.commit()
    conn.close()


def delete_methode_paiement(mid: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM methodes_paiement WHERE id=?", (mid,))
    conn.commit()
    conn.close()


def reorder_methodes_paiement(ids: list):
    """Réordonne les méthodes selon la liste d'IDs fournie."""
    conn = get_connection()
    cursor = conn.cursor()
    for i, mid in enumerate(ids):
        cursor.execute("UPDATE methodes_paiement SET ordre=? WHERE id=?", (i, mid))
    conn.commit()
    conn.close()