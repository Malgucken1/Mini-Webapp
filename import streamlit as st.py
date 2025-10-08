import streamlit as st
import math
import urllib.parse

# --- KONSTANTEN FÜR DEUTSCHLAND (Stand 2024/2025, West) ---
# Diese Werte können für zukünftige Jahre angepasst werden.

# Beitragsbemessungsgrenzen (monatlich)
BBG_KV_PV = 5175.00  # Kranken- und Pflegeversicherung
BBG_RV_AV = 7550.00  # Renten- und Arbeitslosenversicherung

# Beitragssätze Arbeitnehmeranteil
SATZ_RV = 0.093      # Rentenversicherung (9.3%)
SATZ_AV = 0.013      # Arbeitslosenversicherung (1.3%)
SATZ_KV_ALLG = 0.073 # Krankenversicherung, allgemeiner Beitrag (7.3%)
SATZ_KV_ZUSATZ = 0.0085 # Durchschnittlicher Zusatzbeitrag (Annahme: 1.7% gesamt -> 0.85% für AN)
SATZ_KV_GESAMT = SATZ_KV_ALLG + SATZ_KV_ZUSATZ

# Pflegeversicherung (AN-Anteil)
SATZ_PV_MIT_KIND = 0.017 # Mit Kindern (1.7%)
SATZ_PV_OHNE_KIND_ZUSCHLAG = 0.006 # Zuschlag für Kinderlose über 23
SATZ_PV_OHNE_KIND = SATZ_PV_MIT_KIND + SATZ_PV_OHNE_KIND_ZUSCHLAG # (2.3%)

# Lohnsteuer-Tarifzonen (vereinfacht, basierend auf Jahreswerten 2024 / 12)
# Dies ist eine Annäherung, die exakte Formel ist sehr komplex.
GRUNDFREIBETRAG = {1: 11604, 2: 11604, 3: 23208, 4: 11604, 5: 0, 6: 0}
# Freibetrag für Alleinerziehende (Steuerklasse 2)
ENTLASTUNGSBETRAG_SK2 = 4260

# --- FUNKTIONEN ---

def berechne_lohnsteuer(brutto_monat, steuerklasse):
    """
    Vereinfachte Berechnung der monatlichen Lohnsteuer.
    Basiert auf den Jahresgrenzen von 2024, umgerechnet auf den Monat.
    """
    if steuerklasse == 5:
        # Steuerklasse 5 wird oft mit einem fiktiv hohen Steuersatz angenähert,
        # da die Freibeträge in Klasse 3 sind. Dies ist eine starke Vereinfachung.
        return brutto_monat * 0.35

    freibetrag_jahr = GRUNDFREIBETRAG.get(steuerklasse, 0)
    if steuerklasse == 2:
        freibetrag_jahr += ENTLASTUNGSBETRAG_SK2

    zve_jahr = brutto_monat * 12

    if zve_jahr <= freibetrag_jahr:
        return 0.0

    # Progressive Berechnung in Zonen
    steuer_jahr = 0
    if zve_jahr > freibetrag_jahr:
        y = (zve_jahr - freibetrag_jahr) / 10000
        steuer_jahr = (979.18 * y + 1400) * y

    if zve_jahr > 17659: # ca. 1471 € / Monat
        z = (zve_jahr - 17659) / 10000
        steuer_jahr = (192.59 * z + 2397) * z + 1069.53

    if zve_jahr > 66760: # ca. 5563 € / Monat
        steuer_jahr = 0.42 * zve_jahr - 10253.32

    if zve_jahr > 277825: # ca. 23152 € / Monat
        steuer_jahr = 0.45 * zve_jahr - 18588.07

    return steuer_jahr / 12

