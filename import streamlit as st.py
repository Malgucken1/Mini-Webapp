import streamlit as st
import math
import urllib.parse

# --- SEITENKONFIGURATION ---
st.set_page_config(page_title="Gehaltsrechner DE", page_icon="💰", layout="centered")

# --- TITEL ---
st.title("💰 Gehalts- & Arbeitszeitrechner")
st.write("Berechnen Sie Ihr verfügbares Einkommen und wie lange Sie für eine Anschaffung arbeiten müssen.")

# --- Transparenzhinweis (rechtlich notwendig bei Affiliate-Links) ---
st.caption("**Transparenzhinweis:** Als Amazon-Partner verdiene ich an qualifizierten Verkäufen. Für Sie entstehen keine Mehrkosten.")

# --- KONSTANTEN FÜR DEUTSCHLAND (Stand 2024/2025) ---
BBG_KV_PV = 5175.00
BBG_RV_AV = 7550.00
SATZ_RV = 0.093
SATZ_AV = 0.013
SATZ_KV_ALLG = 0.073
SATZ_KV_ZUSATZ = 0.0085
SATZ_KV_GESAMT = SATZ_KV_ALLG + SATZ_KV_ZUSATZ
SATZ_PV_MIT_KIND = 0.017
SATZ_PV_OHNE_KIND_ZUSCHLAG = 0.006
SATZ_PV_OHNE_KIND = SATZ_PV_MIT_KIND + SATZ_PV_OHNE_KIND_ZUSCHLAG
GRUNDFREIBETRAG = {1: 11604, 2: 11604, 3: 23208, 4: 11604, 5: 0, 6: 0}
ENTLASTUNGSBETRAG_SK2 = 4260

# --- FUNKTIONEN ---
def berechne_lohnsteuer(brutto_monat, steuerklasse):
    if steuerklasse == 5:
        return brutto_monat * 0.35

    freibetrag_jahr = GRUNDFREIBETRAG.get(steuerklasse, 0)
    if steuerklasse == 2:
        freibetrag_jahr += ENTLASTUNGSBETRAG_SK2

    zve_jahr = brutto_monat * 12

    if zve_jahr <= freibetrag_jahr:
        return 0.0

    steuer_jahr = 0
    if zve_jahr > freibetrag_jahr:
        y = (zve_jahr - freibetrag_jahr) / 10000
        steuer_jahr = (979.18 * y + 1400) * y
    if zve_jahr > 17659:
        z = (zve_jahr - 17659) / 10000
        steuer_jahr = (192.59 * z + 2397) * z + 1069.53
    if zve_jahr > 66760:
        steuer_jahr = 0.42 * zve_jahr - 10253.32
    if zve_jahr > 277825:
        steuer_jahr = 0.45 * zve_jahr - 18588.07

    return steuer_jahr / 12


def berechne_netto_gehalt(brutto_monat, steuerklasse, bundesland, hat_kinder, kirchensteuerpflichtig, anstellungsart):
    kv_beitrag = pv_beitrag = rv_beitrag = av_beitrag = 0.0
    brutto_kv_pv = min(brutto_monat, BBG_KV_PV)
    brutto_rv_av = min(brutto_monat, BBG_RV_AV)

    if anstellungsart in ["Angestellte/r", "Auszubildende/r"]:
        kv_beitrag = brutto_kv_pv * SATZ_KV_GESAMT
        rv_beitrag = brutto_rv_av * SATZ_RV
        av_beitrag = brutto_rv_av * SATZ_AV
        pv_beitrag = brutto_kv_pv * (SATZ_PV_MIT_KIND if hat_kinder else SATZ_PV_OHNE_KIND)
    elif anstellungsart == "Werkstudent/in":
        rv_beitrag = brutto_rv_av * SATZ_RV

    sozialabgaben_total = kv_beitrag + rv_beitrag + av_beitrag + pv_beitrag

    lohnsteuer = berechne_lohnsteuer(brutto_monat, steuerklasse)
    soli_freigrenze_jahr = 18130
    soli = lohnsteuer * 0.055 if lohnsteuer * 12 > soli_freigrenze_jahr else 0.0

    kirchensteuer = 0.0
    if kirchensteuerpflichtig:
        if bundesland in ["Bayern", "Baden-Württemberg"]:
            kirchensteuer = lohnsteuer * 0.08
        else:
            kirchensteuer = lohnsteuer * 0.09

    steuern_total = lohnsteuer + soli + kirchensteuer
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


# --- Streamlit App Inhalte ---
if 'fixkosten_liste' not in st.session_state:
    st.session_state.fixkosten_liste = []

st.header("1. Ihre Angaben")

col1, col2 = st.columns(2)
with col1:
    brutto_gehalt = st.number_input("Monatl. Bruttogehalt (€)", min_value=0.0, value=3500.0, step=100.0)
    stunden_pro_woche = st.number_input("Stunden pro Woche", min_value=1.0, max_value=80.0, value=40.0)
    anstellungsart = st.selectbox("Anstellungsverhältnis", ["Angestellte/r", "Auszubildende/r", "Werkstudent/in", "Beamte/Beamtin"])
    steuerklasse = st.selectbox("Steuerklasse", [1, 2, 3, 4, 5, 6], index=0)

