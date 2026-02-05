import streamlit as st
import pikepdf
from pikepdf import Pdf, Rectangle
import time
import io
import os
import zipfile
import gc

st.set_page_config(page_title="Combinador de PDFs", page_icon="📄", layout="wide")

if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

st.title("📄 Combinador de PDFs")
st.write("Combina páginas de un PDF en parejas verticales siguiendo el patrón: (1,3), (2,4), (5,7), (6,8)...")

archivos_subidos = st.file_uploader(
    "Sube uno o varios PDFs",
    type=['pdf'],
    accept_multiple_files=True,
    key=f'file_uploader_{st.session_state.uploader_key}'
)

if archivos_subidos:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📁 {len(archivos_subidos)} archivo(s) subido(s)")
    with col2:
        if st.button("🗑️ Borrar todos", type="secondary", use_container_width=True):
            st.session_state.uploader_key += 1
            st.rerun()

    with st.expander(f"📋 Ver los {len(archivos_subidos)} archivo(s) subido(s)"):
        for i, archivo in enumerate(archivos_subidos, 1):
            st.write(f"{i}. {archivo.name}")

    if st.button("🚀 Procesar todos los PDFs", type="primary"):
        progreso_general = st.progress(0)
        texto_general = st.empty()

        archivos_procesados = []
        tiempo_total_inicio = time.time()

        with st.expander("📊 Ver detalles de procesamiento", expanded=False):
            contenedor_detalles = st.container()

        for idx_archivo, archivo_subido in enumerate(archivos_subidos, 1):
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
                # Leer PDF
                pdf_bytes = archivo_subido.read()
                pdf_origen = Pdf.open(io.BytesIO(pdf_bytes))
                num_paginas = len(pdf_origen.pages)

                primera_pagina = pdf_origen.pages[0]
                mediabox = primera_pagina.mediabox
                ancho = float(mediabox[2] - mediabox[0])
                alto = float(mediabox[3] - mediabox[1])

                # Calcular índices dinámicamente
                indices_a_procesar = []
                for p in range(0, num_paginas, 4):
                    if p + 2 < num_paginas:
                        indices_a_procesar.append((p, p + 2))
                    if p + 3 < num_paginas:
                        indices_a_procesar.append((p + 1, p + 3))

                total_pares = len(indices_a_procesar)
                pdf_salida = Pdf.new()

                for i, (idx_arriba, idx_abajo) in enumerate(indices_a_procesar, 1):
                    if i % 5 == 0 or i == 1 or i == total_pares:
                        barra_archivo.progress(i / total_pares)
                        estado_archivo.text(f"{i}/{total_pares}")

                    nueva_pagina = pdf_salida.add_blank_page(page_size=(ancho, alto * 2))
                    nueva_pagina.add_overlay(pdf_origen.pages[idx_abajo], Rectangle(0, 0, ancho, alto))
                    nueva_pagina.add_overlay(pdf_origen.pages[idx_arriba], Rectangle(0, alto, ancho, alto * 2))

                barra_archivo.progress(1.0)
                estado_archivo.text("✅")

                pdf_origen.close()
                del pdf_origen
                del pdf_bytes
                gc.collect()

                # Guardar resultado comprimido eficientemente
                buffer = io.BytesIO()
                pdf_salida.save(
                    buffer,
                    compress_streams=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate
                )
                pdf_salida.close()
                del pdf_salida
                gc.collect()

                buffer.seek(0)

                tiempo_total = time.time() - inicio
                nombre_original = archivo_subido.name
                nombre_sin_extension = os.path.splitext(nombre_original)[0]
                nombre_salida = f"{nombre_sin_extension}_Combinado.pdf"

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

        progreso_general.progress(1.0)
        tiempo_total_general = time.time() - tiempo_total_inicio
        texto_general.text(f"✅ Procesamiento completado en {tiempo_total_general:.2f}s")

        st.write("---")
        st.header("📥 Descargar archivos procesados")

        if archivos_procesados:
            st.success(f"🎉 {len(archivos_procesados)} archivo(s) procesado(s) correctamente")

            if len(archivos_procesados) > 1:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for archivo_info in archivos_procesados:
                        zip_file.writestr(archivo_info['nombre'], archivo_info['buffer'].getvalue())
                zip_buffer.seek(0)

                st.download_button(
                    label="📦 Descargar todos (ZIP)",
                    data=zip_buffer,
                    file_name="PDFs_Combinados.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
                del zip_buffer
                gc.collect()

            st.subheader("📄 Descargar archivos individuales")

            opciones_archivos = [f"{i+1}. {info['nombre_original']} → {info['nombre']}"
                                 for i, info in enumerate(archivos_procesados)]

            archivo_seleccionado_idx = st.selectbox(
                "Selecciona un archivo para descargar:",
                range(len(archivos_procesados)),
                format_func=lambda x: opciones_archivos[x]
            )

            archivo_sel = archivos_procesados[archivo_seleccionado_idx]

            st.download_button(
                label=f"⬇️ Descargar {archivo_sel['nombre']}",
                data=archivo_sel['buffer'],
                file_name=archivo_sel['nombre'],
                mime="application/pdf",
                use_container_width=True
            )

        else:
            st.warning("⚠️ No se procesó ningún archivo correctamente")

else:
    st.info("👆 Sube uno o varios archivos PDF para comenzar")
  
