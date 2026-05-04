import streamlit as st
import pandas as pd
from datetime import date, timedelta
import holidays
import os

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(page_title="ERP Formación 2026", layout="wide", page_icon="🎓")

# =========================
# FUNCIONES CSV
# =========================
def cargar_datos(archivo, columnas):
    if os.path.exists(archivo):
        return pd.read_csv(archivo)
    return pd.DataFrame(columns=columnas)

def guardar_datos(df, archivo):
    df.to_csv(archivo, index=False)

def recargar_datos():
    global df_alumnos, df_cursos, df_matriculas, df_asistencia

    df_alumnos = cargar_datos("alumnos.csv", ["DNI", "Nombre"])
    df_cursos = cargar_datos("cursos.csv", ["Nombre", "Inicio", "Fin", "Región"])
    df_matriculas = cargar_datos("matriculas.csv", ["Curso", "DNI"])
    df_asistencia = cargar_datos("asistencia.csv", ["Fecha", "Curso", "DNI", "Estado"])

# =========================
# CALENDARIO
# =========================
def obtener_calendario_curso(inicio, fin, region):
    years = list(set([inicio.year, fin.year]))
    festivos = holidays.CountryHoliday('ES', subdiv=region, years=years)

    dias = []
    curr = inicio
    while curr <= fin:
        if curr.weekday() < 5 and curr not in festivos:
            dias.append(curr)
        curr += timedelta(days=1)
    return dias

# =========================
# CARGA INICIAL
# =========================
recargar_datos()

# =========================
# MENÚ
# =========================
st.sidebar.title("🚀 ERP Formación")

menu = [
    "👥 Alumnos",
    "📚 Cursos",
    "📝 Matriculación",
    "🗑️ Eliminar Datos",
    "🖊️ Pasar Lista",
    "📊 Reporte"
]

choice = st.sidebar.radio("Navegación", menu)

# =========================
# 1. ALUMNOS
# =========================
if "Alumnos" in choice:
    st.header("👥 Alumnos")

    with st.form("form_alumnos", clear_on_submit=True):
        dni = st.text_input("DNI")
        nombre = st.text_input("Nombre")

        if st.form_submit_button("Guardar") and dni and nombre:
            df_alumnos = pd.concat(
                [df_alumnos, pd.DataFrame([[dni, nombre]], columns=["DNI", "Nombre"])],
                ignore_index=True
            )
            guardar_datos(df_alumnos, "alumnos.csv")
            recargar_datos()
            st.success("Alumno añadido")

    st.dataframe(df_alumnos, use_container_width=True)

# =========================
# 2. CURSOS
# =========================
elif "Cursos" in choice:
    st.header("📚 Cursos")

    with st.form("form_cursos", clear_on_submit=True):
        nombre = st.text_input("Curso")

        col1, col2 = st.columns(2)
        inicio = col1.date_input("Inicio", date.today())
        fin = col2.date_input("Fin", date.today() + timedelta(days=60))

        region = st.selectbox("Región", ['MD','CL','CT','AN','VC','PV','GA','RI'])

        if st.form_submit_button("Crear") and nombre:
            df_cursos = pd.concat(
                [df_cursos, pd.DataFrame([[nombre, inicio, fin, region]],
                columns=["Nombre", "Inicio", "Fin", "Región"])],
                ignore_index=True
            )
            guardar_datos(df_cursos, "cursos.csv")
            recargar_datos()
            st.success("Curso creado")

    st.dataframe(df_cursos, use_container_width=True)

# =========================
# 3. MATRICULACIÓN
# =========================
elif "Matriculación" in choice:
    st.header("📝 Matriculación")

    if df_alumnos.empty or df_cursos.empty:
        st.warning("Faltan datos")
    else:
        with st.form("form_matricula"):
            curso = st.selectbox("Curso", df_cursos["Nombre"])
            alumno = st.selectbox(
                "Alumno",
                df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")"
            )

            dni = alumno.split("(")[1].replace(")", "")

            if st.form_submit_button("Matricular"):
                if df_matriculas[(df_matriculas["Curso"] == curso) & (df_matriculas["DNI"] == dni)].empty:
                    df_matriculas = pd.concat(
                        [df_matriculas, pd.DataFrame([[curso, dni]], columns=["Curso", "DNI"])],
                        ignore_index=True
                    )
                    guardar_datos(df_matriculas, "matriculas.csv")
                    recargar_datos()
                    st.success("Matriculado")
                else:
                    st.warning("Ya matriculado")