with col2:
    preis_artikel = st.number_input("Preis des Artikels (€)", min_value=0.0, value=1000.0, step=10.0)
    bundesland = st.selectbox("Bundesland", [
        "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessen",
        "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz",
        "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"
    ])
    hat_kinder = st.radio("Haben Sie Kinder?", ["Ja", "Nein"]) == "Ja"
    kirchensteuerpflichtig = st.radio("Kirchensteuerpflichtig?", ["Ja", "Nein"], index=1) == "Ja"

# --- Fixkosten ---
st.header("2. Ihre monatlichen Fixkosten")

def remove_fixkosten(index_to_remove):
    if 0 <= index_to_remove < len(st.session_state.fixkosten_liste):
        st.session_state.fixkosten_liste.pop(index_to_remove)

with st.form(key="fixkosten_form", clear_on_submit=True):
    col_form1, col_form2 = st.columns(2)
    with col_form1:
        neuer_posten_name = st.text_input("Beschreibung", placeholder="z.B. Miete, Handyvertrag...")
    with col_form2:
        neuer_posten_wert = st.number_input("Betrag (€)", min_value=0.01, step=0.01, format="%.2f")
    submitted = st.form_submit_button("Hinzufügen")
    if submitted and neuer_posten_name and neuer_posten_wert:
        st.session_state.fixkosten_liste.append({"name": neuer_posten_name, "wert": neuer_posten_wert})

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

# --- Berechnung ---
if brutto_gehalt > 0:
    st.header("3. Ihre Ergebnisse")
    netto_gehalt, abzuege = berechne_netto_gehalt(brutto_gehalt, steuerklasse, bundesland, hat_kinder, kirchensteuerpflichtig, anstellungsart)
    verfuegbares_einkommen = netto_gehalt - fixkosten_total
    WOCHEN_PRO_MONAT = 4.33
    monatliche_arbeitsstunden = stunden_pro_woche * WOCHEN_PRO_MONAT

    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.metric("Monatl. Nettogehalt (vor Fixkosten)", f"{netto_gehalt:,.2f} €")
    with col_res2:
        st.metric("Verfügbares Einkommen (nach Fixkosten)", f"{verfuegbares_einkommen:,.2f} €", delta=f"{-fixkosten_total:,.2f} € Fixkosten")

    if monatliche_arbeitsstunden > 0:
        st.metric("Stundenlohn (Netto)", f"{netto_gehalt / monatliche_arbeitsstunden:,.2f} €")

# --- Affiliate-Link Generator ---
st.header("4. Amazon Link zum Produkt")
affiliate_tag = "affiliatesche-21"
search_term = st.text_input("Was möchten Sie kaufen?", placeholder="z.B. Neues Smartphone")

if st.button("Link zum Produkt generieren"):
    if search_term:
        encoded_search_term = urllib.parse.quote_plus(search_term)
        amazon_link = f"https://www.amazon.de/s?k={encoded_search_term}&tag={affiliate_tag}"
        st.success("Ihr Affiliate-Link wurde erstellt!")
        st.code(amazon_link, language="text")
        st.markdown(f"**[Klickbarer Link zum Testen]({amazon_link})**")
    else:
        st.error("Bitte geben Sie einen Suchbegriff ein.")

# --- FOOTER: Rechtliche Hinweise ---
st.markdown("---")
st.info(
    """
    **Impressum (§ 5 TMG):**  
    Betreiber dieser Website:  
    **Niklas Schelkle**  
    Spichernstraße 9  
    24116 Kiel  
    📧 E-Mail: [niklasschelkle@gmail.com](mailto:niklasschelkle@gmail.com)

    **Verantwortlich für den Inhalt (§ 55 Abs. 2 RStV):**  
    Niklas Schelkle

    **Datenschutz:**  
    Diese Anwendung verwendet keine Cookies oder eigenes Tracking.  
    Beim Klick auf Amazon-Links werden Cookies von Amazon gesetzt, um Einkäufe korrekt zuordnen zu können.  
    Weitere Informationen finden Sie in der [Datenschutzerklärung von Amazon](https://www.amazon.de/gp/help/customer/display.html?nodeId=201909010).

    **Affiliate-Hinweis:**  
    Als Amazon-Partner verdiene ich an qualifizierten Verkäufen. Für Sie entstehen dadurch keine Mehrkosten.

    **Haftungsausschluss:**  
    Trotz sorgfältiger inhaltlicher Kontrolle übernehme ich keine Haftung für externe Links.  
    Für den Inhalt verlinkter Seiten sind ausschließlich deren Betreiber verantwortlich.  
    Diese Anwendung dient ausschließlich Informationszwecken – alle Berechnungen erfolgen ohne Gewähr.
    """
)
st.caption("© 2025 Niklas Schelkle – Alle Rechte vorbehalten.")