def berechne_netto_gehalt(brutto_monat, steuerklasse, bundesland, hat_kinder, kirchensteuerpflichtig, anstellungsart):
    """Berechnet das Nettogehalt basierend auf detaillierten deutschen Abzügen."""

    # Initialisiere alle Beiträge
    kv_beitrag, pv_beitrag, rv_beitrag, av_beitrag = 0.0, 0.0, 0.0, 0.0

    # 1. Sozialversicherungsbeiträge je nach Anstellungsart berechnen
    brutto_kv_pv = min(brutto_monat, BBG_KV_PV)
    brutto_rv_av = min(brutto_monat, BBG_RV_AV)

    if anstellungsart in ["Angestellte/r", "Auszubildende/r"]:
        # Standard-Sozialversicherungspflicht (Azubis über 325€/Monat)
        kv_beitrag = brutto_kv_pv * SATZ_KV_GESAMT
        rv_beitrag = brutto_rv_av * SATZ_RV
        av_beitrag = brutto_rv_av * SATZ_AV
        if hat_kinder:
            pv_beitrag = brutto_kv_pv * SATZ_PV_MIT_KIND
        else:
            pv_beitrag = brutto_kv_pv * SATZ_PV_OHNE_KIND
    elif anstellungsart == "Werkstudent/in":
        # Werkstudenten zahlen nur in die Rentenversicherung
        rv_beitrag = brutto_rv_av * SATZ_RV
    elif anstellungsart == "Beamte/Beamtin":
        # Beamte zahlen keine Sozialversicherungsbeiträge, da sie anders abgesichert sind
        pass # Alle Beiträge bleiben 0

    sozialabgaben_total = kv_beitrag + rv_beitrag + av_beitrag + pv_beitrag

    # 2. Steuern berechnen (gilt für alle Anstellungsarten)
    lohnsteuer = berechne_lohnsteuer(brutto_monat, steuerklasse)

    soli_freigrenze_jahr = 18130
    if lohnsteuer * 12 > soli_freigrenze_jahr:
        soli = lohnsteuer * 0.055
    else:
        soli = 0.0

    kirchensteuer = 0.0
    if kirchensteuerpflichtig:
        if bundesland in ["Bayern", "Baden-Württemberg"]:
            kirchensteuer = lohnsteuer * 0.08
        else:
            kirchensteuer = lohnsteuer * 0.09

    steuern_total = lohnsteuer + soli + kirchensteuer

    # 3. Nettogehalt berechnen
    netto_gehalt = brutto_monat - sozialabgaben_total - steuern_total

    abzuege_details = {
        "Lohnsteuer": lohnsteuer,
        "Solidaritätszuschlag": soli,
        "Kirchensteuer": kirchensteuer,
        "Steuern Gesamt": steuern_total,
        "Krankenversicherung": kv_beitrag,
        "Rentenversicherung": rv_beitrag,
        "Arbeitslosenversicherung": av_beitrag,
        "Pflegeversicherung": pv_beitrag,
        "Sozialabgaben Gesamt": sozialabgaben_total,
        "Gesamtabzüge": sozialabgaben_total + steuern_total
    }

    return netto_gehalt, abzuege_details


# --- Streamlit App ---
st.set_page_config(page_title="Gehaltsrechner DE", page_icon="💰", layout="centered")

st.title("💰 Gehalts- & Arbeitszeitrechner")
st.write("Berechnen Sie Ihr verfügbares Einkommen und wie lange Sie für eine Anschaffung arbeiten müssen.")

# Initialize session state for fixed costs list
if 'fixkosten_liste' not in st.session_state:
    st.session_state.fixkosten_liste = []


# --- Eingabefelder ---
st.header("1. Ihre Angaben")

col1, col2 = st.columns(2)
with col1:
    brutto_gehalt = st.number_input("Monatl. Bruttogehalt (€)", min_value=0.0, value=3500.0, step=100.0)
    stunden_pro_woche = st.number_input("Stunden pro Woche", min_value=1.0, max_value=80.0, value=40.0, step=1.0)
    anstellungsart = st.selectbox(
        "Anstellungsverhältnis",
        options=["Angestellte/r", "Auszubildende/r", "Werkstudent/in", "Beamte/Beamtin"],
        index=0
    )
    steuerklasse = st.selectbox("Steuerklasse", options=[1, 2, 3, 4, 5, 6], index=0)

