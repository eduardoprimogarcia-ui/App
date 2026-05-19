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
        st.session_state.df_alumnos = cargar_datos("alumnos", [
            "DNI", "Nombre", "Dirección", "CP", "Población", "Provincia", "Teléfono", "Email"
        ])
    if 'df_cursos' not in st.session_state:
        st.session_state.df_cursos = cargar_datos("cursos", [
            "Plan Formativo", "Código", "Nombre", "Horas", "Inicio", "Fin", "Horario", "Región"
        ])
    if 'df_matriculas' not in st.session_state:
        st.session_state.df_matriculas = cargar_datos("matriculas", ["Curso", "DNI"])
    if 'df_asistencia' not in st.session_state:
        st.session_state.df_asistencia = cargar_datos("asistencia", ["Fecha", "Curso", "DNI", "Estado"])

inicializar_estado()

# =========================================================
# 2. FUNCIONES AUXILIARES
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

def calcular_horas_limite(horas_totales):
    h25 = round(horas_totales * 0.25, 1)
    h75 = round(horas_totales * 0.75, 1)
    return h25, h75

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
menu = [
    "👥 Alumnos", "📚 Cursos", "📝 Matriculación",
    "🖊️ Pasar Lista", "📊 Reporte", "📄 PDF Semanal",
    "🔍 Búsqueda", "🗑️ Eliminar Datos"
]
choice = st.sidebar.radio("Menú", menu)

df_alumnos   = st.session_state.df_alumnos
df_cursos    = st.session_state.df_cursos
df_matriculas = st.session_state.df_matriculas
df_asistencia = st.session_state.df_asistencia

# --- ALUMNOS ---
if choice == "👥 Alumnos":
    st.header("👥 Gestión de Alumnos")
    with st.form("f_alu", clear_on_submit=True):
        c1, c2 = st.columns(2)
        dni  = c1.text_input("DNI")
        nom  = c2.text_input("Nombre y Apellidos")
        dir_ = st.text_input("Dirección")
        c3, c4, c5 = st.columns(3)
        cp   = c3.text_input("CP")
        pob  = c4.text_input("Población")
        prov = c5.text_input("Provincia")
        c6, c7 = st.columns(2)
        tel  = c6.text_input("Teléfono")
        email = c7.text_input("Email")
        if st.form_submit_button("Añadir alumno"):
            nuevo = pd.DataFrame([[dni, nom, dir_, cp, pob, prov, tel, email]],
                                 columns=["DNI", "Nombre", "Dirección", "CP", "Población", "Provincia", "Teléfono", "Email"])
            st.session_state.df_alumnos = pd.concat([df_alumnos, nuevo], ignore_index=True)
            guardar_datos(st.session_state.df_alumnos, "alumnos")
            st.success("Alumno añadido")
            st.rerun()
    st.dataframe(df_alumnos, use_container_width=True)

# --- CURSOS ---
elif choice == "📚 Cursos":
    st.header("📚 Gestión de Cursos")
    with st.form("f_cur"):
        c1, c2 = st.columns(2)
        plan  = c1.text_input("Plan Formativo")
        codigo = c2.text_input("Código Acción Formativa")
        nombre = st.text_input("Nombre del Curso")
        c3, c4 = st.columns(2)
        horas  = c3.number_input("Horas totales", min_value=1, value=40)
        horario = c4.text_input("Horario (ej: 09:00-14:00)")
        c5, c6 = st.columns(2)
        ini = c5.date_input("Fecha Inicio")
        fin = c6.date_input("Fecha Fin")
        reg = st.selectbox("Región", ['MD','CL','CT','AN','VC','PV','GA','RI'], index=1)
        if st.form_submit_button("Crear curso"):
            h25, h75 = calcular_horas_limite(horas)
            nuevo = pd.DataFrame([[plan, codigo, nombre, horas, str(ini), str(fin), horario, reg]],
                                 columns=["Plan Formativo", "Código", "Nombre", "Horas", "Inicio", "Fin", "Horario", "Región"])
            st.session_state.df_cursos = pd.concat([df_cursos, nuevo], ignore_index=True)
            guardar_datos(st.session_state.df_cursos, "cursos")
            st.success(f"Curso creado — 25%: {h25}h | 75%: {h75}h")
            st.rerun()
    if not df_cursos.empty:
        st.dataframe(df_cursos, use_container_width=True)
        # Mostrar límites de horas por curso
        st.subheader("Límites de horas por curso")
        for _, row in df_cursos.iterrows():
            try:
                h = float(row["Horas"])
                h25, h75 = calcular_horas_limite(h)
                st.caption(f"**{row['Nombre']}** → Mínimo 25%: {h25}h | Máximo faltas 75%: {h75}h")
            except:
                pass

