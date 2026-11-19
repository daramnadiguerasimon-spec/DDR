# hydraulique.py
import numpy as np
from scipy.optimize import brentq

G = 9.81
TOLERANCE = 1e-6

def geometrie_section(forme, y, b=0.0, m=0.0, D=0.0):
    if y <= 0:
        return 1e-9, 1e-9, 1e-9

    if forme == "Rectangulaire":
        S = b * y
        P = b + 2 * y
        T = b

    elif forme == "Trapézoïdale":
        S = (b + m * y) * y
        P = b + 2 * y * np.sqrt(1 + m**2)
        T = b + 2 * m * y

    elif forme == "Circulaire":
        y_eff = min(y, D * 0.9999)
        theta = 2 * np.arccos(1 - 2 * y_eff / D)
        S = (D**2 / 8) * (theta - np.sin(theta))
        P = (D / 2) * theta
        T = D * np.sin(theta / 2)

    elif forme == "En U":
        R = D / 2.0
        if y <= R:
            theta = 2 * np.arccos(1 - y / R)
            S = (R**2 / 2) * (theta - np.sin(theta))
            P = R * theta
            T = 2 * R * np.sin(theta / 2)
        else:
            S_demi = (np.pi * R**2) / 2.0
            P_demi = np.pi * R
            h_droit = y - R
            S = S_demi + D * h_droit
            P = P_demi + 2 * h_droit
            T = D

    return S, P, T

def calculer_regime_uniforme(Q, I, Ks, forme, b=0.0, m=0.0, D=0.0):
    y_max = D * 0.995 if forme == "Circulaire" else 30.0

    def eq_normale(y):
        S, P, _ = geometrie_section(forme, y, b, m, D)
        Rh = S / P
        return Ks * S * (Rh**(2/3)) * np.sqrt(I) - Q

    yn = brentq(eq_normale, 1e-5, y_max, xtol=TOLERANCE)

    def eq_critique(y):
        S, _, T = geometrie_section(forme, y, b, m, D)
        return (Q**2 * T) / (G * S**3) - 1.0

    yc = brentq(eq_critique, 1e-5, y_max, xtol=TOLERANCE)

    Sn, Pn, Tn = geometrie_section(forme, yn, b, m, D)
    Rhn = Sn / Pn
    Vn = Q / Sn
    Fr = Vn / np.sqrt(G * (Sn / Tn))

    if np.isclose(Fr, 1.0, atol=0.02):
        regime = "Critique (Fr ≈ 1)"
    elif Fr < 1.0:
        regime = "Fluvial (Fr < 1)"
    else:
        regime = "Torrentiel (Fr > 1)"

    return {
        "yn": yn, "yc": yc, "Vn": Vn, "Fr": Fr,
        "regime": regime, "Sn": Sn, "Pn": Pn, "Rhn": Rhn, "Tn": Tn
    }

def section_optimale(Q, I, Ks, forme, m=1.5):
    if forme == "Rectangulaire":
        def eq_opt(y):
            b = 2 * y
            S = b * y
            Rh = y / 2.0
            return Ks * S * (Rh**(2/3)) * np.sqrt(I) - Q
        y_opt = brentq(eq_opt, 1e-4, 30.0, xtol=TOLERANCE)
        return {"y_opt": y_opt, "b_opt": 2 * y_opt, "m": 0.0}

    elif forme == "Trapézoïdale":
        def eq_opt(y):
            b = 2 * y * (np.sqrt(1 + m**2) - m)
            S = (b + m * y) * y
            Rh = y / 2.0
            return Ks * S * (Rh**(2/3)) * np.sqrt(I) - Q
        y_opt = brentq(eq_opt, 1e-4, 30.0, xtol=TOLERANCE)
        b_opt = 2 * y_opt * (np.sqrt(1 + m**2) - m)
        return {"y_opt": y_opt, "b_opt": b_opt, "m": m}

    elif forme == "Circulaire":
        taux = 0.80
        def eq_opt(D):
            y = taux * D
            S, P, _ = geometrie_section("Circulaire", y, D=D)
            Rh = S / P
            return Ks * S * (Rh**(2/3)) * np.sqrt(I) - Q
        D_opt = brentq(eq_opt, 0.05, 20.0, xtol=TOLERANCE)
        return {"D_opt": D_opt, "y_opt": taux * D_opt, "taux": taux * 100}

def calculer_ressaut(Q, y1, forme, b=0.0, m=0.0, D=0.0):
    S1, _, T1 = geometrie_section(forme, y1, b, m, D)
    V1 = Q / S1
    Fr1 = V1 / np.sqrt(G * (S1 / T1))

    if Fr1 <= 1.0:
        return None

    if forme == "Rectangulaire":
        y2 = (y1 / 2.0) * (np.sqrt(1 + 8 * Fr1**2) - 1)
    else:
        def impulsion(y):
            S, _, _ = geometrie_section(forme, y, b, m, D)
            yg = y / 2.0 if forme == "Rectangulaire" else (y * (3*b + 2*m*y)) / (6*(b + m*y)) if forme == "Trapézoïdale" else y * 0.45
            return (Q**2) / (G * S) + S * yg

        M1 = impulsion(y1)
        y2 = brentq(lambda y: impulsion(y) - M1, y1 * 1.01, y1 * 20.0, xtol=TOLERANCE)

    S2, _, _ = geometrie_section(forme, y2, b, m, D)
    V2 = Q / S2
    H1 = y1 + (V1**2) / (2 * G)
    H2 = y2 + (V2**2) / (2 * G)
    delta_H = H1 - H2
    longueur_ressaut = 6.0 * (y2 - y1)

    return {"Fr1": Fr1, "y2": y2, "delta_H": delta_H, "L_ressaut": longueur_ressaut}

def courbe_remous_pas_directs(Q, I, Ks, y_debut, y_fin, n_pas, forme, b=0.0, m=0.0, D=0.0):
    y_vals = np.linspace(y_debut, y_fin, n_pas + 1)
    x_vals = [0.0]
    z_fond = [0.0]
    z_eau = [y_vals[0]]

    def charge_et_pente(y):
        S, P, _ = geometrie_section(forme, y, b, m, D)
        Rh = S / P
        V = Q / S
        H = y + (V**2) / (2 * G)
        J = (V / (Ks * (Rh**(2/3))))**2
        return H, J

    for i in range(n_pas):
        y1, y2 = y_vals[i], y_vals[i+1]
        H1, J1 = charge_et_pente(y1)
        H2, J2 = charge_et_pente(y2)
        J_moy = 0.5 * (J1 + J2)
        dx = (H2 - H1) / (I - J_moy)
        x_nouveau = x_vals[-1] + dx
        x_vals.append(x_nouveau)
        z_f = -I * x_nouveau
        z_fond.append(z_f)
        z_eau.append(z_f + y2)

    return np.array(x_vals), y_vals, np.array(z_fond), np.array(z_eau)

def methode_rationnelle(C, i_mm_h, A_ha):
    return (C * i_mm_h * A_ha) / 360.0
