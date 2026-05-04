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
# FUNCIONES DATA (CSV)
# =========================
def cargar_datos(archivo, columnas):
    if os.path.exists(archivo):
        try:
            return pd.read_csv(archivo)
        except:
            return pd.DataFrame(columns=columnas)
    return pd.DataFrame(columns=columnas)

def guardar_datos(df, archivo):
    df.to_csv(archivo, index=False)

def recargar_datos():
    st.session_state.df_alumnos = cargar_datos("alumnos.csv", ["DNI", "Nombre"])
    st.session_state.df_cursos = cargar_datos("cursos.csv", ["Nombre", "Inicio", "Fin", "Región"])
    st.session_state.df_matriculas = cargar_datos("matriculas.csv", ["Curso", "DNI"])
    st.session_state.df_asistencia = cargar_datos("asistencia.csv", ["Fecha", "Curso", "DNI", "Estado"])

if 'df_alumnos' not in st.session_state:
    recargar_datos()

# =========================
# LÓGICA CALENDARIO
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
# INTERFAZ
# =========================
st.sidebar.title("🚀 ERP Formación")
menu = ["👥 Alumnos", "📚 Cursos", "📝 Matriculación", "🗑️ Eliminar Datos", "🖊️ Pasar Lista", "📊 Reporte"]
choice = st.sidebar.radio("Menú", menu)

df_alumnos = st.session_state.df_alumnos
df_cursos = st.session_state.df_cursos
df_matriculas = st.session_state.df_matriculas
df_asistencia = st.session_state.df_asistencia

# 1. ALUMNOS
if "Alumnos" in choice:
    st.header("👥 Gestión de Alumnos")
    with st.form("f_al"):
        dni = st.text_input("DNI")
        nom = st.text_input("Nombre")
        if st.form_submit_button("Añadir") and dni and nom:
            st.session_state.df_alumnos = pd.concat([df_alumnos, pd.DataFrame([[dni, nom]], columns=["DNI", "Nombre"])], ignore_index=True)
            guardar_datos(st.session_state.df_alumnos, "alumnos.csv")
            st.rerun()
    st.dataframe(df_alumnos, use_container_width=True)

# 2. CURSOS
elif "Cursos" in choice:
    st.header("📚 Gestión de Cursos")
    with st.form("f_cu"):
        n_c = st.text_input("Nombre Curso")
        c1, c2 = st.columns(2)
        ini = c1.date_input("Inicio")
        fin = c2.date_input("Fin", date.today() + timedelta(days=30))
        reg = st.selectbox("Región", ['MD','CL','CT','AN','VC','PV','GA','RI'], index=1)
        if st.form_submit_button("Crear") and n_c:
            st.session_state.df_cursos = pd.concat([df_cursos, pd.DataFrame([[n_c, ini, fin, reg]], columns=["Nombre", "Inicio", "Fin", "Región"])], ignore_index=True)
            guardar_datos(st.session_state.df_cursos, "cursos.csv")
            st.rerun()
    st.dataframe(df_cursos, use_container_width=True)