# --- MATRICULACIÓN ---
elif choice == "📝 Matriculación":
    st.header("📝 Matriculación")
    if not df_alumnos.empty and not df_cursos.empty:
        with st.form("f_mat"):
            c_sel = st.selectbox("Curso", df_cursos["Nombre"])
            a_sel = st.selectbox("Alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")")
            dni_m = a_sel.split("(")[1].replace(")", "")
            if st.form_submit_button("Matricular"):
                # Evitar duplicados
                ya = df_matriculas[(df_matriculas["Curso"] == c_sel) & (df_matriculas["DNI"] == dni_m)]
                if not ya.empty:
                    st.warning("Este alumno ya está matriculado en ese curso")
                else:
                    nuevo = pd.DataFrame([[c_sel, dni_m]], columns=["Curso", "DNI"])
                    st.session_state.df_matriculas = pd.concat([df_matriculas, nuevo], ignore_index=True)
                    guardar_datos(st.session_state.df_matriculas, "matriculas")
                    st.success("Matriculado correctamente")
                    st.rerun()
    else:
        st.info("Necesitas tener alumnos y cursos registrados primero")

# --- PASAR LISTA ---
elif choice == "🖊️ Pasar Lista":
    st.header("🖊️ Pasar Lista")
    if not df_matriculas.empty:
        c_l = st.selectbox("Curso", df_cursos["Nombre"])
        row = df_cursos[df_cursos["Nombre"] == c_l].iloc[0]
        dias = obtener_calendario_curso(
            pd.to_datetime(row["Inicio"]).date(),
            pd.to_datetime(row["Fin"]).date(),
            row["Región"]
        )
        f_l = st.selectbox("Fecha", dias)

        dnis = df_matriculas[df_matriculas["Curso"] == c_l]["DNI"]
        alus = df_alumnos[df_alumnos["DNI"].isin(dnis)]

        with st.form("f_lista"):
            res = {}
            for _, r in alus.iterrows():
                res[r["DNI"]] = st.radio(f"{r['Nombre']}", ["Presente", "Ausente"], horizontal=True)
            if st.form_submit_button("Guardar lista"):
                st.session_state.df_asistencia = df_asistencia[
                    ~((df_asistencia["Fecha"] == str(f_l)) & (df_asistencia["Curso"] == c_l))
                ]
                for d, e in res.items():
                    nueva_fila = pd.DataFrame([[str(f_l), c_l, d, e]], columns=["Fecha", "Curso", "DNI", "Estado"])
                    st.session_state.df_asistencia = pd.concat([st.session_state.df_asistencia, nueva_fila])
                guardar_datos(st.session_state.df_asistencia, "asistencia")
                st.success("Lista guardada correctamente")
    else:
        st.info("No hay matrículas registradas")

