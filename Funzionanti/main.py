import os
import sqlite3
import sys
import threading
from datetime import datetime
import flet as ft
import speech_recognition as sr

# --- GESTIONE DATABASE SQLITE ---
DB_NAME = "appunti.db"


def init_db():
    """Crea il database e la tabella se non esistono."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anteprima TEXT,
            contenuto TEXT,
            data TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def carica_note_db():
    """Legge tutte le note ordinate dalla più recente."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, anteprima, contenuto, data FROM note ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    note = []
    for r in rows:
        note.append({"id": r[0], "anteprima": r[1], "contenuto": r[2], "data": r[3]})
    return note


def inserisci_nota_db(anteprima, contenuto, data):
    """Salva una nuova nota nel DB e restituisce il suo ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO note (anteprima, contenuto, data) VALUES (?, ?, ?)",
        (anteprima, contenuto, data),
    )
    conn.commit()
    nuovo_id = cursor.lastrowid
    conn.close()
    return nuovo_id


def aggiorna_nota_db(nota_id, anteprima, contenuto):
    """Aggiorna una nota esistente nel database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE note SET anteprima = ?, contenuto = ? WHERE id = ?",
        (anteprima, contenuto, nota_id),
    )
    conn.commit()
    conn.close()


# --- Forzatura Icona Nativa su Windows ---
if sys.platform == "win32":
    import ctypes

    myappid = "spsoft.appunti.notesapp.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


def estrai_anteprima_due_righe(testo_completo):
    """Estrae fino a 2 righe di testo reale ignorando l'intestazione con la data."""
    righe = [r.strip() for r in testo_completo.strip().split("\n") if r.strip()]
    righe_valide = []

    for riga in righe:
        if not (riga.startswith("[") and riga.endswith("]") and len(riga) <= 20):
            righe_valide.append(riga)

    if not righe_valide:
        return "Nuovo Appunto"

    return "\n".join(righe_valide[:2])