# 3. MATRICULACIÓN
elif "Matriculación" in choice:
    st.header("📝 Matricular en Curso")
    if df_alumnos.empty or df_cursos.empty: st.info("Datos insuficientes")
    else:
        with st.form("f_ma"):
            cur = st.selectbox("Curso", df_cursos["Nombre"])
            alu = st.selectbox("Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            d_m = alu.split("(")[1].replace(")", "")
            if st.form_submit_button("Matricular"):
                if df_matriculas[(df_matriculas["Curso"] == cur) & (df_matriculas["DNI"] == d_m)].empty:
                    st.session_state.df_matriculas = pd.concat([df_matriculas, pd.DataFrame([[cur, d_m]], columns=["Curso", "DNI"])], ignore_index=True)
                    guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
                    st.success("Hecho")
                    st.rerun()

# 4. ELIMINAR DATOS (PERSONALIZADO)
elif "Eliminar Datos" in choice:
    st.header("🗑️ Zona de Borrado")
    op = st.selectbox("¿Qué borrar?", ["Un Alumno", "Un Curso", "Asistencia de un Alumno", "TODA la Asistencia"])
    conf = st.checkbox("Confirmar acción")

    if op == "Asistencia de un Alumno":
        if not df_matriculas.empty:
            c_s = st.selectbox("Curso", df_cursos["Nombre"])
            dnis_c = df_matriculas[df_matriculas["Curso"] == c_s]["DNI"]
            alus_c = df_alumnos[df_alumnos["DNI"].isin(dnis_c)]
            if not alus_c.empty:
                a_s = st.selectbox("Alumno", alus_c["Nombre"] + " (" + alus_c["DNI"] + ")")
                d_l = a_s.split("(")[1].replace(")", "")
                if st.button("Limpiar historial de este alumno") and conf:
                    st.session_state.df_asistencia = df_asistencia[~((df_asistencia["DNI"] == d_l) & (df_asistencia["Curso"] == c_s))]
                    guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
                    st.rerun()

    elif op == "TODA la Asistencia":
        if st.button("BORRAR TODO EL HISTORIAL") and conf:
            st.session_state.df_asistencia = pd.DataFrame(columns=["Fecha", "Curso", "DNI", "Estado"])
            guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
            st.rerun()
    # (Resto de opciones Alumno/Curso similares...)

# 5. PASAR LISTA
elif "Pasar Lista" in choice:
    st.header("🖊️ Pasar Lista")
    if not df_matriculas.empty:
        c_l = st.selectbox("Curso", df_cursos["Nombre"])
        d_c = df_cursos[df_cursos["Nombre"] == c_l].iloc[0]
        lec = obtener_calendario_curso(pd.to_datetime(d_c["Inicio"]).date(), pd.to_datetime(d_c["Fin"]).date(), d_c["Región"])
        f_l = st.selectbox("Fecha", lec)
        d_m = df_matriculas[df_matriculas["Curso"] == c_l]["DNI"]
        a_m = df_alumnos[df_alumnos["DNI"].isin(d_m)]
        
        with st.form("f_as"):
            res = {}
            for _, r in a_m.iterrows():
                col1, col2 = st.columns([3,1])
                col1.write(r["Nombre"])
                res[r["DNI"]] = col2.radio("S/N", ["Presente", "Ausente"], key=r["DNI"], horizontal=True)
            if st.form_submit_button("Guardar"):
                df_asistencia = df_asistencia[~((df_asistencia["Fecha"] == str(f_l)) & (df_asistencia["Curso"] == c_l))]
                for d, e in res.items():
                    df_asistencia = pd.concat([df_asistencia, pd.DataFrame([[str(f_l), c_l, d, e]], columns=["Fecha", "Curso", "DNI", "Estado"])])
                st.session_state.df_asistencia = df_asistencia
                guardar_datos(df_asistencia, "asistencia.csv")
                st.success("Guardado")

# 6. REPORTE
elif "Reporte" in choice:
    st.header("📊 Reporte")
    if not df_asistencia.empty:
        c_r = st.selectbox("Curso", df_cursos["Nombre"])
        d_r = df_cursos[df_cursos["Nombre"] == c_r].iloc[0]
        l_r = obtener_calendario_curso(pd.to_datetime(d_r["Inicio"]).date(), pd.to_datetime(d_r["Fin"]).date(), d_r["Región"])
        total = len(l_r)
        dnis_r = df_matriculas[df_matriculas["Curso"] == c_r]["DNI"]
        filas = []
        for d in dnis_r:
            n = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
            as_a = df_asistencia[(df_asistencia["Curso"] == c_r) & (df_asistencia["DNI"] == d)]
            p, f = len(as_a[as_a["Estado"]=="Presente"]), len(as_a[as_a["Estado"]=="Ausente"])
            pct = (f/total*100) if total > 0 else 0
            if p == 0 and (p+f)>0: est = "🚫 NO INCORPORADO"
            elif pct >= 80: est = "❌ BAJA"
            elif pct >= 25: est = "⚠️ VARIABLE"
            else: est = "✅ ACTIVO"
            filas.append([n, d, p, f, f"{pct:.1f}%", est])
        
        df_f = pd.DataFrame(filas, columns=["Alumno", "DNI", "Pres.", "Faltas", "%", "Estado"])
        st.dataframe(df_f.style.apply(lambda x: ["background-color:#ff9999" if "BAJA" in str(v) else "background-color:#ffff99" if "VARIABLE" in str(v) else "background-color:#ffcc99" if "NO INCORPORADO" in str(v) else "background-color:#ccffcc" if "ACTIVO" in str(v) else "" for v in x], axis=1), use_container_width=True)
