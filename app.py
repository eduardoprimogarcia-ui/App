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
def cargar_datos(archivo, columns):
    if os.path.exists(archivo):
        try:
            return pd.read_csv(archivo)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def guardar_datos(df, archivo):
    df.to_csv(archivo, index=False)

def recargar_datos():
    # Usamos st.session_state para que los datos persistan correctamente en la interfaz
    st.session_state.df_alumnos = cargar_datos("alumnos.csv", ["DNI", "Nombre"])
    st.session_state.df_cursos = cargar_datos("cursos.csv", ["Nombre", "Inicio", "Fin", "Región"])
    st.session_state.df_matriculas = cargar_datos("matriculas.csv", ["Curso", "DNI"])
    st.session_state.df_asistencia = cargar_datos("asistencia.csv", ["Fecha", "Curso", "DNI", "Estado"])

# Inicialización de sesión
if 'df_alumnos' not in st.session_state:
    recargar_datos()

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
# MENÚ LATERAL
# =========================
st.sidebar.title("🚀 ERP Formación")
menu = ["👥 Alumnos", "📚 Cursos", "📝 Matriculación", "🗑️ Eliminar Datos", "🖊️ Pasar Lista", "📊 Reporte"]
choice = st.sidebar.radio("Navegación", menu)

# Acceso rápido a los datos
df_alumnos = st.session_state.df_alumnos
df_cursos = st.session_state.df_cursos
df_matriculas = st.session_state.df_matriculas
df_asistencia = st.session_state.df_asistencia

# =========================
# 1. ALUMNOS
# =========================
if "Alumnos" in choice:
    st.header("👥 Alumnos")
    with st.form("form_alumnos", clear_on_submit=True):
        dni = st.text_input("DNI")
        nombre = st.text_input("Nombre")
        if st.form_submit_button("Guardar") and dni and nombre:
            nuevo = pd.DataFrame([[dni, nombre]], columns=["DNI", "Nombre"])
            st.session_state.df_alumnos = pd.concat([df_alumnos, nuevo], ignore_index=True)
            guardar_datos(st.session_state.df_alumnos, "alumnos.csv")
            st.success("Alumno añadido")
            st.rerun()
    st.dataframe(df_alumnos, use_container_width=True)

# =========================
# 2. CURSOS
# =========================
elif "Cursos" in choice:
    st.header("📚 Cursos")
    with st.form("form_cursos", clear_on_submit=True):
        nombre_c = st.text_input("Curso")
        col1, col2 = st.columns(2)
        inicio = col1.date_input("Inicio", date.today())
        fin = col2.date_input("Fin", date.today() + timedelta(days=60))
        region = st.selectbox("Región", ['MD','CL','CT','AN','VC','PV','GA','RI'], index=1)
        if st.form_submit_button("Crear") and nombre_c:
            nuevo_c = pd.DataFrame([[nombre_c, inicio, fin, region]], columns=["Nombre", "Inicio", "Fin", "Región"])
            st.session_state.df_cursos = pd.concat([df_cursos, nuevo_c], ignore_index=True)
            guardar_datos(st.session_state.df_cursos, "cursos.csv")
            st.success("Curso creado")
            st.rerun()
    st.dataframe(df_cursos, use_container_width=True)

