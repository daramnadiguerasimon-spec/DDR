# app.py
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from materiaux import MATERIAUX_DEFAUT
from hydraulique import (
    geometrie_section, calculer_regime_uniforme, section_optimale,
    calculer_ressaut, courbe_remous_pas_directs, methode_rationnelle, TOLERANCE
)

st.set_page_config(page_title="HydroDim Pro - Assainissement", layout="wide")
st.title("Dimensionnement des Canaux et Ouvrages d'Évacuation")
st.caption(f"Moteur hydraulique haute précision (critère de convergence numérique : {TOLERANCE} m)")

if "materiaux" not in st.session_state:
    st.session_state.materiaux = MATERIAUX_DEFAUT.copy()

with st.sidebar:
    st.header("1. Débit de projet")
    mode_debit = st.radio("Source du débit :", ["Saisie directe (m³/s)", "Méthode rationnelle (Q = CiA/360)"])
    if mode_debit == "Saisie directe (m³/s)":
        Q = st.number_input("Débit Q (m³/s)", min_value=0.005, value=2.50, step=0.1)
    else:
        C = st.slider("Coefficient de ruissellement C", 0.1, 1.0, 0.75, 0.05)
        i_pluie = st.number_input("Intensité de pluie i (mm/h)", min_value=1.0, value=90.0, step=5.0)
        A_bv = st.number_input("Surface bassin versant A (ha)", min_value=0.1, value=12.0, step=0.5)
        Q = methode_rationnelle(C, i_pluie, A_bv)
        st.info(f"Débit calculé : **{Q:.3f} m³/s**")

    st.header("2. Pente et Matériau")
    I = st.number_input("Pente longitudinale I (m/m)", min_value=0.0001, value=0.0040, format="%.4f")
    mat_choisi = st.selectbox("Matériau de revêtement", list(st.session_state.materiaux.keys()))
    infos_mat = st.session_state.materiaux[mat_choisi]
    Ks = st.number_input("Coefficient Strickler Ks", value=float(infos_mat["Ks"]), step=1.0)

    st.header("3. Géométrie de la section")
    forme = st.selectbox("Forme de l'ouvrage", ["Trapézoïdale", "Rectangulaire", "Circulaire", "En U"])
    b, m, D = 0.0, 0.0, 0.0
    if forme in ["Rectangulaire", "Trapézoïdale"]:
        b = st.number_input("Largeur au plafond b (m)", min_value=0.1, value=1.50, step=0.1)
    if forme == "Trapézoïdale":
        m = st.number_input("Fruit des berges m (H/V)", min_value=0.1, value=1.50, step=0.1)
    if forme in ["Circulaire", "En U"]:
        D = st.number_input("Diamètre D (m)", min_value=0.2, value=1.50, step=0.1)

tab1, tab2, tab3, tab4 = st.tabs([
    "Régime Uniforme & Profil en travers",
    "Section Économique Optimale",
    "Remous & Ressaut Hydraulique",
    "Bibliothèque & Export Fiche"
])

