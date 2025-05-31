import pandas as pd
import streamlit as st
import re
import io

# Configuración de la página - AÑADIR ESTO AL INICIO
st.set_page_config(
    page_title="Consolidador de Clientes Claro",  # Cambia este texto al nombre que desees
    page_icon="📱",  # Puedes usar emojis o rutas a imágenes
    layout="wide",  # Opciones: "centered" o "wide"
    initial_sidebar_state="expanded"  # Opciones: "auto", "expanded", "collapsed"
)

def limpiar_csv(df):

  
    columnas_necesarias = {
        "ID del cliente": "CI/RUC",
        "Nombre del cliente": "Nombre del cliente",
        "Número de teléfono": "celular",
        "Plan  tarifario": "Plan tarifario",
        "Operadora Donante": "Operadora Donante",
        "Fecha Gestion ASCP": "Fecha Gestion ASCP",
    }

    df = df[list(columnas_necesarias.keys())].rename(columns=columnas_necesarias)


    # Asegurar que la columna "celular" exista y mantenga ceros iniciales
    if "celular" in df.columns:
        df["celular"] = df["celular"].astype(str).str.zfill(10)

    return df

def consolidar_duplicados(df):
    if "CI/RUC" not in df.columns:
        return df, pd.DataFrame()  # Si no hay identificación, devolver igual y un DataFrame vacío
    
    # Crear un DataFrame para clientes con más de 5 líneas
    clientes_con_muchas_lineas = df.groupby("CI/RUC").filter(lambda x: len(x) > 5)
    
    # Crear un DataFrame para clientes con 5 o menos líneas
    clientes_con_pocas_lineas = df.groupby("CI/RUC").filter(lambda x: len(x) <= 5)
    
    # Procesar clientes con 5 o menos líneas como antes
    if not clientes_con_pocas_lineas.empty:
        # Agrupar los celulares en nuevas columnas celular1, celular2, ..., celular5
        df_agrupado = clientes_con_pocas_lineas.groupby("CI/RUC").agg({
            "Nombre del cliente": "first",
            "Plan tarifario": "first",
            "Operadora Donante": "first",
            "Fecha Gestion ASCP": "first",    
            "celular": lambda x: list(x)[:5]  # Tomar máximo 5 celulares por identificación
        }).reset_index()

        # Expandir los celulares en columnas celular1, celular2, ..., celular5
        for i in range(5):
            df_agrupado[f"celular{i+1}"] = df_agrupado["celular"].apply(lambda x: x[i] if i < len(x) else "")

        df_agrupado.drop(columns=["celular"], inplace=True)  # Eliminar la columna original
        # Agregar una columna con el total de números agrupados
        df_agrupado["No. Lineas"] = df_agrupado["celular1"].apply(lambda x: 1 if x != "" else 0) + \
                                     df_agrupado["celular2"].apply(lambda x: 1 if x != "" else 0) + \
                                     df_agrupado["celular3"].apply(lambda x: 1 if x != "" else 0) + \
                                     df_agrupado["celular4"].apply(lambda x: 1 if x != "" else 0) + \
                                     df_agrupado["celular5"].apply(lambda x: 1 if x != "" else 0)
        # Reordenar las columnas para que 'No. Lineas' esté en la segunda posición
        columnas_ordenadas = ["CI/RUC", "No. Lineas", "Nombre del cliente", "celular1", "celular2", "celular3", "celular4", "celular5","Plan tarifario", "Operadora Donante", "Fecha Gestion ASCP"]
        df_agrupado = df_agrupado[columnas_ordenadas]
    else:
        df_agrupado = pd.DataFrame()
    
    return df_agrupado, clientes_con_muchas_lineas

