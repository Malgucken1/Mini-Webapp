import streamlit as st
import math

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

def berechne_netto_gehalt(brutto_monat, steuerklasse, bundesland, hat_kinder, kirchensteuerpflichtig):
    """Berechnet das Nettogehalt basierend auf detaillierten deutschen Abzügen."""

    # 1. Sozialversicherungsbeiträge berechnen
    # Brutto bis zur jeweiligen Beitragsbemessungsgrenze
    brutto_kv_pv = min(brutto_monat, BBG_KV_PV)
    brutto_rv_av = min(brutto_monat, BBG_RV_AV)

    kv_beitrag = brutto_kv_pv * SATZ_KV_GESAMT
    rv_beitrag = brutto_rv_av * SATZ_RV
    av_beitrag = brutto_rv_av * SATZ_AV

    if hat_kinder:
        pv_beitrag = brutto_kv_pv * SATZ_PV_MIT_KIND
    else:
        pv_beitrag = brutto_kv_pv * SATZ_PV_OHNE_KIND

    sozialabgaben_total = kv_beitrag + rv_beitrag + av_beitrag + pv_beitrag

    # 2. Steuern berechnen
    lohnsteuer = berechne_lohnsteuer(brutto_monat, steuerklasse)

    # Solidaritätszuschlag (oft 0, da Freigrenze hoch ist)
    soli_freigrenze_jahr = 18130 # Single, 2024
    if lohnsteuer * 12 > soli_freigrenze_jahr:
        soli = lohnsteuer * 0.055
    else:
        soli = 0.0

    # Kirchensteuer
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

st.title("💰 Gehaltsrechner für Deutschland")
st.write("Berechnen Sie Ihr Nettogehalt und finden Sie heraus, wie lange Sie für eine Anschaffung arbeiten müssen.")

# --- Eingabefelder ---
st.header("1. Ihre Angaben")

col1, col2 = st.columns(2)
with col1:
    brutto_gehalt = st.number_input("Monatl. Bruttogehalt (€)", min_value=0.0, value=3500.0, step=100.0)
    steuerklasse = st.selectbox("Steuerklasse", options=[1, 2, 3, 4, 5, 6], index=0)
    hat_kinder = st.radio("Haben Sie Kinder?", options=["Ja", "Nein"], index=0) == "Ja"

with col2:
    preis_artikel = st.number_input("Preis des Artikels (€)", min_value=0.0, value=1000.0, step=10.0)
    bundesland = st.selectbox("Bundesland", options=[
        "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessen",
        "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz",
        "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"
    ])
    kirchensteuerpflichtig = st.radio("Kirchensteuerpflichtig?", options=["Ja", "Nein"], index=1) == "Ja"


# --- Berechnung und Ausgabe ---
if brutto_gehalt > 0:
    st.header("2. Ihre Ergebnisse")

    netto_gehalt, abzuege = berechne_netto_gehalt(brutto_gehalt, steuerklasse, bundesland, hat_kinder, kirchensteuerpflichtig)

    st.metric(label="Geschätztes monatliches Nettogehalt", value=f"{netto_gehalt:,.2f} €")

    with st.expander("Details der Abzüge anzeigen"):
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
    STUNDEN_PRO_WOCHE = 40
    WOCHEN_PRO_MONAT = 4.33
    MONATLICHE_ARBEITSSTUNDEN = STUNDEN_PRO_WOCHE * WOCHEN_PRO_MONAT
    stundenlohn_netto = netto_gehalt / MONATLICHE_ARBEITSSTUNDEN

    st.metric(label="Ihr Netto-Stundenlohn", value=f"{stundenlohn_netto:,.2f} €")

    if preis_artikel > 0:
        st.subheader("Benötigte Arbeitszeit für den Artikel")

        benoetigte_stunden_total = preis_artikel / stundenlohn_netto
        arbeitstage = math.floor(benoetigte_stunden_total / 8)
        rest_stunden = benoetigte_stunden_total % 8
        stunden = math.floor(rest_stunden)
        minuten = math.floor((rest_stunden - stunden) * 60)

        ergebnis_text = ""
        if arbeitstage > 0:
            ergebnis_text += f"{arbeitstage} Tag(e), "
        if stunden > 0:
            ergebnis_text += f"{stunden} Stunde(n) und "
        ergebnis_text += f"{minuten} Minute(n)"

        st.metric(label=f"Um {preis_artikel:,.2f} € zu verdienen, müssen Sie arbeiten:",
                  value=ergebnis_text.strip().strip(","))

# --- Footer ---
st.markdown("---")
st.info(
    "**Haftungsausschluss:** Dies ist eine vereinfachte Berechnung und dient nur zur Orientierung. "
    "Die tatsächliche Lohnabrechnung kann aufgrund von individuellen Faktoren (z.B. genauer Krankenkassenzusatzbeitrag, "
    "private Krankenversicherung, geldwerte Vorteile) abweichen. Die Lohnsteuerberechnung ist eine Annäherung."
)
