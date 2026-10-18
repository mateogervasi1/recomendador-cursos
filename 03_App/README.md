# App — Recomendador de cursos online (Proyecto EdTech)

Prototipo en **Streamlit** del sistema de recomendación.

- **Estudiante registrado con historial (≥ 5 eventos):** modelo final **Híbrido SVD + Perfil**.
- **Estudiante con poco o ningún historial / visitante nuevo:** **Cold Start** por perfil declarado (interés, idioma y nivel).

> Proyecto académico. El catálogo (60 cursos) es real (YouTube Data API); los estudiantes y sus interacciones son **simulados**.

## Estructura

```
03_App/
├── app.py               # interfaz Streamlit
├── recomendador.py      # lógica del sistema (mismo código de los notebooks 04-06)
├── requirements.txt     # dependencias
├── .streamlit/config.toml
└── data/
    ├── items_clean.csv
    ├── users_clean.csv
    ├── interactions_clean.csv
    └── config_modelo_final.json   # modelo elegido y sus hiperparámetros (notebooks 05 y 06)
```

La app se entrena al iniciar con **todas** las interacciones limpias (train + test), como se haría en producción,
usando los hiperparámetros elegidos en el notebook 05 (`config_modelo_final.json`).

## Ejecutar en tu computadora

```bash
cd 03_App
pip install -r requirements.txt
streamlit run app.py
```
Se abre en el navegador en `http://localhost:8501`.

## Publicar en Streamlit Community Cloud (gratis)

1. Crea una cuenta en **github.com** (si no tienes).
2. Crea un repositorio nuevo **público** (por ejemplo `recomendador-cursos`) y sube la carpeta `03_App` completa
   (botón **Add file → Upload files**, arrastra la carpeta y presiona **Commit changes**).
3. Entra a **share.streamlit.io** e inicia sesión con tu cuenta de GitHub.
4. Presiona **Create app → Deploy a public app from GitHub** y completa:
   - **Repository:** `tu_usuario/recomendador-cursos`
   - **Branch:** `main`
   - **Main file path:** `03_App/app.py`
   - (Opcional) **App URL:** un nombre corto, por ejemplo `recomendador-edtech`.
   - En **Advanced settings**, elige **Python 3.11**.
5. Presiona **Deploy**. En 2–3 minutos tendrás un link como `https://recomendador-edtech.streamlit.app`.

**Si actualizas los datos** (por ejemplo, vuelves a ejecutar los notebooks), copia los 4 archivos de `Data/processed`
(`items_clean.csv`, `users_clean.csv`, `interactions_clean.csv`, `config_modelo_final.json`) a `03_App/data/`
y súbelos de nuevo a GitHub: la app se actualiza sola.

## Guion sugerido para la demo (4 min)

1. **Estudiante con historial** (por ejemplo, el 238: Python, portugués): abrir el historial, mostrar el método usado y leer las razones de cada recomendación.
2. **Estudiante sin historial suficiente** (por ejemplo, el 7): mostrar que el sistema cambia automáticamente a Cold Start.
3. **Nuevo estudiante:** llenar el formulario (Python + español), recomendar; luego cambiar a portugués y mostrar cómo cambia la lista.
4. Pestaña **¿Cómo funciona?**: explicar el flujo y las métricas.
