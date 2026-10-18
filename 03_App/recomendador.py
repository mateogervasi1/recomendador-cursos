"""
Lógica del sistema de recomendación (sin interfaz).
Es el mismo código de los notebooks 04-06, reunido para que la app lo use.

Modelo final: Híbrido SVD + Perfil declarado (pesos y factores leídos de config_modelo_final.json).
Cold Start: Perfil declarado (interés principal/secundario + idioma + nivel + popularidad).
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

CARPETA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NIVEL_ADECUADO = {"Principiante": "Básico", "Intermedio": "Intermedio", "Avanzado": "Intermedio"}


# ------------------------------------------------------------------
# Carga de datos
# ------------------------------------------------------------------
def cargar_datos(carpeta=CARPETA_DATOS):
    cursos = pd.read_csv(os.path.join(carpeta, "items_clean.csv"))
    usuarios = pd.read_csv(os.path.join(carpeta, "users_clean.csv"))
    interacciones = pd.read_csv(os.path.join(carpeta, "interactions_clean.csv"), parse_dates=["timestamp"])
    with open(os.path.join(carpeta, "config_modelo_final.json"), encoding="utf-8") as f:
        config = json.load(f)
    return cursos, usuarios, interacciones, config


# ------------------------------------------------------------------
# Preparación: matriz usuario-curso
# ------------------------------------------------------------------
def preparar(datos, cursos):
    item_ids = cursos["item_id"].to_numpy()
    user_ids = np.sort(datos["user_id"].unique())
    u_idx = {u: i for i, u in enumerate(user_ids)}
    i_idx = {it: j for j, it in enumerate(item_ids)}
    agregada = datos.groupby(["user_id", "item_id"])["interaction_weight"].sum().reset_index()
    agregada = agregada[agregada["interaction_weight"] > 0]
    M = csr_matrix((agregada["interaction_weight"].astype(float),
                    (agregada["user_id"].map(u_idx), agregada["item_id"].map(i_idx))),
                   shape=(len(user_ids), len(item_ids)))
    vistos = datos.groupby("user_id")["item_id"].apply(set).to_dict()
    eventos = datos[datos["event_type"] != "calificacion"].groupby("user_id").size().to_dict()
    return {"M": M, "user_ids": user_ids, "item_ids": item_ids, "u_idx": u_idx, "i_idx": i_idx,
            "vistos": vistos, "eventos": eventos, "cursos": cursos}


def top_k(scores, prep, user_id, k=10):
    vistos = prep["vistos"].get(user_id, set())
    orden = np.argsort(-np.asarray(scores, dtype=float), kind="stable")
    return [int(prep["item_ids"][j]) for j in orden if prep["item_ids"][j] not in vistos][:k]


# ------------------------------------------------------------------
# Modelos
# ------------------------------------------------------------------
def popularidad(prep):
    return np.asarray(prep["M"].sum(axis=0)).ravel()


def modelo_svd(prep, n_factores=5):
    M = prep["M"]
    svd = TruncatedSVD(n_components=min(n_factores, min(M.shape) - 1), random_state=42)
    U = svd.fit_transform(M)
    V = svd.components_
    return lambda user_id: U[prep["u_idx"][user_id]] @ V


def puntaje_perfil(prep, interes_principal, interes_secundario="Ninguno", idioma=None, nivel_experiencia=None,
                   peso_secundario=0.5, factor_idioma=0.4, factor_nivel=0.7):
    c = prep["cursos"]
    pop = popularidad(prep) + 1
    afinidad = np.where(c["categoria"] == interes_principal, 1.0,
               np.where(c["categoria"] == interes_secundario, peso_secundario, 0.01))
    f_idioma = np.where(c["idioma"] == idioma, 1.0, factor_idioma) if idioma else 1.0
    f_nivel = np.where(c["nivel"] == NIVEL_ADECUADO.get(nivel_experiencia), 1.0, factor_nivel) if nivel_experiencia else 1.0
    return pop * afinidad * f_idioma * f_nivel


def fusion_rangos(prep, user_id, rankings_pesos, k):
    """Fusión por rango recíproco ponderado: cada curso suma peso / posición en cada ranking."""
    puntaje = {}
    for peso, ranking in rankings_pesos:
        for posicion, item in enumerate(ranking, start=1):
            puntaje[item] = puntaje.get(item, 0) + peso / posicion
    return [it for it, _ in sorted(puntaje.items(), key=lambda z: -z[1])][:k]


# ------------------------------------------------------------------
# Sistema completo
# ------------------------------------------------------------------
class SistemaRecomendacion:
    def __init__(self, cursos, usuarios, interacciones, config):
        self.cursos = cursos
        self.usuarios = usuarios.set_index("user_id")
        self.config = config
        hp = config["hiperparametros"]
        self.peso_svd = hp["peso_svd_hibrido_perfil"]
        self.parametros_perfil = hp.get("perfil", {})
        self.umbral = config.get("cold_start", {}).get("umbral_eventos_historial", 5)
        self.interacciones = interacciones
        self.prep = preparar(interacciones, cursos)
        self.svd = modelo_svd(self.prep, hp["n_factores"])
        self.ranking_popularidad = top_k(popularidad(self.prep), self.prep, None, len(cursos))

    def _perfil(self, interes_principal, interes_secundario, idioma, nivel):
        return puntaje_perfil(self.prep, interes_principal, interes_secundario, idioma, nivel, **self.parametros_perfil)

    def tiene_historial(self, user_id):
        return self.prep["eventos"].get(user_id, 0) >= self.umbral

    def recomendar_estudiante(self, user_id, k=5):
        """Devuelve (método usado, lista de item_id, lista de item_id del ranking SVD)."""
        p = self.usuarios.loc[user_id]
        scores_perfil = self._perfil(p["interes_principal"], p["interes_secundario"],
                                     p["idioma_preferido"], p["nivel_experiencia"])
        if self.tiene_historial(user_id):
            candidatos = 30
            r_svd = top_k(self.svd(user_id), self.prep, user_id, candidatos)
            r_perfil = top_k(scores_perfil, self.prep, user_id, candidatos)
            recs = fusion_rangos(self.prep, user_id, [(self.peso_svd, r_svd), (1 - self.peso_svd, r_perfil)], k)
            return "Modelo final (Híbrido SVD + Perfil)", recs, r_svd[:10]
        return "Cold Start (perfil declarado)", top_k(scores_perfil, self.prep, user_id, k), []

    def recomendar_nuevo(self, interes_principal, idioma, nivel, interes_secundario="Ninguno", k=5):
        return top_k(self._perfil(interes_principal, interes_secundario, idioma, nivel), self.prep, None, k)

    def historial(self, user_id):
        """Cursos del estudiante con la etapa máxima alcanzada y su rating (si calificó)."""
        h = self.interacciones[self.interacciones["user_id"] == user_id]
        if h.empty:
            return pd.DataFrame(columns=["titulo", "categoria", "idioma", "etapa", "rating"])
        orden = {"inscripcion": 1, "avance_50": 2, "completado": 3}
        nombres = {1: "Inscrito", 2: "Avanzó 50%", 3: "Completado"}
        nivel_etapa = (h[h["event_type"].isin(orden)].assign(o=lambda d: d["event_type"].map(orden))
                       .groupby("item_id")["o"].max())
        rating = h.groupby("item_id")["rating"].max()
        t = pd.DataFrame({"orden": nivel_etapa, "rating": rating}).reset_index()
        t = t.merge(self.cursos[["item_id", "titulo", "categoria", "idioma"]], on="item_id")
        t = t.sort_values(["orden", "rating"], ascending=False)
        t["etapa"] = t["orden"].map(nombres)
        return t[["titulo", "categoria", "idioma", "etapa", "rating"]].reset_index(drop=True)

    def razones(self, item_id, perfil, ranking_svd=()):
        """Explicación simple de por qué se recomienda un curso."""
        c = self.cursos.set_index("item_id").loc[item_id]
        r = []
        if c["categoria"] == perfil.get("interes_principal"):
            r.append(f"Es de tu interés principal ({c['categoria']})")
        elif c["categoria"] == perfil.get("interes_secundario"):
            r.append(f"Es de tu interés secundario ({c['categoria']})")
        if perfil.get("idioma") and c["idioma"] == perfil.get("idioma"):
            r.append(f"Está en {c['idioma'].lower()}")
        if perfil.get("nivel") and c["nivel"] == NIVEL_ADECUADO.get(perfil.get("nivel")):
            r.append(f"Nivel adecuado para ti ({c['nivel']})")
        if item_id in ranking_svd:
            r.append("Lo tomaron estudiantes con un historial parecido al tuyo")
        if item_id in self.ranking_popularidad[:10]:
            r.append("Está entre los 10 cursos más populares")
        return r or ["Curso popular en la plataforma"]