with col2:
    preis_artikel = st.number_input("Preis des Artikels (€)", min_value=0.0, value=1000.0, step=10.0)
    bundesland = st.selectbox("Bundesland", options=[
        "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessen",
        "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz",
        "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"
    ])
    hat_kinder = st.radio("Haben Sie Kinder?", options=["Ja", "Nein"], index=0) == "Ja"
    kirchensteuerpflichtig = st.radio("Kirchensteuerpflichtig?", options=["Ja", "Nein"], index=1) == "Ja"

# --- Bereich für individuelle Fixkosten ---
st.header("2. Ihre monatlichen Fixkosten")

# Function to remove an item
def remove_fixkosten(index_to_remove):
    if 0 <= index_to_remove < len(st.session_state.fixkosten_liste):
        st.session_state.fixkosten_liste.pop(index_to_remove)

# Input form for new items
with st.form(key="fixkosten_form", clear_on_submit=True):
    col_form1, col_form2 = st.columns(2)
    with col_form1:
        neuer_posten_name = st.text_input("Beschreibung", placeholder="z.B. Miete, Handyvertrag...")
    with col_form2:
        neuer_posten_wert = st.number_input("Betrag (€)", min_value=0.01, step=0.01, format="%.2f")
    
    submitted = st.form_submit_button("Hinzufügen")
    if submitted and neuer_posten_name and neuer_posten_wert:
        st.session_state.fixkosten_liste.append({"name": neuer_posten_name, "wert": neuer_posten_wert})

# Display existing items
if st.session_state.fixkosten_liste:
    st.write("---")
    for i, posten in enumerate(st.session_state.fixkosten_liste):
        col_disp1, col_disp2, col_disp3 = st.columns([3, 2, 1])
        with col_disp1:
            st.write(posten["name"])
        with col_disp2:
            st.write(f"{posten['wert']:,.2f} €")
        with col_disp3:
            st.button("🗑️", key=f"delete_{i}", on_click=remove_fixkosten, args=(i,))
    st.write("---")

fixkosten_total = sum(posten['wert'] for posten in st.session_state.fixkosten_liste)


