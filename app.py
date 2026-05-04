import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
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
        self.set_font('Arial', '', 10)
        self.cell(0, 10, f'Generado el: {date.today().strftime("%d/%m/%Y")}', 0, 1, 'R')
        self.ln(5)

def generar_pdf_semanal(df_semana, curso_nombre, inicio_semana):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Curso: {curso_nombre}", 0, 1)
    pdf.cell(0, 10, f"Semana del {inicio_semana.strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)

    # Cabecera tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(80, 10, 'Alumno', 1, 0, 'C', True)
    pdf.cell(40, 10, 'DNI', 1, 0, 'C', True)
    pdf.cell(30, 10, 'Presencias', 1, 0, 'C', True)
    pdf.cell(30, 10, 'Ausencias', 1, 1, 'C', True)

    # Datos
    pdf.set_font('Arial', '', 10)
    for _, fila in df_semana.iterrows():
        pdf.cell(80, 10, str(fila['Alumno']), 1)
        pdf.cell(40, 10, str(fila['DNI']), 1, 0, 'C')
        pdf.cell(30, 10, str(fila['Pres.']), 1, 0, 'C')
        pdf.cell(30, 10, str(fila['Faltas']), 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# =========================
# INTERFAZ
# =========================
st.sidebar.title("🚀 ERP Formación")
menu = ["👥 Alumnos", "📚 Cursos", "📝 Matriculación", "🗑️ Eliminar Datos", "🖊️ Pasar Lista", "📊 Reporte", "📄 Exportar PDF"]
choice = st.sidebar.radio("Menú", menu)

df_alumnos = st.session_state.df_alumnos
df_cursos = st.session_state.df_cursos
df_matriculas = st.session_state.df_matriculas
df_asistencia = st.session_state.df_asistencia

# [Secciones 1 a 6 se mantienen igual que tu versión anterior...]

# =========================
# 7. EXPORTAR PDF (NUEVO)
# =========================
if "PDF" in choice:
    st.header("📄 Generar Informe Semanal en PDF")
    
    if df_asistencia.empty:
        st.warning("No hay datos de asistencia para exportar.")
    else:
        curso_pdf = st.selectbox("Selecciona Curso", df_cursos["Nombre"])
        
        # Elegir lunes de la semana que queremos reportar
        fecha_ref = st.date_input("Selecciona un día de la semana a reportar", date.today())
        lunes = fecha_ref - timedelta(days=fecha_ref.weekday())
        domingo = lunes + timedelta(days=6)
        
        st.info(f"Reportando del lunes {lunes.strftime('%d/%m')} al domingo {domingo.strftime('%d/%m')}")
        
        # Filtrar asistencia de esa semana y curso
        df_asistencia['Fecha_DT'] = pd.to_datetime(df_asistencia['Fecha']).dt.date
        asist_semana = df_asistencia[
            (df_asistencia["Curso"] == curso_pdf) & 
            (df_asistencia["Fecha_DT"] >= lunes) & 
            (df_asistencia["Fecha_DT"] <= domingo)
        ]
        
        if asist_semana.empty:
            st.error("No se encontraron registros de asistencia en esa semana para este curso.")
        else:
            # Procesar datos para el PDF
            dnis_r = df_matriculas[df_matriculas["Curso"] == curso_pdf]["DNI"]
            resumen_semanal = []
            for d in dnis_r:
                n = df_alumnos[df_alumnos["DNI"] == d]["Nombre"].iloc[0]
                datos_a = asist_semana[asist_semana["DNI"] == d]
                p = len(datos_a[datos_a["Estado"] == "Presente"])
                f = len(datos_a[datos_a["Estado"] == "Ausente"])
                resumen_semanal.append({"Alumno": n, "DNI": d, "Pres.": p, "Faltas": f})
            
            df_pdf = pd.DataFrame(resumen_semanal)
            st.table(df_pdf)
            
            pdf_bytes = generar_pdf_semanal(df_pdf, curso_pdf, lunes)
            
            st.download_button(
                label="📥 Descargar Reporte Semanal PDF",
                data=pdf_bytes,
                file_name=f"Reporte_{curso_pdf}_{lunes}.pdf",
                mime="application/pdf"
            )

# [Mantenemos el resto del código de Pasar Lista y Reporte General...]
