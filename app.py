import streamlit as st
import pikepdf
from pikepdf import Pdf, Rectangle
import time
import io
import os
import zipfile

st.set_page_config(page_title="Combinador de PDFs", page_icon="📄", layout="wide")

# Inicializar session_state para el contador del uploader
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

st.title("📄 Combinador de PDFs")
st.write("Combina páginas de un PDF en parejas verticales siguiendo el patrón: (1,3), (2,4), (5,7), (6,8)...")

# Subir múltiples archivos con key dinámico
archivos_subidos = st.file_uploader(
    "Sube uno o varios PDFs", 
    type=['pdf'],
    accept_multiple_files=True,
    key=f'file_uploader_{st.session_state.uploader_key}'
)

if archivos_subidos:
    # Fila con info y botón de borrar
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📁 {len(archivos_subidos)} archivo(s) subido(s)")
    with col2:
        if st.button("🗑️ Borrar todos", type="secondary", use_container_width=True):
            st.session_state.uploader_key += 1
            st.rerun()
    
    # Mostrar lista de archivos subidos en un expander
    with st.expander(f"📋 Ver los {len(archivos_subidos)} archivo(s) subido(s)"):
        for i, archivo in enumerate(archivos_subidos, 1):
            st.write(f"{i}. {archivo.name}")
    
    # Botón para procesar
    if st.button("🚀 Procesar todos los PDFs", type="primary"):
        
        # Progreso general
        progreso_general = st.progress(0)
        texto_general = st.empty()
        
        archivos_procesados = []
        tiempo_total_inicio = time.time()
        
        # Contenedor colapsable para detalles de procesamiento
        with st.expander("📊 Ver detalles de procesamiento", expanded=False):
            contenedor_detalles = st.container()
        
        for idx_archivo, archivo_subido in enumerate(archivos_subidos, 1):
            # Actualizar progreso general
            progreso_general.progress((idx_archivo - 1) / len(archivos_subidos))
            texto_general.text(f"Procesando archivo {idx_archivo}/{len(archivos_subidos)}: {archivo_subido.name}")
            
            with contenedor_detalles:
                st.write(f"**{idx_archivo}. {archivo_subido.name}**")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    barra_archivo = st.progress(0)
                with col2:
                    estado_archivo = st.empty()
            
            inicio = time.time()
            
            try:
                # Leer PDF desde memoria
                pdf_bytes = archivo_subido.read()
                pdf_origen = Pdf.open(io.BytesIO(pdf_bytes))
                num_paginas = len(pdf_origen.pages)
                
                # Obtener dimensiones
                primera_pagina = pdf_origen.pages[0]
                mediabox = primera_pagina.mediabox
                ancho = float(mediabox[2] - mediabox[0])
                alto = float(mediabox[3] - mediabox[1])
                
                # Pre-calcular índices
                indices_a_procesar = []
                p = 0
                for i in range(80):
                    if i % 2 == 0:
                        indices = (p, p + 2)
                    else:
                        indices = (p + 1, p + 3)
                        p += 4
                    
                    if indices[0] >= num_paginas or indices[1] >= num_paginas:
                        break
                    
                    indices_a_procesar.append(indices)
                
                total_pares = len(indices_a_procesar)
                
                # Crear nuevo PDF
                pdf_salida = Pdf.new()
                
                # Procesar páginas
                for i, (idx_arriba, idx_abajo) in enumerate(indices_a_procesar, 1):
                    # Actualizar progreso cada 5 páginas
                    if i % 5 == 0 or i == 1 or i == total_pares:
                        progreso = i / total_pares
                        barra_archivo.progress(progreso)
                        estado_archivo.text(f"{i}/{total_pares}")
                    
                    # Crear página nueva
                    nueva_pagina = pdf_salida.add_blank_page(page_size=(ancho, alto * 2))
                    
                    # Obtener páginas
                    pagina_abajo = pdf_origen.pages[idx_abajo]
                    pagina_arriba = pdf_origen.pages[idx_arriba]
                    
                    # Combinar
                    nueva_pagina.add_overlay(pagina_abajo, Rectangle(0, 0, ancho, alto))
                    nueva_pagina.add_overlay(pagina_arriba, Rectangle(0, alto, ancho, alto * 2))
                
                barra_archivo.progress(1.0)
                estado_archivo.text("✅")
                
                # Cerrar PDF origen
                pdf_origen.close()
                
                # Guardar en memoria
                buffer = io.BytesIO()
                pdf_salida.save(buffer, compress_streams=True)
                pdf_salida.close()
                buffer.seek(0)
                
                tiempo_total = time.time() - inicio
                
                # Generar nombre de archivo con _Combinado
                nombre_original = archivo_subido.name
                nombre_sin_extension = os.path.splitext(nombre_original)[0]
                nombre_salida = f"{nombre_sin_extension}_Combinado.pdf"
                
                # Guardar info para descarga
                archivos_procesados.append({
                    'nombre': nombre_salida,
                    'nombre_original': nombre_original,
                    'buffer': buffer,
                    'tiempo': tiempo_total,
                    'pares': total_pares
                })
                
            except Exception as e:
                estado_archivo.text("❌")
                with contenedor_detalles:
                    st.error(f"Error: {str(e)}")
        
        # Actualizar progreso general al 100%
        progreso_general.progress(1.0)
        tiempo_total_general = time.time() - tiempo_total_inicio
        texto_general.text(f"✅ Procesamiento completado en {tiempo_total_general:.2f}s")
        
        # SECCIÓN DE DESCARGAS - ARRIBA
        st.write("---")
        st.header("📥 Descargar archivos procesados")
        
        if archivos_procesados:
            st.success(f"🎉 {len(archivos_procesados)} archivo(s) procesado(s) correctamente")
            
            # Botón para descargar todos en ZIP
            if len(archivos_procesados) > 1:
                # Mensaje mientras se prepara el ZIP
                placeholder_zip = st.empty()
                placeholder_zip.info("⏳ Preparando archivo ZIP...")
                
                # Crear ZIP en memoria
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for archivo_info in archivos_procesados:
                        zip_file.writestr(archivo_info['nombre'], archivo_info['buffer'].getvalue())
                
                zip_buffer.seek(0)
                
                # Limpiar mensaje de carga
                placeholder_zip.empty()
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.download_button(
                        label="📦 Descargar todos (ZIP)",
                        data=zip_buffer,
                        file_name="PDFs_Combinados.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
                with col2:
                    st.info(f"Descargarás {len(archivos_procesados)} archivos PDF en un único archivo ZIP")
                
                st.write("---")
            
            # Descargas individuales con selectbox
            st.subheader("📄 Descargar archivos individuales")
            
            # Crear opciones para el selectbox
            opciones_archivos = [f"{i+1}. {info['nombre_original']} → {info['nombre']}" 
                                for i, info in enumerate(archivos_procesados)]
            
            archivo_seleccionado_idx = st.selectbox(
                "Selecciona un archivo para descargar:",
                range(len(archivos_procesados)),
                format_func=lambda x: opciones_archivos[x]
            )
            
            # Mostrar información del archivo seleccionado
            archivo_sel = archivos_procesados[archivo_seleccionado_idx]
            
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.metric("Nombre", archivo_sel['nombre'][:25] + "..." if len(archivo_sel['nombre']) > 25 else archivo_sel['nombre'])
            with col2:
                st.metric("Tiempo de proceso", f"{archivo_sel['tiempo']:.2f}s")
            with col3:
                st.metric("Pares procesados", archivo_sel['pares'])
            
            st.write("")
            
            # Botón de descarga del archivo seleccionado
            st.download_button(
                label=f"⬇️ Descargar {archivo_sel['nombre']}",
                data=archivo_sel['buffer'],
                file_name=archivo_sel['nombre'],
                mime="application/pdf",
                type="secondary",
                use_container_width=True
            )
            
        else:
            st.warning("⚠️ No se procesó ningún archivo correctamente")

else:
    st.info("👆 Sube uno o varios archivos PDF para comenzar")
    
    # Instrucciones
    st.markdown("---")
    st.markdown("### 📝 Cómo funciona")
    st.markdown("""
    1. **Sube uno o varios PDFs** usando el selector de archivos de arriba
    2. **Haz clic en "Procesar"** y espera a que termine el procesamiento
    3. **Descarga los archivos:**
       - Si procesaste varios PDFs, puedes descargarlos todos en un ZIP
       - O selecciona un archivo específico para descargarlo individualmente
    
    ---
    
    ### 🔄 Patrón de combinación
    
    Las páginas se combinan verticalmente en parejas siguiendo este orden:
    
    - **Par 1:** página 1 (arriba) + página 3 (abajo)
    - **Par 2:** página 2 (arriba) + página 4 (abajo)
    - **Par 3:** página 5 (arriba) + página 7 (abajo)
    - **Par 4:** página 6 (arriba) + página 8 (abajo)
    - Y así sucesivamente...
    
    El resultado son páginas verticales del doble de altura con dos páginas del documento original.
    """)