# --- Berechnung und Ausgabe ---
if brutto_gehalt > 0:
    st.header("3. Ihre Ergebnisse")

    netto_gehalt, abzuege = berechne_netto_gehalt(brutto_gehalt, steuerklasse, bundesland, hat_kinder, kirchensteuerpflichtig, anstellungsart)
    verfuegbares_einkommen = netto_gehalt - fixkosten_total

    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.metric(label="Monatl. Nettogehalt (vor Fixkosten)", value=f"{netto_gehalt:,.2f} €")
    with col_res2:
        st.metric(label="Verfügbares Einkommen (nach Fixkosten)", value=f"{verfuegbares_einkommen:,.2f} €",
                  delta=f"{-fixkosten_total:,.2f} € Fixkosten")


    with st.expander("Details der Abzüge vom Bruttogehalt anzeigen"):
        st.write(f"**Gesamtabzüge: {abzuege['Gesamtabzüge']:,.2f} €**")
        st.write("---")
        st.write(f"**Steuern ({abzuege['Steuern Gesamt']:,.2f} €):**")
        st.write(f"- Lohnsteuer: {abzuege['Lohnsteuer']:,.2f} €")
        st.write(f"- Solidaritätszuschlag: {abzuege['Solidaritätszuschlag']:,.2f} €")
        st.write(f"- Kirchensteuer: {abzuege['Kirchensteuer']:,.2f} €")
        st.write("---")
        st.write(f"**Sozialabgaben ({abzuege['Sozialabgaben Gesamt']:,.2f} €):**")
        st.write(f"- Rentenversicherung: {abzuege['Rentenversicherung']:,.2f} €")
        st.write(f"- Krankenversicherung: {abzuege['Krankenversicherung']:,.2f} €")
        st.write(f"- Arbeitslosenversicherung: {abzuege['Arbeitslosenversicherung']:,.2f} €")
        st.write(f"- Pflegeversicherung: {abzuege['Pflegeversicherung']:,.2f} €")

    # Stundenlohn und Arbeitszeit
    WOCHEN_PRO_MONAT = 4.33
    monatliche_arbeitsstunden = stunden_pro_woche * WOCHEN_PRO_MONAT
    
    if monatliche_arbeitsstunden > 0 and preis_artikel > 0:
        st.subheader(f"Benötigte Arbeitszeit für den Artikel ({preis_artikel:,.2f} €)")

        if verfuegbares_einkommen > 0:
            stundenlohn_verfuegbar = verfuegbares_einkommen / monatliche_arbeitsstunden
            benoetigte_stunden_total = preis_artikel / stundenlohn_verfuegbar
            
            # Umrechnung in Stunden, Minuten und Sekunden
            stunden_ganz = int(benoetigte_stunden_total)
            minuten_decimal = (benoetigte_stunden_total - stunden_ganz) * 60
            minuten_ganz = int(minuten_decimal)
            sekunden_decimal = (minuten_decimal - minuten_ganz) * 60
            sekunden_ganz = int(sekunden_decimal)

            ergebnis_text = f"{stunden_ganz} Stunde(n), {minuten_ganz} Minute(n) und {sekunden_ganz} Sekunde(n)"
            
            st.metric(label="Um den Betrag aus Ihrem verfügbaren Einkommen zu sparen, müssen Sie arbeiten:",
                      value=ergebnis_text)
        else:
            st.warning("Ihre Fixkosten sind gleich hoch oder höher als Ihr Nettogehalt. Sie können den Artikel nicht aus dem laufenden Einkommen ansparen.")

# --- Amazon Affiliate Link Generator ---
st.header("4. Amazon Affiliate Link erstellen")
st.write("Geben Sie Ihren Amazon-Partner-Tag und ein Produkt ein, um einen persönlichen Affiliate-Link zu erstellen.")

affiliate_tag = st.text_input("Ihr Amazon Partner-Tag (z.B. mein-tag-21)", key="affiliate_tag")
search_term = st.text_input("Was möchten Sie kaufen?", placeholder="z.B. Neues Smartphone", key="search_term")

if st.button("Affiliate-Link generieren"):
    if affiliate_tag and search_term:
        # URL-encode the search term to handle spaces and special characters
        encoded_search_term = urllib.parse.quote_plus(search_term)
        
        # Construct the affiliate link for amazon.de
        amazon_link = f"https://www.amazon.de/s?k={encoded_search_term}&tag={affiliate_tag}"
        
        st.success("Ihr Affiliate-Link wurde erstellt!")
        st.code(amazon_link, language="text")
        st.markdown(f"**[Klickbarer Link zum Testen]({amazon_link})**")
    else:
        st.error("Bitte geben Sie sowohl Ihren Partner-Tag als auch einen Suchbegriff ein.")


# --- Footer ---
st.markdown("---")
st.info(
    """
    **Haftungsausschluss:** Dies ist eine vereinfachte Berechnung und dient nur zur Orientierung. Die tatsächliche Lohnabrechnung kann aufgrund von individuellen Faktoren abweichen.
    - **Für Werkstudenten:** Die Beiträge zur studentischen Kranken- und Pflegeversicherung sind hier nicht berücksichtigt und müssen separat entrichtet werden.
    - **Für Beamte:** Die Beiträge zur privaten Kranken- und Pflegeversicherung (Restkostenabsicherung zur Beihilfe) sind hier nicht berücksichtigt und müssen separat entrichtet werden.
    - **Für Auszubildende:** Bei einem Gehalt unter 325 €/Monat (Geringverdienergrenze) zahlt der Arbeitgeber die Sozialabgaben allein. Dies wird hier nicht abgebildet.
    """
)