# --- REPORTE ---
elif choice == "📊 Reporte":
    st.header("📊 Reporte de Asistencia")
    if not df_asistencia.empty and not df_cursos.empty:
        c_r = st.selectbox("Curso", df_cursos["Nombre"])
        row = df_cursos[df_cursos["Nombre"] == c_r].iloc[0]
        total_d = len(obtener_calendario_curso(
            pd.to_datetime(row["Inicio"]).date(),
            pd.to_datetime(row["Fin"]).date(),
            row["Región"]
        ))
        try:
            horas_tot = float(row["Horas"])
            h25, h75 = calcular_horas_limite(horas_tot)
            st.info(f"Total días lectivos: {total_d} | Horas totales: {horas_tot}h | Mínimo asistencia (25%): {h25}h | Límite faltas (75%): {h75}h")
        except:
            pass

        dnis_r = df_matriculas[df_matriculas["Curso"] == c_r]["DNI"]
        data = []
        for d in dnis_r:
            fila_alu = df_alumnos[df_alumnos["DNI"] == d]
            if fila_alu.empty:
                continue
            nom = fila_alu["Nombre"].iloc[0]
            asist = df_asistencia[(df_asistencia["Curso"] == c_r) & (df_asistencia["DNI"] == d)]
            p = len(asist[asist["Estado"] == "Presente"])
            f = len(asist[asist["Estado"] == "Ausente"])
            pct = (f / total_d * 100) if total_d > 0 else 0
            est = "❌ BAJA" if pct >= 75 else "⚠️ RIESGO" if pct >= 25 else "✅ ACTIVO"
            data.append([nom, d, p, f, f"{pct:.1f}%", est])

        if data:
            st.dataframe(pd.DataFrame(data, columns=["Alumno", "DNI", "Pres.", "Faltas", "% Faltas", "Estado"]))
    else:
        st.info("No hay datos de asistencia aún")

# --- PDF ---
elif choice == "📄 PDF Semanal":
    st.header("📄 PDF Semanal")
    if not df_asistencia.empty:
        c_pdf = st.selectbox("Seleccione Curso", df_cursos["Nombre"])
        f_ref = st.date_input("Día de la semana")
        lun = f_ref - timedelta(days=f_ref.weekday())
        dom = lun + timedelta(days=6)

        as_sem = df_asistencia[
            (df_asistencia["Curso"] == c_pdf) &
            (pd.to_datetime(df_asistencia["Fecha"]).dt.date >= lun) &
            (pd.to_datetime(df_asistencia["Fecha"]).dt.date <= dom)
        ]

        if not as_sem.empty:
            resumen = []
            for d in df_matriculas[df_matriculas["Curso"] == c_pdf]["DNI"]:
                fila = df_alumnos[df_alumnos["DNI"] == d]
                if fila.empty:
                    continue
                n = fila["Nombre"].iloc[0]
                dat = as_sem[as_sem["DNI"] == d]
                resumen.append({
                    "Alumno": n, "DNI": d,
                    "Pres.": len(dat[dat["Estado"] == "Presente"]),
                    "Faltas": len(dat[dat["Estado"] == "Ausente"])
                })
            if resumen:
                pdf_b = generar_pdf_semanal(pd.DataFrame(resumen), c_pdf, f"{lun} a {dom}")
                st.download_button("Descargar PDF", pdf_b, "reporte.pdf", "application/pdf")
        else:
            st.info("No hay asistencia registrada para esa semana")
    else:
        st.info("No hay datos de asistencia aún")

