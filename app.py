import streamlit as st
import pandas as pd
from datetime import date, timedelta
import holidays
import os
from fpdf import FPDF

# =========================================================
# 1. CONFIGURACIÓN Y PERSISTENCIA DE DATOS
# =========================================================
st.set_page_config(page_title="ERP Formación 2026", layout="wide", page_icon="🎓")

def cargar_datos(archivo, columnas):
    if os.path.exists(archivo):
        try:
            return pd.read_csv(archivo)
        except:
            return pd.DataFrame(columns=columnas)
    return pd.DataFrame(columns=columnas)

def guardar_datos(df, archivo):
    df.to_csv(archivo, index=False)

def inicializar_estado():
    if 'df_alumnos' not in st.session_state:
        st.session_state.df_alumnos = cargar_datos("alumnos.csv", ["DNI", "Nombre"])
    if 'df_cursos' not in st.session_state:
        st.session_state.df_cursos = cargar_datos("cursos.csv", ["Nombre", "Inicio", "Fin", "Región"])
    if 'df_matriculas' not in st.session_state:
        st.session_state.df_matriculas = cargar_datos("matriculas.csv", ["Curso", "DNI"])
    if 'df_asistencia' not in st.session_state:
        st.session_state.df_asistencia = cargar_datos("asistencia.csv", ["Fecha", "Curso", "DNI", "Estado"])

inicializar_estado()

# =========================================================
# 2. LÓGICA DE CALENDARIO Y PDF
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
        self.cell(0, 10, 'INFORME SEMANAL DE ASISTENCIA', 0, 1, 'C')
        self.ln(5)