# =========================
# 3. MATRICULACIÓN
# =========================
elif "Matriculación" in choice:
    st.header("📝 Matriculación")
    if df_alumnos.empty or df_cursos.empty:
        st.warning("Faltan alumnos o cursos")
    else:
        with st.form("form_matricula"):
            curso_m = st.selectbox("Curso", df_cursos["Nombre"])
            alumno_m = st.selectbox("Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            dni_m = alumno_m.split("(")[1].replace(")", "")
            if st.form_submit_button("Matricular"):
                if df_matriculas[(df_matriculas["Curso"] == curso_m) & (df_matriculas["DNI"] == dni_m)].empty:
                    nueva_m = pd.DataFrame([[curso_m, dni_m]], columns=["Curso", "DNI"])
                    st.session_state.df_matriculas = pd.concat([df_matriculas, nueva_m], ignore_index=True)
                    guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
                    st.success("Matriculado")
                    st.rerun()
                else:
                    st.warning("Ya matriculado")

# =========================
# 4. ELIMINAR DATOS (ACTUALIZADO)
# =========================
elif "Eliminar Datos" in choice:
    st.header("🗑️ Gestión de Borrado")
    
    opcion = st.selectbox("¿Qué deseas eliminar?", ["Un Alumno", "Un Curso", "TODA la Asistencia"])
    confirmar = st.checkbox("Confirmo que deseo borrar estos datos permanentemente")

    if opcion == "Un Alumno":
        if not df_alumnos.empty:
            sel = st.selectbox("Selecciona Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            dni_b = sel.split("(")[1].replace(")", "")
            if st.button("🗑️ Eliminar Alumno") and confirmar:
                st.session_state.df_alumnos = df_alumnos[df_alumnos["DNI"] != dni_b]
                st.session_state.df_matriculas = df_matriculas[df_matriculas["DNI"] != dni_b]
                st.session_state.df_asistencia = df_asistencia[df_asistencia["DNI"] != dni_b]
                guardar_datos(st.session_state.df_alumnos, "alumnos.csv")
                guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
                guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
                st.success("Alumno eliminado")
                st.rerun()

    elif opcion == "Un Curso":
        if not df_cursos.empty:
            curso_b = st.selectbox("Selecciona Curso", df_cursos["Nombre"])
            if st.button("🗑️ Eliminar Curso") and confirmar:
                st.session_state.df_cursos = df_cursos[df_cursos["Nombre"] != curso_b]
                st.session_state.df_matriculas = df_matriculas[df_matriculas["Curso"] != curso_b]
                st.session_state.df_asistencia = df_asistencia[df_asistencia["Curso"] != curso_b]
                guardar_datos(st.session_state.df_cursos, "cursos.csv")
                guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
                guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
                st.success("Curso eliminado")
                st.rerun()

    elif opcion == "TODA la Asistencia":
        st.warning("⚠️ CUIDADO: Esto borrará el historial de asistencia de TODOS los cursos y alumnos. Los alumnos y cursos NO se borrarán.")
        if st.button("🔥 BORRAR TODA LA ASISTENCIA") and confirmar:
            # Creamos un dataframe vacío con las mismas columnas
            st.session_state.df_asistencia = pd.DataFrame(columns=["Fecha", "Curso", "DNI", "Estado"])
            guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
            st.success("Historial de asistencia limpiado por completo.")
            st.rerun()

# =========================
# 5. PASAR LISTA
# =========================
elif "Pasar Lista" in choice:
    st.header("🖊️ Asistencia diaria")
    if df_matriculas.empty:
        st.info("No hay alumnos matriculados")
    else:
        curso_l = st.selectbox("Curso", df_cursos["Nombre"])
        datos_c = df_cursos[df_cursos["Nombre"] == curso_l].iloc[0]
        lectivos = obtener_calendario_curso(pd.to_datetime(datos_c["Inicio"]).date(), pd.to_datetime(datos_c["Fin"]).date(), datos_c["Región"])
        dia_l = st.selectbox("Día lectivo", lectivos)
        
        dnis_en_curso = df_matriculas[df_matriculas["Curso"] == curso_l]["DNI"]
        alumnos_l = df_alumnos[df_alumnos["DNI"].isin(dnis_en_curso)]

        with st.form("form_asistencia"):
            registros_h = {}
            for _, al in alumnos_l.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(al["Nombre"])
                registros_h[al["DNI"]] = c2.radio("Estado", ["Presente", "Ausente"], key=al["DNI"], horizontal=True)
            
            if st.form_submit_button("Guardar"):
                # Limpiar registros previos de ese día/curso
                df_asistencia = df_asistencia[~((df_asistencia["Fecha"] == str(dia_l)) & (df_asistencia["Curso"] == curso_l))]
                for d, e in registros_h.items():
                    df_asistencia = pd.concat([df_asistencia, pd.DataFrame([[str(dia_l), curso_l, d, e]], columns=["Fecha", "Curso", "DNI", "Estado"])])
                st.session_state.df_asistencia = df_asistencia
                guardar_datos(df_asistencia, "asistencia.csv")
                st.success("Asistencia guardada")

# =========================
# 6. REPORTE
# =========================
elif "Reporte" in choice:
    st.header("📊 Reporte de Situación")
    if df_asistencia.empty:
        st.info("No hay datos de asistencia")
    else:
        curso_r = st.selectbox("Curso", df_cursos["Nombre"])
        datos_r = df_cursos[df_cursos["Nombre"] == curso_r].iloc[0]
        lectivos_r = obtener_calendario_curso(pd.to_datetime(datos_r["Inicio"]).date(), pd.to_datetime(datos_r["Fin"]).date(), datos_r["Región"])
        total_d = len(lectivos_r)
        
        dnis_r = df_matriculas[df_matriculas["Curso"] == curso_r]["DNI"]
        salida = []
        for d in dnis_r:
            nom_a = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
            asist_a = df_asistencia[(df_asistencia["Curso"] == curso_r) & (df_asistencia["DNI"] == d)]
            p = len(asist_a[asist_a["Estado"] == "Presente"])
            f = len(asist_a[asist_a["Estado"] == "Ausente"])
            pct = (f / total_d * 100) if total_d > 0 else 0
            
            if p == 0 and (p+f) > 0: est = "🚫 NO INCORPORADO"
            elif pct >= 80: est = "❌ BAJA"
            elif pct >= 25: est = "⚠️ VARIABLE"
            else: est = "✅ ACTIVO"
            
            salida.append([nom_a, d, p, f, f"{pct:.1f}%", est])
        
        df_rep = pd.DataFrame(salida, columns=["Alumno", "DNI", "Asistencias", "Faltas", "% Faltas", "Estado"])
        st.dataframe(df_rep.style.apply(lambda x: ["background-color:#ff9999" if "BAJA" in str(v) else "background-color:#ffff99" if "VARIABLE" in str(v) else "background-color:#ffcc99" if "NO INCORPORADO" in str(v) else "background-color:#ccffcc" if "ACTIVO" in str(v) else "" for v in x], axis=1), use_container_width=True)