# --- BÚSQUEDA ---
elif choice == "🔍 Búsqueda":
    st.header("🔍 Búsqueda")
    tipo = st.radio("Buscar por", ["Alumno", "Curso"], horizontal=True)

    if tipo == "Alumno" and not df_alumnos.empty:
        busq = st.text_input("Nombre, DNI o email del alumno")
        if busq:
            mask = (
                df_alumnos["Nombre"].str.contains(busq, case=False, na=False) |
                df_alumnos["DNI"].str.contains(busq, case=False, na=False) |
                df_alumnos["Email"].str.contains(busq, case=False, na=False)
            )
            resultados = df_alumnos[mask]
            if not resultados.empty:
                for _, alu in resultados.iterrows():
                    with st.expander(f"👤 {alu['Nombre']} — {alu['DNI']}"):
                        c1, c2 = st.columns(2)
                        c1.write(f"**Dirección:** {alu.get('Dirección','')}")
                        c1.write(f"**CP:** {alu.get('CP','')} — **Población:** {alu.get('Población','')}")
                        c1.write(f"**Provincia:** {alu.get('Provincia','')}")
                        c2.write(f"**Teléfono:** {alu.get('Teléfono','')}")
                        c2.write(f"**Email:** {alu.get('Email','')}")
                        # Cursos matriculados
                        cursos_alu = df_matriculas[df_matriculas["DNI"] == alu["DNI"]]["Curso"].tolist()
                        if cursos_alu:
                            st.write("**Cursos matriculados:**")
                            for c in cursos_alu:
                                asist = df_asistencia[(df_asistencia["DNI"] == alu["DNI"]) & (df_asistencia["Curso"] == c)]
                                p = len(asist[asist["Estado"] == "Presente"])
                                f = len(asist[asist["Estado"] == "Ausente"])
                                st.caption(f"• {c} → Presencias: {p} | Faltas: {f}")
                        else:
                            st.write("Sin matrículas registradas")
            else:
                st.info("No se encontraron alumnos")

    elif tipo == "Curso" and not df_cursos.empty:
        busq = st.text_input("Nombre o código del curso")
        if busq:
            mask = (
                df_cursos["Nombre"].str.contains(busq, case=False, na=False) |
                df_cursos["Código"].str.contains(busq, case=False, na=False) |
                df_cursos["Plan Formativo"].str.contains(busq, case=False, na=False)
            )
            resultados = df_cursos[mask]
            if not resultados.empty:
                for _, cur in resultados.iterrows():
                    with st.expander(f"📚 {cur['Nombre']} — {cur.get('Código','')}"):
                        c1, c2 = st.columns(2)
                        c1.write(f"**Plan Formativo:** {cur.get('Plan Formativo','')}")
                        c1.write(f"**Inicio:** {cur.get('Inicio','')} | **Fin:** {cur.get('Fin','')}")
                        c1.write(f"**Horario:** {cur.get('Horario','')}")
                        try:
                            h = float(cur["Horas"])
                            h25, h75 = calcular_horas_limite(h)
                            c2.write(f"**Horas totales:** {h}h")
                            c2.write(f"**Mínimo 25%:** {h25}h")
                            c2.write(f"**Límite faltas 75%:** {h75}h")
                        except:
                            pass
                        # Alumnos matriculados
                        dnis_cur = df_matriculas[df_matriculas["Curso"] == cur["Nombre"]]["DNI"].tolist()
                        if dnis_cur:
                            st.write(f"**Alumnos matriculados ({len(dnis_cur)}):**")
                            for d in dnis_cur:
                                fila = df_alumnos[df_alumnos["DNI"] == d]
                                nombre_alu = fila["Nombre"].iloc[0] if not fila.empty else d
                                asist = df_asistencia[(df_asistencia["DNI"] == d) & (df_asistencia["Curso"] == cur["Nombre"])]
                                p = len(asist[asist["Estado"] == "Presente"])
                                f = len(asist[asist["Estado"] == "Ausente"])
                                st.caption(f"• {nombre_alu} ({d}) → Presencias: {p} | Faltas: {f}")
                        else:
                            st.write("Sin alumnos matriculados")
            else:
                st.info("No se encontraron cursos")

