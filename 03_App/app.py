"""
App Streamlit — Sistema de recomendación de cursos online (Proyecto EdTech)
Ejecutar localmente:  streamlit run app.py
"""
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

from recomendador import SistemaRecomendacion, cargar_datos

st.set_page_config(page_title="Recomendador de cursos", page_icon="🎓", layout="wide")

CATEGORIAS = ["Data Science", "Marketing Digital", "Python"]
IDIOMAS = ["Español", "Portugués", "Inglés"]
NIVELES = ["Principiante", "Intermedio", "Avanzado"]
ICONO_CATEGORIA = {"Data Science": "📊", "Marketing Digital": "📣", "Python": "🐍"}


# ------------------------------------------------------------------
# Carga (se hace una sola vez y queda en memoria)
# ------------------------------------------------------------------
@st.cache_resource(show_spinner="Cargando datos y entrenando el modelo...")
def iniciar_sistema():
    cursos, usuarios, interacciones, config = cargar_datos()
    return SistemaRecomendacion(cursos, usuarios, interacciones, config), cursos, usuarios, config


sistema, cursos, usuarios, config = iniciar_sistema()
info_cursos = cursos.set_index("item_id")


def tarjeta_curso(rank, item_id, razones):
    """Muestra un curso recomendado como tarjeta."""
    c = info_cursos.loc[item_id]
    with st.container(border=True):
        col_a, col_b = st.columns([0.08, 0.92])
        col_a.markdown(f"### {rank}")
        col_b.markdown(f"**{c['titulo']}**")
        col_b.caption(f"{ICONO_CATEGORIA.get(c['categoria'], '📘')} {c['categoria']}  ·  {c['formato']}  ·  "
                      f"Nivel {c['nivel']}  ·  {c['idioma']}  ·  Creador: {c['creador']}")
        col_b.markdown("**¿Por qué te lo recomendamos?** " + " · ".join(razones))
        col_b.markdown(f"[🔎 Buscar en YouTube](https://www.youtube.com/results?search_query={quote_plus(c['titulo'])})")


def mostrar_recomendaciones(recs, perfil, ranking_svd=()):
    if not recs:
        st.warning("No hay cursos nuevos para recomendar: este estudiante ya tomó todo el catálogo.")
        return
    for i, item_id in enumerate(recs, start=1):
        tarjeta_curso(i, item_id, sistema.razones(item_id, perfil, ranking_svd))


# ------------------------------------------------------------------
# Barra lateral
# ------------------------------------------------------------------
st.sidebar.title("🎓 Recomendador de cursos")
modo = st.sidebar.radio("¿Quién usa la plataforma?", ["👤 Estudiante registrado", "✨ Nuevo estudiante"])
k = st.sidebar.slider("Número de recomendaciones (K)", min_value=3, max_value=10, value=int(config["k_recomendado"]))
st.sidebar.divider()
st.sidebar.markdown(
    f"**Modelo final:** {config['modelo_final']}  \n"
    f"**Cold Start:** perfil declarado  \n"
    f"**Catálogo:** {len(cursos)} cursos reales (YouTube)  \n"
    f"**Estudiantes:** {len(usuarios)} (simulados)"
)
st.sidebar.caption("Proyecto académico. Los estudiantes y sus interacciones son datos simulados.")

tab_rec, tab_info = st.tabs(["Recomendaciones", "¿Cómo funciona?"])