def generar_pdf_semanal(df_semana, curso_nombre, rango_fechas):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Curso: {curso_nombre}", 0, 1)
    pdf.cell(0, 10, f"Periodo: {rango_fechas}", 0, 1)
    pdf.ln(5)
    # Encabezados
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(80, 10, 'Alumno', 1, 0, 'C', True)
    pdf.cell(40, 10, 'DNI', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Presencias', 1, 0, 'C', True)
    pdf.cell(35, 10, 'Ausencias', 1, 1, 'C', True)
    # Contenido
    pdf.set_font('Arial', '', 10)
    for _, fila in df_semana.iterrows():
        pdf.cell(80, 10, str(fila['Alumno']), 1)
        pdf.cell(40, 10, str(fila['DNI']), 1, 0, 'C')
        pdf.cell(35, 10, str(fila['Pres.']), 1, 0, 'C')
        pdf.cell(35, 10, str(fila['Faltas']), 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

# =========================================================
# 3. INTERFAZ DE NAVEGACIÓN
# =========================================================
st.sidebar.title("🚀 Panel de Control")
menu = ["👥 Alumnos", "📚 Cursos", "📝 Matriculación", "🖊️ Pasar Lista", "📊 Reporte General", "📄 PDF Semanal", "🗑️ Eliminar Datos"]
choice = st.sidebar.radio("Ir a:", menu)

# Alias para facilitar el manejo
df_alumnos = st.session_state.df_alumnos
df_cursos = st.session_state.df_cursos
df_matriculas = st.session_state.df_matriculas
df_asistencia = st.session_state.df_asistencia

# --- SECCIÓN 1: ALUMNOS ---
if choice == "👥 Alumnos":
    st.header("👥 Gestión de Alumnos")
    with st.form("form_alumnos", clear_on_submit=True):
        dni = st.text_input("DNI del Alumno")
        nombre = st.text_input("Nombre Completo")
        if st.form_submit_button("Registrar Alumno") and dni and nombre:
            st.session_state.df_alumnos = pd.concat([df_alumnos, pd.DataFrame([[dni, nombre]], columns=["DNI", "Nombre"])], ignore_index=True)
            guardar_datos(st.session_state.df_alumnos, "alumnos.csv")
            st.success("Alumno guardado")
            st.rerun()
    st.subheader("Listado Actual")
    st.dataframe(df_alumnos, use_container_width=True)

# --- SECCIÓN 2: CURSOS ---
elif choice == "📚 Cursos":
    st.header("📚 Configuración de Cursos")
    with st.form("form_cursos"):
        n_c = st.text_input("Nombre del Curso")
        c1, c2 = st.columns(2)
        ini = c1.date_input("Fecha de Inicio")
        fin = c2.date_input("Fecha de Fin", date.today() + timedelta(days=30))
        reg = st.selectbox("Región (Festivos)", ['MD','CL','CT','AN','VC','PV','GA','RI'], index=1)
        if st.form_submit_button("Crear Curso") and n_c:
            st.session_state.df_cursos = pd.concat([df_cursos, pd.DataFrame([[n_c, ini, fin, reg]], columns=["Nombre", "Inicio", "Fin", "Región"])], ignore_index=True)
            guardar_datos(st.session_state.df_cursos, "cursos.csv")
            st.success("Curso creado")
            st.rerun()
    st.dataframe(df_cursos, use_container_width=True)

# --- SECCIÓN 3: MATRICULACIÓN ---
elif choice == "📝 Matriculación":
    st.header("📝 Matricular Alumnos en Cursos")
    if df_alumnos.empty or df_cursos.empty:
        st.info("Debe haber alumnos y cursos creados para matricular.")
    else:
        with st.form("form_mat"):
            curso_sel = st.selectbox("Seleccione Curso", df_cursos["Nombre"])
            alumno_sel = st.selectbox("Seleccione Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            dni_m = alumno_sel.split("(")[1].replace(")", "")
            if st.form_submit_button("Confirmar Matrícula"):
                if df_matriculas[(df_matriculas["Curso"] == curso_sel) & (df_matriculas["DNI"] == dni_m)].empty:
                    st.session_state.df_matriculas = pd.concat([df_matriculas, pd.DataFrame([[curso_sel, dni_m]], columns=["Curso", "DNI"])], ignore_index=True)
                    guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
                    st.success("Matriculado")
                    st.rerun()
                else:
                    st.warning("Este alumno ya está en el curso.")

# --- SECCIÓN 4: PASAR LISTA ---
elif choice == "🖊️ Pasar Lista":
    st.header("🖊️ Registro de Asistencia Diaria")
    if df_matriculas.empty:
        st.warning("No hay alumnos matriculados en ningún curso.")
    else:
        curso_l = st.selectbox("Curso", df_cursos["Nombre"])
        datos_c = df_cursos[df_cursos["Nombre"] == curso_l].iloc[0]
        dias_lectivos = obtener_calendario_curso(pd.to_datetime(datos_c["Inicio"]).date(), pd.to_datetime(datos_c["Fin"]).date(), datos_c["Región"])
        fecha_l = st.selectbox("Día de Clase", dias_lectivos)
        
        dnis_en_curso = df_matriculas[df_matriculas["Curso"] == curso_l]["DNI"]
        alumnos_en_curso = df_alumnos[df_alumnos["DNI"].isin(dnis_en_curso)]
        
        with st.form("form_lista"):
            estados = {}
            for _, al in alumnos_en_curso.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{al['Nombre']}** ({al['DNI']})")
                estados[al["DNI"]] = c2.radio("Asistencia", ["Presente", "Ausente"], key=al["DNI"], horizontal=True)
            
            if st.form_submit_button("Guardar Lista de Hoy"):
                # Limpiar si ya se pasó lista este día
                st.session_state.df_asistencia = df_asistencia[~((df_asistencia["Fecha"] == str(fecha_l)) & (df_asistencia["Curso"] == curso_l))]
                for d, e in estados.items():
                    st.session_state.df_asistencia = pd.concat([st.session_state.df_asistencia, pd.DataFrame([[str(fecha_l), curso_l, d, e]], columns=["Fecha", "Curso", "DNI", "Estado"])])
                guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
                st.success("Asistencia registrada correctamente")

# --- SECCIÓN 5: REPORTE GENERAL ---
elif choice == "📊 Reporte General":
    st.header("📊 Situación Acumulada del Curso")
    if not df_asistencia.empty:
        c_r = st.selectbox("Seleccione Curso para ver Informe", df_cursos["Nombre"])
        d_r = df_cursos[df_cursos["Nombre"] == c_r].iloc[0]
        total_dias = len(obtener_calendario_curso(pd.to_datetime(d_r["Inicio"]).date(), pd.to_datetime(d_r["Fin"]).date(), d_r["Región"]))
        
        dnis_r = df_matriculas[df_matriculas["Curso"] == c_r]["DNI"]
        tabla = []
        for d in dnis_r:
            nom = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
            asist_alu = df_asistencia[(df_asistencia["Curso"] == c_r) & (df_asistencia["DNI"] == d)]
            p, f = len(asist_alu[asist_alu["Estado"]=="Presente"]), len(asist_alu[asist_alu["Estado"]=="Ausente"])
            pct = (f / total_dias * 100) if total_dias > 0 else 0
            
            if p == 0 and (p+f) > 0: est = "🚫 NO INCORPORADO"
            elif pct >= 80: est = "❌ BAJA"
            elif pct >= 25: est = "⚠️ VARIABLE"
            else: est = "✅ ACTIVO"
            
            tabla.append([nom, d, p, f, f"{pct:.1f}%", est])
        
        df_final = pd.DataFrame(tabla, columns=["Alumno", "DNI", "Pres.", "Faltas", "% Faltas", "Estado"])
        st.dataframe(df_final.style.apply(lambda x: ["background-color:#ff9999" if "BAJA" in str(v) else "background-color:#ffff99" if "VARIABLE" in str(v) else "background-color:#ffcc99" if "NO INCORPORADO" in str(v) else "background-color:#ccffcc" if "ACTIVO" in str(v) else "" for v in x], axis=1), use_container_width=True)

# --- SECCIÓN 6: PDF SEMANAL ---
elif choice == "📄 PDF Semanal":
    st.header("📄 Generar Informe Semanal para Dirección")
    if df_asistencia.empty:
        st.info("No hay datos registrados")
    else:
        c_pdf = st.selectbox("Curso a exportar", df_cursos["Nombre"])
        f_ref = st.date_input("Elija un día de la semana")
        lunes = f_ref - timedelta(days=f_ref.weekday())
        domingo = lunes + timedelta(days=6)
        
        asist_sem = df_asistencia[(df_asistencia["Curso"] == c_pdf) & 
                                 (pd.to_datetime(df_asistencia["Fecha"]).dt.date >= lunes) & 
                                 (pd.to_datetime(df_asistencia["Fecha"]).dt.date <= domingo)]
        
        if not asist_sem.empty:
            resumen = []
            for d in df_matriculas[df_matriculas["Curso"] == c_pdf]["DNI"]:
                n = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
                dat = asist_sem[asist_sem["DNI"] == d]
                resumen.append({"Alumno": n, "DNI": d, "Pres.": len(dat[dat["Estado"]=="Presente"]), "Faltas": len(dat[dat["Estado"]=="Ausente"])})
            
            df_p = pd.DataFrame(resumen)
            st.table(df_p)
            pdf_bytes = generar_pdf_semanal(df_p, c_pdf, f"{lunes} al {domingo}")
            st.download_button("📥 Descargar Reporte PDF", data=pdf_bytes, file_name=f"Asistencia_{c_pdf}_{lunes}.pdf", mime="application/pdf")
        else:
            st.warning("No hay datos de asistencia para esa semana.")

# --- SECCIÓN 7: ELIMINAR DATOS ---
elif choice == "🗑️ Eliminar Datos":
    st.header("🗑️ Gestión de Borrado")
    opcion_borrar = st.selectbox("¿Qué desea eliminar?", ["Asistencia de un Alumno", "Un Alumno", "Un Curso", "TODA la Asistencia"])
    confirmar = st.checkbox("Entiendo que esta acción no se puede deshacer")

    if opcion_borrar == "Asistencia de un Alumno":
        c_sel = st.selectbox("Del Curso", df_cursos["Nombre"])
        dnis_en_c = df_matriculas[df_matriculas["Curso"] == c_sel]["DNI"]
        alus_en_c = df_alumnos[df_alumnos["DNI"].isin(dnis_en_c)]
        if not alus_en_c.empty:
            a_sel = st.selectbox("Alumno", alus_en_c["Nombre"] + " (" + alus_en_c["DNI"] + ")")
            dni_limpiar = a_sel.split("(")[1].replace(")", "")
            if st.button("Limpiar Asistencia") and confirmar:
                st.session_state.df_asistencia = df_asistencia[~((df_asistencia["DNI"] == dni_limpiar) & (df_asistencia["Curso"] == c_sel))]
                guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
                st.success("Historial del alumno limpiado")
                st.rerun()

    elif opcion_borrar == "TODA la Asistencia":
        if st.button("🔥 BORRAR TODO EL HISTORIAL") and confirmar:
            st.session_state.df_asistencia = pd.DataFrame(columns=["Fecha", "Curso", "DNI", "Estado"])
            guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
            st.success("Base de datos de asistencia vaciada")
            st.rerun()

    elif opcion_borrar == "Un Alumno":
        a_b = st.selectbox("Seleccione Alumno a eliminar del sistema", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
        dni_b = a_b.split("(")[1].replace(")", "")
        if st.button("Borrar Alumno") and confirmar:
            st.session_state.df_alumnos = df_alumnos[df_alumnos["DNI"] != dni_b]
            st.session_state.df_matriculas = df_matriculas[df_matriculas["DNI"] != dni_b]
            st.session_state.df_asistencia = df_asistencia[df_asistencia["DNI"] != dni_b]
            guardar_datos(st.session_state.df_alumnos, "alumnos.csv")
            guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
            guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
            st.rerun()

    elif opcion_borrar == "Un Curso":
        c_b = st.selectbox("Seleccione Curso a eliminar", df_cursos["Nombre"])
        if st.button("Borrar Curso") and confirmar:
            st.session_state.df_cursos = df_cursos[df_cursos["Nombre"] != c_b]
            st.session_state.df_matriculas = df_matriculas[df_matriculas["Curso"] != c_b]
            st.session_state.df_asistencia = df_asistencia[df_asistencia["Curso"] != c_b]
            guardar_datos(st.session_state.df_cursos, "cursos.csv")
            guardar_datos(st.session_state.df_matriculas, "matriculas.csv")
            guardar_datos(st.session_state.df_asistencia, "asistencia.csv")
            st.rerun()