with tab1:
    try:
        res = calculer_regime_uniforme(Q, I, Ks, forme, b, m, D)
        yn, yc, Vn, Fr = res["yn"], res["yc"], res["Vn"], res["Fr"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Hauteur normale (yn)", f"{yn:.3f} m")
        c2.metric("Hauteur critique (yc)", f"{yc:.3f} m")
        c3.metric("Vitesse d'écoulement (V)", f"{Vn:.2f} m/s")
        c4.metric("Nombre de Froude (Fr)", f"{Fr:.2f}", res["regime"])

        v_min, v_max = infos_mat["v_min"], infos_mat["v_max"]
        if Vn < v_min:
            st.warning(f"Auto-curage non assuré : V = {Vn:.2f} m/s < {v_min} m/s (risque d'ensablement).")
        elif Vn > v_max:
            st.error(f"Risque d'érosion : V = {Vn:.2f} m/s > {v_max} m/s (protéger le radier).")
        else:
            st.success(f"Vitesse réglementaire validée ({v_min} <= V <= {v_max} m/s).")

        fig, ax = plt.subplots(figsize=(8, 3.8))
        H_des = max(yn, yc) * 1.35

        if forme in ["Rectangulaire", "Trapézoïdale"]:
            xb = [-b/2 - m*H_des, -b/2, b/2, b/2 + m*H_des]
            yb = [H_des, 0, 0, H_des]
            xe = [-b/2 - m*yn, -b/2, b/2, b/2 + m*yn]
            ye = [yn, 0, 0, yn]
            ax.fill(xe, ye, color="#2980b9", alpha=0.45, label=f"Eau normale (yn = {yn:.2f} m)")
            ax.plot(xb, yb, color="black", linewidth=2.5, label="Paroi canal")
            ax.axhline(yc, color="#e74c3c", linestyle="--", label=f"Hauteur critique (yc = {yc:.2f} m)")

        elif forme == "Circulaire":
            cercle = patches.Circle((0, D/2), D/2, fill=False, edgecolor="black", linewidth=2.5)
            ax.add_patch(cercle)
            ax.axhline(yn, color="#2980b9", linewidth=2.5, label=f"Niveau normal (yn = {yn:.2f} m)")
            ax.axhline(yc, color="#e74c3c", linestyle="--", label=f"Niveau critique (yc = {yc:.2f} m)")
            ax.set_xlim(-D*0.65, D*0.65)
            ax.set_ylim(-0.05, D*1.1)
            ax.set_aspect("equal")

        elif forme == "En U":
            R = D / 2
            H_u = max(D, H_des)
            arc = patches.Arc((0, R), D, D, angle=0, theta1=180, theta2=360, color="black", linewidth=2.5)
            ax.add_patch(arc)
            ax.plot([-R, -R], [R, H_u], color="black", linewidth=2.5)
            ax.plot([R, R], [R, H_u], color="black", linewidth=2.5)
            ax.axhline(yn, color="#2980b9", linewidth=2.5, label=f"Niveau normal (yn = {yn:.2f} m)")
            ax.axhline(yc, color="#e74c3c", linestyle="--", label=f"Niveau critique (yc = {yc:.2f} m)")
            ax.set_xlim(-D*0.7, D*0.7)
            ax.set_ylim(-0.05, H_u*1.1)
            ax.set_aspect("equal")

        ax.set_title(f"Profil en travers - Section {forme}")
        ax.set_xlabel("Largeur (m)")
        ax.set_ylabel("Cote (m)")
        ax.legend()
        ax.grid(True, linestyle=":", alpha=0.6)
        st.pyplot(fig)

    except Exception:
        st.error("Capacité dépassée : l'ouvrage déborde ou se met en charge. Augmentez les dimensions.")

with tab2:
    st.subheader("Dimensionnement de la section la plus économique (Rendement maximal)")
    if forme in ["Rectangulaire", "Trapézoïdale", "Circulaire"]:
        opt = section_optimale(Q, I, Ks, forme, m)
        if forme == "Rectangulaire":
            st.info("Pour une section **Rectangulaire** optimale (b = 2y) :")
            st.write(f"- Largeur au plafond optimale **b_opt** : `{opt['b_opt']:.3f} m`")
            st.write(f"- Tirant d'eau optimal **y_opt** : `{opt['y_opt']:.3f} m`")
        elif forme == "Trapézoïdale":
            st.info(f"Pour une section **Trapézoïdale** optimale avec fruit m = {m} :")
            st.write(f"- Largeur au plafond optimale **b_opt** : `{opt['b_opt']:.3f} m`")
            st.write(f"- Tirant d'eau optimal **y_opt** : `{opt['y_opt']:.3f} m`")
        elif forme == "Circulaire":
            st.info(f"Pour un collecteur **Circulaire** (remplissage maximal recommandé à {opt['taux']:.0f}%) :")
            st.write(f"- Diamètre nominal minimal **D_opt** : `{opt['D_opt']:.3f} m`")
            st.write(f"- Hauteur d'eau correspondante : `{opt['y_opt']:.3f} m`")
    else:
        st.warning("La section optimale analytique s'applique aux profils Rectangulaires, Trapézoïdaux et Circulaires.")

with tab3:
    col_rem, col_res = st.columns(2)
    with col_rem:
        st.subheader("Profil en long (Méthode des pas directs)")
        y_init = st.number_input("Hauteur limite connue y1 (m)", min_value=0.05, value=1.20, step=0.05)
        y_cible = st.number_input("Hauteur cible y2 (m)", min_value=0.05, value=0.85, step=0.05)
        if st.button("Tracer la courbe de remous"):
            x_v, y_v, zf, ze = courbe_remous_pas_directs(Q, I, Ks, y_init, y_cible, 25, forme, b, m, D)
            fig2, ax2 = plt.subplots(figsize=(6, 3.5))
            ax2.plot(x_v, zf, color="black", linewidth=2, label="Radier (Fond)")
            ax2.plot(x_v, ze, color="#2980b9", linewidth=2, label="Ligne d'eau")
            ax2.fill_between(x_v, zf, ze, color="#2980b9", alpha=0.3)
            ax2.set_xlabel("Distance longitudinale x (m)")
            ax2.set_ylabel("Altitude relative (m)")
            ax2.set_title(f"Distance de remous : {abs(x_v[-1]):.1f} m")
            ax2.legend()
            ax2.grid(True, linestyle=":")
            st.pyplot(fig2)

    with col_res:
        st.subheader("Calcul du Ressaut Hydraulique")
        y1_ressaut = st.number_input("Hauteur torrentielle amont y1 (m)", min_value=0.02, value=0.30, step=0.05)
        res_jump = calculer_ressaut(Q, y1_ressaut, forme, b, m, D)
        if res_jump:
            st.success(f"Régime torrentiel détecté (Fr1 = {res_jump['Fr1']:.2f} > 1)")
            st.write(f"- **Hauteur conjuguée aval (y2) :** `{res_jump['y2']:.3f} m`")
            st.write(f"- **Perte de charge (dH) :** `{res_jump['delta_H']:.3f} m`")
            st.write(f"- **Longueur estimée du ressaut :** `{res_jump['L_ressaut']:.2f} m`")
        else:
            st.warning("L'écoulement amont est fluvial (Fr1 <= 1) : aucun ressaut ne peut se former.")

with tab4:
    st.subheader("Bibliothèque des coefficients de rugosité (Modifiable)")
    df_mat = pd.DataFrame.from_dict(st.session_state.materiaux, orient="index")
    df_edite = st.data_editor(df_mat, num_rows="dynamic")
    if st.button("Enregistrer les modifications de matériaux"):
        st.session_state.materiaux = df_edite.to_dict(orient="index")
        st.success("Bibliothèque mise à jour !")

    st.divider()
    st.subheader("Export de la fiche de calcul")
    try:
        res = calculer_regime_uniforme(Q, I, Ks, forme, b, m, D)
        fiche_texte = f"""FICHE DE CALCUL HYDRAULIQUE - ASSAINISSEMENT PLUVIAL
====================================================
DONNEES D'ENTREE :
- Débit de projet (Q) : {Q:.3f} m3/s
- Pente longitudinale (I) : {I:.5f} m/m
- Matériau : {mat_choisi} (Ks = {Ks})
- Géométrie : {forme} (b={b}m, m={m}, D={D}m)

RESULTATS EN REGIME UNIFORME (Convergence {TOLERANCE} m) :
- Hauteur normale (yn) : {res['yn']:.3f} m
- Hauteur critique (yc) : {res['yc']:.3f} m
- Surface mouillée (Sn) : {res['Sn']:.3f} m2
- Périmètre mouillé (Pn) : {res['Pn']:.3f} m
- Rayon hydraulique (Rh) : {res['Rhn']:.3f} m
- Vitesse d'écoulement (V) : {res['Vn']:.2f} m/s
- Nombre de Froude (Fr) : {res['Fr']:.2f} -> {res['regime']}
"""
        st.download_button(
            label="Télécharger la fiche de calcul (.txt)",
            data=fiche_texte,
            file_name="fiche_calcul_hydraulique.txt",
            mime="text/plain"
        )
    except Exception:
        st.info("Corrigez les dimensions dans l'onglet 1 pour générer la fiche de calcul.")
