import streamlit as st
import pandas as pd
from datetime import date, timedelta
import holidays
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# =========================================================
# 1. CONFIGURACIÓN Y CONEXIÓN A GOOGLE SHEETS
# =========================================================
st.set_page_config(page_title="ERP Formación 2026", layout="wide", page_icon="🎓")

def cargar_datos(pestaña, columnas):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=pestaña, ttl=0)
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=columnas)
        return df
    except:
        return pd.DataFrame(columns=columnas)

def guardar_datos(df, pestaña):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=pestaña, data=df)

def inicializar_estado():
    if 'df_alumnos' not in st.session_state:
        st.session_state.df_alumnos = cargar_datos("alumnos", ["DNI", "Nombre"])
    if 'df_cursos' not in st.session_state:
        st.session_state.df_cursos = cargar_datos("cursos", ["Nombre", "Inicio", "Fin", "Región"])
    if 'df_matriculas' not in st.session_state:
        st.session_state.df_matriculas = cargar_datos("matriculas", ["Curso", "DNI"])
    if 'df_asistencia' not in st.session_state:
        st.session_state.df_asistencia = cargar_datos("asistencia", ["Fecha", "Curso", "DNI", "Estado"])

inicializar_estado()

# =========================================================
# 2. FUNCIONES AUXILIARES (CALENDARIO Y PDF)
# =========================================================
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

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'REPORTE SEMANAL DE ASISTENCIA', 0, 1, 'C')
        self.ln(5)