# =========================
# 4. ELIMINAR DATOS (BORRADO REAL)
# =========================
elif "Eliminar Datos" in choice:
    st.header("🗑️ Eliminación Total")

    opcion = st.selectbox("Tipo de dato", ["Alumnos", "Cursos", "Matriculaciones", "Asistencia"])
    confirmar = st.checkbox("Confirmo que quiero eliminar")

    # ---------------- ALUMNOS ----------------
    if opcion == "Alumnos":
        if not df_alumnos.empty:
            sel = st.selectbox("Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            dni = sel.split("(")[1].replace(")", "")

            if st.button("🗑️ Eliminar alumno") and confirmar:
                df_alumnos = df_alumnos[df_alumnos["DNI"] != dni]
                df_matriculas = df_matriculas[df_matriculas["DNI"] != dni]
                df_asistencia = df_asistencia[df_asistencia["DNI"] != dni]

                guardar_datos(df_alumnos, "alumnos.csv")
                guardar_datos(df_matriculas, "matriculas.csv")
                guardar_datos(df_asistencia, "asistencia.csv")

                recargar_datos()
                st.success("Alumno eliminado")
                st.rerun()

    # ---------------- CURSOS ----------------
    elif opcion == "Cursos":
        if not df_cursos.empty:
            curso = st.selectbox("Curso", df_cursos["Nombre"])

            if st.button("🗑️ Eliminar curso") and confirmar:
                df_cursos = df_cursos[df_cursos["Nombre"] != curso]
                df_matriculas = df_matriculas[df_matriculas["Curso"] != curso]
                df_asistencia = df_asistencia[df_asistencia["Curso"] != curso]

                guardar_datos(df_cursos, "cursos.csv")
                guardar_datos(df_matriculas, "matriculas.csv")
                guardar_datos(df_asistencia, "asistencia.csv")

                recargar_datos()
                st.success("Curso eliminado")
                st.rerun()

# =========================
# 5. PASAR LISTA
# =========================
elif "Pasar Lista" in choice:
    st.header("🖊️ Asistencia diaria")

    if df_matriculas.empty:
        st.info("No hay alumnos")
    else:
        curso = st.selectbox("Curso", df_cursos["Nombre"])
        datos = df_cursos[df_cursos["Nombre"] == curso].iloc[0]

        lectivos = obtener_calendario_curso(
            pd.to_datetime(datos["Inicio"]).date(),
            pd.to_datetime(datos["Fin"]).date(),
            datos["Región"]
        )

        dia = st.selectbox("Día lectivo", lectivos)

        alumnos = df_alumnos[df_alumnos["DNI"].isin(
            df_matriculas[df_matriculas["Curso"] == curso]["DNI"]
        )]

        with st.form("asistencia"):
            registros = {}

            for _, a in alumnos.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(a["Nombre"])
                registros[a["DNI"]] = col2.radio(
                    "Estado",
                    ["Presente", "Ausente"],
                    key=a["DNI"]
                )

            if st.form_submit_button("Guardar"):
                df_asistencia = df_asistencia[
                    ~((df_asistencia["Fecha"] == str(dia)) &
                      (df_asistencia["Curso"] == curso))
                ]

                for dni, est in registros.items():
                    df_asistencia = pd.concat([
                        df_asistencia,
                        pd.DataFrame([[str(dia), curso, dni, est]],
                        columns=["Fecha", "Curso", "DNI", "Estado"])
                    ])

                guardar_datos(df_asistencia, "asistencia.csv")
                recargar_datos()
                st.success("Asistencia guardada")

# =========================
# 6. REPORTE
# =========================
elif "Reporte" in choice:
    st.header("📊 Reporte")

    if df_asistencia.empty:
        st.warning("Sin datos")
    else:
        curso = st.selectbox("Curso", df_cursos["Nombre"])
        datos = df_cursos[df_cursos["Nombre"] == curso].iloc[0]

        lectivos = obtener_calendario_curso(
            pd.to_datetime(datos["Inicio"]).date(),
            pd.to_datetime(datos["Fin"]).date(),
            datos["Región"]
        )

        total = len(lectivos)
        dnis = df_matriculas[df_matriculas["Curso"] == curso]["DNI"]

        salida = []

        for dni in dnis:
            nombre = df_alumnos[df_alumnos["DNI"] == dni]["Nombre"].iloc[0]

            asist = df_asistencia[
                (df_asistencia["Curso"] == curso) &
                (df_asistencia["DNI"] == dni)
            ]

            pres = len(asist[asist["Estado"] == "Presente"])
            falt = len(asist[asist["Estado"] == "Ausente"])

            pct = (falt / total) * 100 if total else 0

            if pres == 0:
                estado = "🚫 NO INCORPORADO"
            elif pct >= 80:
                estado = "❌ BAJA"
            elif pct >= 25:
                estado = "⚠️ VARIABLE"
            else:
                estado = "✅ ACTIVO"

            salida.append([nombre, dni, pres, falt, f"{pct:.1f}%", estado])

        df_final = pd.DataFrame(
            salida,
            columns=["Alumno", "DNI", "Asistencias", "Faltas", "%", "Estado"]
        )

        def estilo(row):
            color = ""
            if "BAJA" in row["Estado"]:
                color = "background-color:#ff9999"
            elif "VARIABLE" in row["Estado"]:
                color = "background-color:#ffff99"
            elif "NO INCORPORADO" in row["Estado"]:
                color = "background-color:#ffcc99"
            elif "ACTIVO" in row["Estado"]:
                color = "background-color:#ccffcc"
            return [color] * len(row)

        st.dataframe(df_final.style.apply(estilo, axis=1))