# --- ELIMINAR DATOS ---
elif choice == "🗑️ Eliminar Datos":
    st.header("🗑️ Borrado de Datos")

    st.subheader("Limpiar toda la asistencia")
    conf_asist = st.checkbox("Confirmo borrado permanente de toda la asistencia")
    if st.button("Limpiar toda la asistencia") and conf_asist:
        st.session_state.df_asistencia = pd.DataFrame(columns=["Fecha", "Curso", "DNI", "Estado"])
        guardar_datos(st.session_state.df_asistencia, "asistencia")
        st.success("Asistencia borrada")
        st.rerun()

    st.divider()

    st.subheader("Eliminar asistencia de un alumno")
    if not df_alumnos.empty and not df_asistencia.empty:
        alu_asist = st.selectbox("Selecciona alumno", df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")", key="del_asist_alu")
        dni_asist = alu_asist.split("(")[1].replace(")", "")

        cursos_con_asist = df_asistencia[df_asistencia["DNI"] == dni_asist]["Curso"].unique()
        if len(cursos_con_asist) > 0:
            st.caption(f"Tiene registros en: {', '.join(cursos_con_asist)}")

        opcion = st.radio("¿Qué asistencia borrar?", ["Solo de un curso", "Toda su asistencia"], key="radio_asist")

        if opcion == "Solo de un curso" and not df_cursos.empty:
            curso_asist = st.selectbox("Curso", df_cursos["Nombre"], key="curso_asist_del")
            conf_asist_alu = st.checkbox("Confirmo borrado", key="conf_asist_alu_cur")
            if st.button("Eliminar asistencia de ese curso") and conf_asist_alu:
                st.session_state.df_asistencia = df_asistencia[
                    ~((df_asistencia["DNI"] == dni_asist) & (df_asistencia["Curso"] == curso_asist))
                ].reset_index(drop=True)
                guardar_datos(st.session_state.df_asistencia, "asistencia")
                st.success(f"Asistencia eliminada")
                st.rerun()
        else:
            conf_asist_alu2 = st.checkbox("Confirmo borrado de toda su asistencia", key="conf_asist_alu_todo")
            if st.button("Eliminar toda su asistencia") and conf_asist_alu2:
                st.session_state.df_asistencia = df_asistencia[
                    df_asistencia["DNI"] != dni_asist
                ].reset_index(drop=True)
                guardar_datos(st.session_state.df_asistencia, "asistencia")
                st.success(f"Toda la asistencia eliminada")
                st.rerun()
    else:
        st.info("No hay datos de asistencia registrados")

    st.divider()

    st.subheader("Eliminar un alumno")
    if not df_alumnos.empty:
        alu_sel = st.selectbox("Selecciona alumno a eliminar",
                               df_alumnos["Nombre"] + " (" + df_alumnos["DNI"] + ")", key="del_alu")
        dni_del = alu_sel.split("(")[1].replace(")", "")
        conf_alu = st.checkbox("Confirmo eliminar este alumno y todos sus datos", key="conf_alu")
        if st.button("Eliminar alumno") and conf_alu:
            st.session_state.df_alumnos    = df_alumnos[df_alumnos["DNI"] != dni_del].reset_index(drop=True)
            st.session_state.df_matriculas = df_matriculas[df_matriculas["DNI"] != dni_del].reset_index(drop=True)
            st.session_state.df_asistencia = df_asistencia[df_asistencia["DNI"] != dni_del].reset_index(drop=True)
            guardar_datos(st.session_state.df_alumnos, "alumnos")
            guardar_datos(st.session_state.df_matriculas, "matriculas")
            guardar_datos(st.session_state.df_asistencia, "asistencia")
            st.success(f"Alumno eliminado")
            st.rerun()
    else:
        st.info("No hay alumnos registrados")

    st.divider()

    st.subheader("Eliminar un curso")
    if not df_cursos.empty:
        curso_del = st.selectbox("Selecciona curso a eliminar", df_cursos["Nombre"], key="del_cur")
        conf_cur = st.checkbox("Confirmo eliminar este curso y todos sus datos", key="conf_cur")
        if st.button("Eliminar curso") and conf_cur:
            st.session_state.df_cursos     = df_cursos[df_cursos["Nombre"] != curso_del].reset_index(drop=True)
            st.session_state.df_matriculas = df_matriculas[df_matriculas["Curso"] != curso_del].reset_index(drop=True)
            st.session_state.df_asistencia = df_asistencia[df_asistencia["Curso"] != curso_del].reset_index(drop=True)
            guardar_datos(st.session_state.df_cursos, "cursos")
            guardar_datos(st.session_state.df_matriculas, "matriculas")
            guardar_datos(st.session_state.df_asistencia, "asistencia")
            st.success(f"Curso eliminado")
            st.rerun()
    else:
        st.info("No hay cursos registrados")