def eliminar_filas_planes(df):
   
    planes_a_eliminar = [
        "OTECEL", "PLAN TOTAL 50", "PLAN TOTAL 0", "PLAN TOTAL 15", "PLAN TOTAL 10",
        "Plan SipTrunk 180", "BAM OTECEL/DAS", "PLAN TOTAL 100", "Plan Proveedores",
        "Plan Smart $8", "BAM OTECEL/DAS.", "PLAN TOTAL 0.", "PLAN TOTAL 10.",
        "Plan Smart $6..", "PLAN LOCALIZACIÓN 1800 VEHIC.", "PLAN M2M CONTROLADO",
        "PLAN SIP TRUNK 45", "PLAN SIP TRUNK 180", "Plan Proveedores.", "PLAN TOTAL 15.",
        "Plan Genérico Datos.", "PLAN M2M TEST.", "PLAN TOTAL 6.", "Plan Datos Móviles.",
        "Plan Smart $8..", "PLAN SIP TRUNK 20",
        "PLAN LOCALIZACION VEHIC. POSPAGO STAND-BY", "PLAN LOCALIZACION VEHICULAR HIBRIDO 1",
        
        "LOCALIZADOR"
    ]

    # Unir los planes en una expresión regular para `str.contains`
    regex_pattern = "|".join(map(re.escape, planes_a_eliminar))  # Escapar caracteres especiales

    # Número de filas antes de eliminar
    filas_antes = df.shape[0]

    # Filtrar las filas que no contienen ninguno de los planes en la columna 'planes'
    df_filtrado = df[~df["Plan tarifario"].str.contains(regex_pattern, case=False, na=False)]

    # Número de filas después de eliminar
    filas_despues = df_filtrado.shape[0]

    # Mostrar el mensaje con la cantidad de filas eliminadas
    filas_eliminadas = filas_antes - filas_despues
    print(f"Se eliminaron {filas_eliminadas} filas. Quedaron {filas_despues} filas.")
    return df_filtrado

st.title("🔄 Unir, Limpiar y Consolidar Identificaciones Duplicadas")

archivos = st.file_uploader("📂 Carga varios archivos CSV", type=["csv"], accept_multiple_files=True)

if archivos:
    dataframes = []

    for archivo in archivos:
        try:
            # Leer el archivo con delimitador "," (comas) y sin cabeceras extras
            df = pd.read_csv(archivo, dtype={"Número de teléfono": str, "ID del cliente": str}, encoding="utf-8", delimiter=",", skiprows=12)
            
            df = limpiar_csv(df)  # Borra las 3 primeras filas y limpia los datos
            dataframes.append(df)
        except Exception as e:
            st.error(f"⚠️ Error al procesar {archivo.name}: {e}")

    if dataframes:
        st.write("✅ **Archivos unidos:**")
        df_unido = pd.concat(dataframes, ignore_index=True)  # Unificar archivos
        st.dataframe(df_unido.head(50000))
        st.write(f"🔹 **El archivo consolidado tiene {df_unido.shape[0]} filas y {df_unido.shape[1]} columnas.**")
        df_unido = eliminar_filas_planes(df_unido)

        # Consolidar identificaciones duplicadas y separar clientes con más de 5 líneas
        df_final, df_muchas_lineas = consolidar_duplicados(df_unido)

        # Mostrar datos de clientes con 5 o menos líneas
        if not df_final.empty:
            st.write("✅ **Datos consolidados (clientes con 5 o menos líneas):**")
            st.dataframe(df_final.head(20))  # Mostrar los primeros 20 registros después de la consolidación
            
            # Descargar el archivo consolidado
            csv_final = df_final.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar archivo consolidado csv",
                data=csv_final,
                file_name="archivo_consolidado.csv",
                mime="text/csv"
            )

            # Convertir DataFrame a Excel en memoria
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_final.to_excel(writer, index=False, sheet_name="Datos Consolidados")
                writer.close()

            # Botón de descarga en Streamlit para Excel
            st.download_button(
                label="📥 Descargar archivo consolidado en Excel",
                data=output.getvalue(),
                file_name="archivo_consolidado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Mostrar datos de clientes con más de 5 líneas
        if not df_muchas_lineas.empty:
            st.write("⚠️ **Clientes con más de 5 líneas (sin consolidar):**")
            st.dataframe(df_muchas_lineas.head(20))  # Mostrar los primeros 20 registros
            st.write(f"🔹 **Se encontraron {df_muchas_lineas.shape[0]} líneas de clientes con más de 5 números.**")
            
            # Descargar el archivo de clientes con muchas líneas
            csv_muchas_lineas = df_muchas_lineas.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar archivo de clientes con más de 5 líneas (csv)",
                data=csv_muchas_lineas,
                file_name="clientes_muchas_lineas.csv",
                mime="text/csv"
            )

            # Convertir DataFrame a Excel en memoria
            output_muchas = io.BytesIO()
            with pd.ExcelWriter(output_muchas, engine="xlsxwriter") as writer:
                df_muchas_lineas.to_excel(writer, index=False, sheet_name="Clientes Muchas Lineas")
                writer.close()

            # Botón de descarga en Streamlit para Excel
            st.download_button(
                label="📥 Descargar archivo de clientes con más de 5 líneas (Excel)",
                data=output_muchas.getvalue(),
                file_name="clientes_muchas_lineas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_muchas_excel"  # Clave única para evitar conflictos con otros botones
            )