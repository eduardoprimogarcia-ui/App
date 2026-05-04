import streamlit as st
import pandas as pd
from datetime import date, timedelta
import holidays
import os
from fpdf import FPDF

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
# GENERADOR DE PDF
# =========================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'REPORTE SEMANAL DE ASISTENCIA', 0, 1, 'C')
        self.ln(5)

def generar_pdf_semanal(df_semana, curso_nombre, inicio_semana):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Curso: {curso_nombre}", 0, 1)
    pdf.cell(0, 10, f"Semana: {inicio_semana}", 0, 1)
    pdf.ln(5)
    # Tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(80, 10, 'Alumno', 1, 0, 'C', True)
    pdf.cell(40, 10, 'DNI', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Asistencias', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Faltas', 1, 1, 'C', True)
    pdf.set_font('Arial', '', 10)
    for _, f in df_semana.iterrows():
        pdf.cell(80, 10, str(f['Alumno']), 1)
        pdf.cell(40, 10, str(f['DNI']), 1, 0, 'C')
        pdf.cell(35, 10, str(f['Pres.']), 1, 0, 'C')
        pdf.cell(35, 10, str(f['Faltas']), 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

# =========================
# INTERFAZ Y NAVEGACIÓN
# =========================
st.sidebar.title("🚀 ERP Formación")
menu = ["👥 Alumnos", "📚 Cursos", "📝 Matriculación", "🗑️ Eliminar Datos", "🖊️ Pasar Lista", "📊 Reporte", "📄 PDF Semanal"]
choice = st.sidebar.radio("Menú", menu)

df_alumnos = st.session_state.df_alumnos
df_cursos = st.session_state.df_cursos
df_matriculas = st.session_state.df_matriculas
df_asistencia = st.session_state.df_asistencia

# 1. ALUMNOS
if "Alumnos" in choice:
    st.header("👥 Gestión de Alumnos")
    with st.form("f_alumnos", clear_on_submit=True):
        dni = st.text_input("DNI")
        nom = st.text_input("Nombre")
        if st.form_submit_button("Añadir"):
            if dni and nom:
                st.session_state.df_alumnos = pd.concat([df_alumnos, pd.DataFrame([[dni, nom]], columns=["DNI", "Nombre"])], ignore_index=True)
                guardar_datos(st.session_state.df_alumnos, "alumnos.csv")
                st.rerun()
    st.dataframe(df_alumnos, use_container_width=True)

# 2. CURSOS
elif "Cursos" in choice:
    st.header("📚 Gestión de Cursos")
    with st.form("f_cursos"):
        n_c = st.text_input("Nombre del Curso")
        c1, c2 = st.columns(2)
        ini = c1.date_input("Inicio")
        fin = c2.date_input("Fin", date.today() + timedelta(days=30))
        reg = st.selectbox("Región Festivos", ['MD','CL','CT','AN','VC','PV','GA','RI'], index=1)
        if st.form_submit_button("Crear Curso") and n_c:
            st.session_state.df_cursos = pd.concat([df_cursos, pd.DataFrame([[n_c, ini, fin, reg]], columns=["Nombre", "Inicio", "Fin", "Región"])], ignore_index=True)
            guardar_datos(st.session_state.df_cursos, "cursos.csv")
            st.rerun()
    st.dataframe(df_cursos, use_container_width=True)

# 3. MATRICULACIÓN
elif "Matriculación" in choice:
    st.header("📝 Matricular Alumnos")
    if df_alumnos.empty or df_cursos.empty: st.warning("Crea alumnos y cursos primero")
    else:
        with st.form("f_mat"):
            c_m = st.selectbox("Curso", df_cursos["Nombre"])
            a_m = st.selectbox("Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            d_m = a_m.split("(")[1].replace(")", "")
            if st.form_submit_button("Matricular"):
                if df_matriculas[(df_matriculas["Curso"] == c_m) & (df_matriculas["DNI"] == d_m)].empty:
                    st.session_state.df_matriculas = pd.concat([df_matriculas, pd.DataFrame([[c_m, d_m]], columns=["Curso", "DNI"])], ignore_index=True)
                    guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
                    st.success("Matriculado con éxito")
                    st.rerun()

# 4. ELIMINAR DATOS
elif "Eliminar Datos" in choice:
    st.header("🗑️ Zona de Borrado")
    op = st.selectbox("Acción", ["Asistencia de un Alumno", "Un Alumno", "Un Curso", "TODA la Asistencia"])
    conf = st.checkbox("Confirmo el borrado permanente")
    
    if op == "Asistencia de un Alumno" and not df_matriculas.empty:
        c_b = st.selectbox("Curso", df_cursos["Nombre"])
        dnis_c = df_matriculas[df_matriculas["Curso"] == c_b]["DNI"]
        alus_c = df_alumnos[df_alumnos["DNI"].isin(dnis_c)]
        if not alus_c.empty:
            a_b = st.selectbox("Alumno", alus_c["Nombre"] + " (" + alus_c["DNI"] + ")")
            dni_b = a_b.split("(")[1].replace(")", "")
            if st.button("Limpiar historial de este alumno") and conf:
                st.session_state.df_asistencia = df_asistencia[~((df_asistencia["DNI"] == dni_b) & (df_asistencia["Curso"] == c_b))]
                guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
                st.rerun()

    elif op == "TODA la Asistencia" and st.button("Borrar todo") and conf:
        st.session_state.df_asistencia = pd.DataFrame(columns=["Fecha", "Curso", "DNI", "Estado"])
        guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
        st.rerun()

# 5. PASAR LISTA
elif "Pasar Lista" in choice:
    st.header("🖊️ Pasar Lista")
    if not df_matriculas.empty:
        c_l = st.selectbox("Selecciona Curso", df_cursos["Nombre"])
        d_c = df_cursos[df_cursos["Nombre"] == c_l].iloc[0]
        lec = obtener_calendario_curso(pd.to_datetime(d_c["Inicio"]).date(), pd.to_datetime(d_c["Fin"]).date(), d_c["Región"])
        f_l = st.selectbox("Fecha Lectiva", lec)
        
        d_m = df_matriculas[df_matriculas["Curso"] == c_l]["DNI"]
        a_m = df_alumnos[df_alumnos["DNI"].isin(d_m)]
        
        with st.form("f_lista"):
            res = {}
            for _, r in a_m.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{r['Nombre']}**")
                res[r["DNI"]] = c2.radio("Estado", ["Presente", "Ausente"], key=r["DNI"], horizontal=True)
            if st.form_submit_button("Guardar Asistencia"):
                # Limpiar registro previo del mismo día/curso
                st.session_state.df_asistencia = df_asistencia[~((df_asistencia["Fecha"] == str(f_l)) & (df_asistencia["Curso"] == c_l))]
                for d, e in res.items():
                    st.session_state.df_asistencia = pd.concat([st.session_state.df_asistencia, pd.DataFrame([[str(f_l), c_l, d, e]], columns=["Fecha", "Curso", "DNI", "Estado"])])
                guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
                st.success("Guardado")

# 6. REPORTE GENERAL
elif "Reporte" in choice:
    st.header("📊 Reporte de Asistencia Acumulado")
    if not df_asistencia.empty:
        c_r = st.selectbox("Ver reporte de:", df_cursos["Nombre"])
        d_r = df_cursos[df_cursos["Nombre"] == c_r].iloc[0]
        lec_r = obtener_calendario_curso(pd.to_datetime(d_r["Inicio"]).date(), pd.to_datetime(d_r["Fin"]).date(), d_r["Región"])
        total_d = len(lec_r)
        
        d_mat = df_matriculas[df_matriculas["Curso"] == c_r]["DNI"]
        datos_tabla = []
        for d in d_mat:
            nom_a = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
            asist = df_asistencia[(df_asistencia["Curso"] == c_r) & (df_asistencia["DNI"] == d)]
            p, f = len(asist[asist["Estado"]=="Presente"]), len(asist[asist["Estado"]=="Ausente"])
            pct = (f/total_d*100) if total_d > 0 else 0
            if p == 0 and (p+f)>0: est = "🚫 NO INCORPORADO"
            elif pct >= 80: est = "❌ BAJA"
            elif pct >= 25: est = "⚠️ VARIABLE"
            else: est = "✅ ACTIVO"
            datos_tabla.append([nom_a, d, p, f, f"{pct:.1f}%", est])
        
        df_f = pd.DataFrame(datos_tabla, columns=["Alumno", "DNI", "Pres.", "Faltas", "%", "Estado"])
        st.dataframe(df_f.style.apply(lambda x: ["background-color:#ff9999" if "BAJA" in str(v) else "background-color:#ffff99" if "VARIABLE" in str(v) else "background-color:#ffcc99" if "NO INCORPORADO" in str(v) else "background-color:#ccffcc" if "ACTIVO" in str(v) else "" for v in x], axis=1), use_container_width=True)

# 7. PDF SEMANAL
elif "PDF" in choice:
    st.header("📄 Generar Reporte Semanal (PDF)")
    if df_asistencia.empty: st.info("Sin datos")
    else:
        c_pdf = st.selectbox("Curso", df_cursos["Nombre"])
        f_ref = st.date_input("Día de la semana")
        lun = f_ref - timedelta(days=f_ref.weekday())
        dom = lun + timedelta(days=6)
        
        as_sem = df_asistencia[(df_asistencia["Curso"] == c_pdf) & (pd.to_datetime(df_asistencia["Fecha"]).dt.date >= lun) & (pd.to_datetime(df_asistencia["Fecha"]).dt.date <= dom)]
        
        if not as_sem.empty:
            d_mat = df_matriculas[df_matriculas["Curso"] == c_pdf]["DNI"]
            res_pdf = []
            for d in d_mat:
                n = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
                dat = as_sem[as_sem["DNI"] == d]
                res_pdf.append({"Alumno": n, "DNI": d, "Pres.": len(dat[dat["Estado"]=="Presente"]), "Faltas": len(dat[dat["Estado"]=="Ausente"])})
            
            df_p = pd.DataFrame(res_pdf)
            st.table(df_p)
            pdf_b = generar_pdf_semanal(df_p, c_pdf, f"{lun} a {dom}")
            st.download_button("Descargar PDF", data=pdf_b, file_name="semanal.pdf", mime="application/pdf")
        else:
            st.warning("No hay registros en esta semana")