def generar_pdf_semanal(df_semana, curso_nombre, periodo):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Curso: {curso_nombre}", 0, 1)
    pdf.cell(0, 10, f"Semana: {periodo}", 0, 1)
    pdf.ln(5)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(80, 10, 'Alumno', 1, 0, 'C', True)
    pdf.cell(40, 10, 'DNI', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Pres.', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Faltas', 1, 1, 'C', True)
    pdf.set_font('Arial', '', 10)
    for _, f in df_semana.iterrows():
        pdf.cell(80, 10, str(f['Alumno']), 1)
        pdf.cell(40, 10, str(f['DNI']), 1, 0, 'C')
        pdf.cell(35, 10, str(f['Pres.']), 1, 0, 'C')
        pdf.cell(35, 10, str(f['Faltas']), 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 3. INTERFAZ Y NAVEGACIÓN
# =========================================================
st.sidebar.title("🚀 ERP Formación Cloud")
menu = ["👥 Alumnos", "📚 Cursos", "📝 Matriculación", "🖊️ Pasar Lista", "📊 Reporte", "📄 PDF Semanal", "🗑️ Eliminar Datos"]
choice = st.sidebar.radio("Menú", menu)

# Referencias locales para simplificar
df_alumnos = st.session_state.df_alumnos
df_cursos = st.session_state.df_cursos
df_matriculas = st.session_state.df_matriculas
df_asistencia = st.session_state.df_asistencia

# --- ALUMNOS ---
if choice == "👥 Alumnos":
    st.header("👥 Gestión de Alumnos")
    with st.form("f_alu", clear_on_submit=True):
        dni = st.text_input("DNI")
        nom = st.text_input("Nombre")
        if st.form_submit_button("Añadir"):
            nuevo = pd.DataFrame([[dni, nom]], columns=["DNI", "Nombre"])
            st.session_state.df_alumnos = pd.concat([df_alumnos, nuevo], ignore_index=True)
            guardar_datos(st.session_state.df_alumnos, "alumnos")
            st.rerun()
    st.dataframe(df_alumnos, use_container_width=True)

# --- CURSOS ---
elif choice == "📚 Cursos":
    st.header("📚 Gestión de Cursos")
    with st.form("f_cur"):
        n_c = st.text_input("Nombre del Curso")
        c1, c2 = st.columns(2)
        ini = c1.date_input("Inicio")
        fin = c2.date_input("Fin")
        reg = st.selectbox("Región", ['MD','CL','CT','AN','VC','PV','GA','RI'], index=1)
        if st.form_submit_button("Crear"):
            nuevo = pd.DataFrame([[n_c, str(ini), str(fin), reg]], columns=["Nombre", "Inicio", "Fin", "Región"])
            st.session_state.df_cursos = pd.concat([df_cursos, nuevo], ignore_index=True)
            guardar_datos(st.session_state.df_cursos, "cursos")
            st.rerun()
    st.dataframe(df_cursos, use_container_width=True)

# --- MATRICULACIÓN ---
elif choice == "📝 Matriculación":
    st.header("📝 Matriculación")
    if not df_alumnos.empty and not df_cursos.empty:
        with st.form("f_mat"):
            c_sel = st.selectbox("Curso", df_cursos["Nombre"])
            a_sel = st.selectbox("Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            dni_m = a_sel.split("(")[1].replace(")", "")
            if st.form_submit_button("Matricular"):
                nuevo = pd.DataFrame([[c_sel, dni_m]], columns=["Curso", "DNI"])
                st.session_state.df_matriculas = pd.concat([df_matriculas, nuevo], ignore_index=True)
                guardar_datos(st.session_state.df_matriculas, "matriculas")
                st.success("Matriculado")
                st.rerun()

# --- PASAR LISTA ---
elif choice == "🖊️ Pasar Lista":
    st.header("🖊️ Pasar Lista")
    if not df_matriculas.empty:
        c_l = st.selectbox("Curso", df_cursos["Nombre"])
        row = df_cursos[df_cursos["Nombre"] == c_l].iloc[0]
        dias = obtener_calendario_curso(pd.to_datetime(row["Inicio"]).date(), pd.to_datetime(row["Fin"]).date(), row["Región"])
        f_l = st.selectbox("Fecha", dias)
        
        dnis = df_matriculas[df_matriculas["Curso"] == c_l]["DNI"]
        alus = df_alumnos[df_alumnos["DNI"].isin(dnis)]
        
        with st.form("f_lista"):
            res = {}
            for _, r in alus.iterrows():
                res[r["DNI"]] = st.radio(f"{r['Nombre']}", ["Presente", "Ausente"], horizontal=True)
            if st.form_submit_button("Guardar"):
                # Limpiar registros previos de ese día/curso
                st.session_state.df_asistencia = df_asistencia[~((df_asistencia["Fecha"] == str(f_l)) & (df_asistencia["Curso"] == c_l))]
                for d, e in res.items():
                    nueva_fila = pd.DataFrame([[str(f_l), c_l, d, e]], columns=["Fecha", "Curso", "DNI", "Estado"])
                    st.session_state.df_asistencia = pd.concat([st.session_state.df_asistencia, nueva_fila])
                guardar_datos(st.session_state.df_asistencia, "asistencia")
                st.success("Guardado")

# --- REPORTE ---
elif choice == "📊 Reporte":
    st.header("📊 Reporte")
    if not df_asistencia.empty:
        c_r = st.selectbox("Curso", df_cursos["Nombre"])
        row = df_cursos[df_cursos["Nombre"] == c_r].iloc[0]
        total_d = len(obtener_calendario_curso(pd.to_datetime(row["Inicio"]).date(), pd.to_datetime(row["Fin"]).date(), row["Región"]))
        
        dnis_r = df_matriculas[df_matriculas["Curso"] == c_r]["DNI"]
        data = []
        for d in dnis_r:
            nom = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
            asist = df_asistencia[(df_asistencia["Curso"] == c_r) & (df_asistencia["DNI"] == d)]
            p, f = len(asist[asist["Estado"]=="Presente"]), len(asist[asist["Estado"]=="Ausente"])
            pct = (f/total_d*100) if total_d > 0 else 0
            est = "❌ BAJA" if pct >= 80 else "⚠️ VARIABLE" if pct >= 25 else "✅ ACTIVO"
            data.append([nom, d, p, f, f"{pct:.1f}%", est])
        
        st.dataframe(pd.DataFrame(data, columns=["Alumno", "DNI", "Pres.", "Faltas", "%", "Estado"]))

# --- PDF ---
elif choice == "📄 PDF Semanal":
    st.header("📄 PDF")
    if not df_asistencia.empty:
        c_pdf = st.selectbox("Seleccione Curso", df_cursos["Nombre"])
        f_ref = st.date_input("Día de la semana")
        lun = f_ref - timedelta(days=f_ref.weekday())
        dom = lun + timedelta(days=6)
        
        as_sem = df_asistencia[(df_asistencia["Curso"] == c_pdf) & 
                               (pd.to_datetime(df_asistencia["Fecha"]).dt.date >= lun) & 
                               (pd.to_datetime(df_asistencia["Fecha"]).dt.date <= dom)]
        
        if not as_sem.empty:
            resumen = []
            for d in df_matriculas[df_matriculas["Curso"] == c_pdf]["DNI"]:
                n = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
                dat = as_sem[as_sem["DNI"] == d]
                resumen.append({"Alumno": n, "DNI": d, "Pres.": len(dat[dat["Estado"]=="Presente"]), "Faltas": len(dat[dat["Estado"]=="Ausente"])})
            
            pdf_b = generar_pdf_semanal(pd.DataFrame(resumen), c_pdf, f"{lun} a {dom}")
            st.download_button("Descargar PDF", pdf_b, "reporte.pdf", "application/pdf")

# --- ELIMINAR DATOS ---
elif choice == "🗑️ Eliminar Datos":
    st.header("🗑️ Borrado de Datos")

    st.subheader("Limpiar toda la asistencia")
    conf_asist = st.checkbox("Confirmo borrado permanente de asistencia")
    if st.button("Limpiar toda la asistencia") and conf_asist:
        st.session_state.df_asistencia = pd.DataFrame(columns=["Fecha", "Curso", "DNI", "Estado"])
        guardar_datos(st.session_state.df_asistencia, "asistencia")
        st.success("Asistencia borrada")
        st.rerun()

    st.divider()

    st.subheader("Eliminar un alumno")
    if not df_alumnos.empty:
        alu_sel = st.selectbox("Selecciona alumno a eliminar", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")", key="del_alu")
        dni_del = alu_sel.split("(")[1].replace(")", "")
        conf_alu = st.checkbox("Confirmo eliminar este alumno y todos sus datos", key="conf_alu")
        if st.button("Eliminar alumno") and conf_alu:
            st.session_state.df_alumnos = df_alumnos[df_alumnos["DNI"] != dni_del].reset_index(drop=True)
            st.session_state.df_matriculas = df_matriculas[df_matriculas["DNI"] != dni_del].reset_index(drop=True)
            st.session_state.df_asistencia = df_asistencia[df_asistencia["DNI"] != dni_del].reset_index(drop=True)
            guardar_datos(st.session_state.df_alumnos, "alumnos")
            guardar_datos(st.session_state.df_matriculas, "matriculas")
            guardar_datos(st.session_state.df_asistencia, "asistencia")
            st.success(f"Alumno {alu_sel} eliminado")
            st.rerun()
    else:
        st.info("No hay alumnos registrados")

    st.divider()

    st.subheader("Eliminar un curso")
    if not df_cursos.empty:
        curso_del = st.selectbox("Selecciona curso a eliminar", df_cursos["Nombre"], key="del_cur")
        conf_cur = st.checkbox("Confirmo eliminar este curso y todos sus datos", key="conf_cur")
        if st.button("Eliminar curso") and conf_cur:
            st.session_state.df_cursos = df_cursos[df_cursos["Nombre"] != curso_del].reset_index(drop=True)
            st.session_state.df_matriculas = df_matriculas[df_matriculas["Curso"] != curso_del].reset_index(drop=True)
            st.session_state.df_asistencia = df_asistencia[df_asistencia["Curso"] != curso_del].reset_index(drop=True)
            guardar_datos(st.session_state.df_cursos, "cursos")
            guardar_datos(st.session_state.df_matriculas, "matriculas")
            guardar_datos(st.session_state.df_asistencia, "asistencia")
            st.success(f"Curso '{curso_del}' eliminado")
            st.rerun()
    else:
        st.info("No hay cursos registrados")