# ------------------------------------------------------------------
# Pestaña 1: recomendaciones
# ------------------------------------------------------------------
with tab_rec:
    if modo == "👤 Estudiante registrado":
        st.header("👤 Estudiante registrado")
        tipo = st.radio("Mostrar estudiantes:", ["Con historial (modelo final)", "Sin historial suficiente (Cold Start)"],
                        horizontal=True)
        con_historial = tipo.startswith("Con")
        ids = [int(u) for u in usuarios["user_id"] if sistema.tiene_historial(int(u)) == con_historial]
        perfiles = usuarios.set_index("user_id")

        def etiqueta(u):
            p = perfiles.loc[u]
            n = sistema.prep["eventos"].get(u, 0)
            return f"Estudiante {u} · {p['interes_principal']} · {p['idioma_preferido']} · {n} eventos"

        user_id = st.selectbox(f"Elige un estudiante ({len(ids)} disponibles)", ids, format_func=etiqueta)
        p = perfiles.loc[user_id]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Interés principal", p["interes_principal"])
        c2.metric("Interés secundario", p["interes_secundario"])
        c3.metric("Idioma preferido", p["idioma_preferido"])
        c4.metric("Nivel", p["nivel_experiencia"])

        historial = sistema.historial(user_id)
        with st.expander(f"📚 Historial del estudiante ({len(historial)} cursos)"):
            if historial.empty:
                st.info("Este estudiante todavía no tiene cursos en su historial.")
            else:
                st.dataframe(historial, hide_index=True, use_container_width=True)

        metodo, recs, ranking_svd = sistema.recomendar_estudiante(user_id, k)
        if metodo.startswith("Modelo final"):
            st.success(f"**Método usado:** {metodo}. El estudiante tiene historial suficiente "
                       f"(≥ {sistema.umbral} eventos), así que combinamos su comportamiento con su perfil.")
        else:
            st.info(f"**Método usado:** {metodo}. El estudiante tiene menos de {sistema.umbral} eventos, "
                    "así que usamos las preferencias que declaró al registrarse.")

        st.subheader(f"Top-{k} cursos recomendados")
        perfil = {"interes_principal": p["interes_principal"], "interes_secundario": p["interes_secundario"],
                  "idioma": p["idioma_preferido"], "nivel": p["nivel_experiencia"]}
        mostrar_recomendaciones(recs, perfil, ranking_svd)

    else:
        st.header("✨ Nuevo estudiante")
        st.write("Cuéntanos qué te interesa y te recomendamos cursos para empezar. "
                 "No necesitas tener historial en la plataforma.")
        with st.form("formulario"):
            c1, c2 = st.columns(2)
            interes = c1.selectbox("¿Qué quieres aprender?", CATEGORIAS)
            secundario = c2.selectbox("¿Algún otro tema? (opcional)", ["Ninguno"] + CATEGORIAS)
            c3, c4 = st.columns(2)
            idioma = c3.selectbox("¿En qué idioma prefieres los cursos?", IDIOMAS)
            nivel = c4.selectbox("¿Cuál es tu nivel?", NIVELES)
            enviado = st.form_submit_button("Recomiéndame cursos", type="primary")

        if enviado:
            if secundario == interes:
                secundario = "Ninguno"
            recs = sistema.recomendar_nuevo(interes, idioma, nivel, secundario, k)
            st.info("**Método usado:** Cold Start (perfil declarado): cursos populares ordenados según "
                    "tu interés, idioma y nivel.")
            st.subheader(f"Top-{k} cursos para empezar")
            perfil = {"interes_principal": interes, "interes_secundario": secundario, "idioma": idioma, "nivel": nivel}
            mostrar_recomendaciones(recs, perfil)
        else:
            st.caption("👆 Completa el formulario y presiona el botón.")

# ------------------------------------------------------------------
# Pestaña 2: cómo funciona
# ------------------------------------------------------------------
with tab_info:
    st.header("¿Cómo funciona el sistema?")
    st.markdown(f"""
**1. ¿El estudiante tiene historial suficiente (≥ {sistema.umbral} eventos)?**

- **Sí → Modelo final: Híbrido SVD + Perfil.** Combina dos rankings:
  - **SVD** ({config['hiperparametros']['n_factores']} factores latentes): aprende del **comportamiento**, es decir, qué cursos tomaron estudiantes con historial parecido.
  - **Perfil declarado**: cursos populares ordenados según el **interés, idioma y nivel** que el estudiante indicó al registrarse.
  - Se fusionan por posición: {config['hiperparametros']['peso_svd_hibrido_perfil']:.0%} SVD y {1 - config['hiperparametros']['peso_svd_hibrido_perfil']:.0%} perfil.
- **No → Cold Start:** solo el perfil declarado.

**2.** Nunca se recomiendan cursos que el estudiante ya tomó.

**3.** Las señales de interés tienen pesos distintos: inscripción = 1, avance al 50% = 3, curso completado = 5.
""")
    st.subheader("Resultados de la evaluación offline (test, K = 10)")
    met = pd.Series(config["metricas_test_k10"]).rename("valor").to_frame()
    st.dataframe(met.style.format("{:.3f}"), use_container_width=False)
    st.caption("Evaluado con datos futuros (junio 2026) que el modelo no vio al entrenar. "
               "Detalle completo en el notebook 05_Evaluacion.")
    st.subheader("Limitaciones")
    st.markdown("""
- Los estudiantes y sus interacciones son **simulados**: la ventaja del perfil declarado está en parte inflada por las reglas de la simulación.
- La evaluación es **offline**: para medir si las recomendaciones aumentan la finalización de cursos haría falta una prueba A/B.
- El catálogo es pequeño (60 cursos de YouTube en 3 categorías).
""")