def main(page: ft.Page):
    # Inizializzazione DB e caricamento note salvate
    init_db()
    note_list = carica_note_db()

    page.title = "Appunti - SPsoft"

    icona_relativa = "logo.ico"
    page.window.icon = icona_relativa

    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 15

    BG_CARTA = "#FDF6E3"
    CARD_BG = "#F4E8C1"
    TEXT_COLOR = "#2B2B2B"
    BORDER_COLOR = "#8B5A2B"

    page.bgcolor = BG_CARTA

    nota_selezionata_idx = None

    status_label = ft.Text("Pronto", italic=True, color="gray", size=13)

    # --- Viste dell'Applicazione ---
    vista_lista = ft.Column(spacing=10, expand=True)
    vista_dettaglio = ft.Column(spacing=10, visible=False, expand=True)

    txt_contenuto = ft.TextField(
        multiline=True,
        min_lines=8,
        max_lines=12,
        bgcolor=CARD_BG,
        border_color="#D3C193",
        focused_border_color=BORDER_COLOR,
        text_style=ft.TextStyle(color=TEXT_COLOR, size=16, font_family="Courier New"),
        cursor_color=BORDER_COLOR,
        expand=True,
    )

    lbl_titolo_dettaglio = ft.Text(
        "", weight=ft.FontWeight.BOLD, size=16, color="#5C3A21"
    )

    # --- Logica Navigazione ---
    def mostra_home(e=None):
        vista_lista.visible = True
        vista_dettaglio.visible = False
        aggiorna_lista_ui()
        page.update()

    def apri_dettaglio(idx):
        nonlocal nota_selezionata_idx
        nota_selezionata_idx = idx
        nota = note_list[idx]

        lbl_titolo_dettaglio.value = nota["anteprima"].replace("\n", " ")[:30] + "..."
        txt_contenuto.value = nota["contenuto"]

        vista_lista.visible = False
        vista_dettaglio.visible = True
        page.update()

    def crea_nuova_nota_manuale(e=None):
        ora_attuale = datetime.now().strftime("%d/%m/%Y %H:%M")
        contenuto_iniziale = f"[{ora_attuale}]\n"
        anteprima = "Nuova Nota"

        # Salva subito la nuova nota nel database SQLite
        nuovo_id = inserisci_nota_db(anteprima, contenuto_iniziale, ora_attuale)

        nuova_nota = {
            "id": nuovo_id,
            "anteprima": anteprima,
            "contenuto": contenuto_iniziale,
            "data": ora_attuale,
        }
        note_list.insert(0, nuova_nota)
        apri_dettaglio(0)

    # --- Salvataggio e Dettatura ---
    def esegui_salvataggio_automatico(testo_completo):
        if testo_completo and testo_completo.strip():
            anteprima = estrai_anteprima_due_righe(testo_completo)
            ora_attuale = datetime.now().strftime("%d/%m/%Y %H:%M")

            # Inserisce nel DB SQLite
            nuovo_id = inserisci_nota_db(anteprima, testo_completo, ora_attuale)

            note_list.insert(
                0,
                {
                    "id": nuovo_id,
                    "anteprima": anteprima,
                    "contenuto": testo_completo,
                    "data": ora_attuale,
                },
            )
            status_label.value = "💾 Registrato e salvato su DB!"
            mostra_home()

    def salva_modifiche_dettaglio(e=None):
        nonlocal nota_selezionata_idx
        if nota_selezionata_idx is not None and txt_contenuto.value:
            testo = txt_contenuto.value.strip()
            anteprima = estrai_anteprima_due_righe(testo)

            nota = note_list[nota_selezionata_idx]
            nota["anteprima"] = anteprima
            nota["contenuto"] = testo

            # Aggiorna il DB SQLite usando l'ID univoco della nota
            aggiorna_nota_db(nota["id"], anteprima, testo)

            status_label.value = "💾 Modifiche salvate!"
            mostra_home()

    def ascolta_vocale(e):
        def worker():
            r = sr.Recognizer()
            with sr.Microphone() as source:
                status_label.value = "🎙️ In ascolto... Parla ora!"
                page.update()
                try:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=8, phrase_time_limit=15)

                    status_label.value = "🔄 Elaborazione testo..."
                    page.update()

                    testo = r.recognize_google(audio, language="it-IT")
                    ora_attuale = datetime.now().strftime("%d/%m/%Y %H:%M")
                    testo_finale = f"[{ora_attuale}]\n{testo}"

                    esegui_salvataggio_automatico(testo_finale)

                except sr.WaitTimeoutError:
                    status_label.value = "⚠️ Nessun audio rilevato."
                except sr.UnknownValueError:
                    status_label.value = "⚠️ Audio non compreso."
                except Exception as ex:
                    status_label.value = f"⚠️ Errore: {str(ex)}"

                page.update()

        threading.Thread(target=worker, daemon=True).start()

    # --- Rendering Lista Appunti ---
    elenco_note_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def aggiorna_lista_ui():
        elenco_note_container.controls.clear()
        if not note_list:
            elenco_note_container.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Nessun appunto presente.\nClicca REGISTRA o NUOVA NOTA per iniziare.",
                        italic=True,
                        color="gray",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=30,
                    alignment=ft.alignment.center,
                )
            )
        else:
            for idx, n in enumerate(note_list):

                def make_click(i):
                    return lambda e: apri_dettaglio(i)

                card = ft.Container(
                    content=ft.ListTile(
                        leading=ft.Icon(ft.Icons.NOTE_ALT, color=BORDER_COLOR),
                        title=ft.Text(
                            n["anteprima"],
                            weight=ft.FontWeight.BOLD,
                            color="#5C3A21",
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        on_click=make_click(idx),
                    ),
                    bgcolor=CARD_BG,
                    border=ft.border.all(1, "#D3C193"),
                    border_radius=6,
                )
                elenco_note_container.controls.append(card)

    # --- Costruzione UI Vista Home ---
    btn_registra = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.MIC, size=38, color=BORDER_COLOR),
                ft.Text("REGISTRA", weight=ft.FontWeight.BOLD, color="#5C3A21"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=CARD_BG,
        border=ft.border.all(1.5, BORDER_COLOR),
        border_radius=8,
        padding=10,
        ink=True,
        on_click=ascolta_vocale,
        expand=True,
    )

    btn_nuova = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.NOTE_ADD, size=38, color=BORDER_COLOR),
                ft.Text("NUOVA NOTA", weight=ft.FontWeight.BOLD, color="#5C3A21"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=CARD_BG,
        border=ft.border.all(1.5, BORDER_COLOR),
        border_radius=8,
        padding=10,
        ink=True,
        on_click=crea_nuova_nota_manuale,
        expand=True,
    )

    vista_lista.controls = [
        ft.Row([btn_registra, btn_nuova], spacing=10),
        ft.Divider(color=BORDER_COLOR, height=10),
        ft.Text("I Tuoi Appunti:", weight=ft.FontWeight.BOLD, color="#5C3A21"),
        elenco_note_container,
    ]

    # --- Costruzione UI Vista Dettaglio ---
    def crea_btn_azione(testo, icona, on_click_fn=None):
        return ft.OutlinedButton(
            content=ft.Row(
                [
                    ft.Icon(icona, size=14, color=BORDER_COLOR),
                    ft.Text(testo, size=11, color="#5C3A21"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=3,
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=4),
                side=ft.BorderSide(width=1, color=BORDER_COLOR),
                bgcolor=CARD_BG,
                padding=4,
            ),
            on_click=on_click_fn,
            expand=True,
        )

    col_azioni_sx = ft.Column(
        [
            crea_btn_azione(
                "Salva", ft.Icons.SAVE, on_click_fn=salva_modifiche_dettaglio
            ),
            crea_btn_azione("Modifica", ft.Icons.MODE_EDIT_OUTLINE),
            crea_btn_azione("Cerca", ft.Icons.SEARCH),
        ],
        spacing=5,
        expand=True,
    )

    col_azioni_dx = ft.Column(
        [
            crea_btn_azione("Stampa", ft.Icons.PRINT),
            crea_btn_azione("Inoltra", ft.Icons.SHARE),
            crea_btn_azione("Imposta Ora", ft.Icons.ALARM_ADD),
        ],
        spacing=5,
        expand=True,
    )

    vista_dettaglio.controls = [
        ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=BORDER_COLOR,
                    on_click=mostra_home,
                ),
                lbl_titolo_dettaglio,
            ],
            alignment=ft.MainAxisAlignment.START,
        ),
        ft.Row([col_azioni_sx, col_azioni_dx], spacing=10),
        ft.Container(height=5),
        txt_contenuto,
    ]

    # --- Inizializzazione Layout ---
    mostra_home()

    page.add(
        ft.Column(
            [vista_lista, vista_dettaglio, status_label],
            expand=True,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    )


if __name__ == "__main__":
    assets_dir_path = os.path.join(os.path.dirname(__file__), "assets")
    ft.app(target=main, assets_dir=assets_dir_path)
