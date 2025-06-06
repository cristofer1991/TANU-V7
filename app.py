
import streamlit as st
import requests
from pathlib import Path
import zipfile
import io
import shutil

st.set_page_config(page_title="Descargador de Aves Patagonia", layout="centered")
st.title("🦅 Descargador de Imágenes de Aves - Patagonia (iNaturalist API)")

st.markdown("Esta herramienta permite descargar imágenes de aves observadas en la Patagonia y otras regiones de Chile desde iNaturalist, para construir datasets de visión artificial.")

# Lista extendida de aves comunes en Magallanes
especies_dict = {
    "Tiuque (Milvago chimango)": "Milvago chimango",
    "Queltehue (Vanellus chilensis)": "Vanellus chilensis",
    "Carancho (Caracara plancus)": "Caracara plancus",
    "Cauquén común (Chloephaga picta)": "Chloephaga picta",
    "Cauquén colorado (Chloephaga rubidiceps)": "Chloephaga rubidiceps",
    "Gaviota dominicana (Larus dominicanus)": "Larus dominicanus",
    "Jote cabeza colorada (Cathartes aura)": "Cathartes aura",
    "Jote cabeza negra (Coragyps atratus)": "Coragyps atratus",
    "Ñandú (Rhea pennata)": "Rhea pennata",
    "Canquén (Coscoroba coscoroba)": "Coscoroba coscoroba",
    "Rayador (Rynchops niger)": "Rynchops niger"
}

# Diccionario de regiones (place_id de iNaturalist)
region_place_ids = {
    "Todo el mundo": None,
    "Magallanes": 7083,
    "Región Metropolitana": 6787,
    "Valparaíso": 6785,
    "Los Lagos": 6791,
    "Aysén": 7081,
    "Biobío": 6789,
    "Araucanía": 6790,
    "Coquimbo": 6784
}

especie = st.selectbox("Selecciona una especie de ave:", list(especies_dict.keys()))
nombre_cientifico = especies_dict[especie]
cantidad = st.slider("Cantidad máxima de imágenes a descargar:", 10, 500, 100)

st.markdown("### 🔍 Filtros opcionales")

region = st.selectbox("Filtrar por región", list(region_place_ids.keys()))
licencia_opcion = st.selectbox("Filtrar por licencia de uso", ["Solo licencias abiertas (CC0, BY, BY-SA)", "Todas las licencias"])
solo_calidad_alta = st.checkbox("Solo observaciones con calidad 'research'", value=True)
solo_en_vuelo = st.checkbox("Buscar solo aves en vuelo (requiere 'flight' o 'vuelo' en la descripción)", value=False)

if st.button("Iniciar descarga"):
    carpeta_destino = Path("dataset") / nombre_cientifico.replace(" ", "_")
    if carpeta_destino.exists():
        shutil.rmtree(carpeta_destino)
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    fotos = []
    page = 1
    base_url = f"https://api.inaturalist.org/v1/observations"
    params = {
        "taxon_name": nombre_cientifico,
        "photos": "true",
        "per_page": 100,
        "page": page
    }

    if licencia_opcion == "Solo licencias abiertas (CC0, BY, BY-SA)":
        params["license"] = "CC0,CC-BY,CC-BY-SA"
    if solo_calidad_alta:
        params["quality_grade"] = "research"
    if region_place_ids[region]:
        params["place_id"] = region_place_ids[region]

    st.write(f"🔎 Buscando imágenes para: **{nombre_cientifico}**")

    while len(fotos) < cantidad and page <= 10:
        params["page"] = page
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            break
        data = response.json()
        if not data["results"]:
            break

        for obs in data["results"]:
            if solo_en_vuelo:
                description = obs.get("description", "") or ""
                if "vuelo" not in description.lower() and "flight" not in description.lower():
                    continue
            for foto in obs.get("photos", []):
                url = foto.get("url", "").replace("square", "original").split("?")[0]
                if url not in fotos:
                    fotos.append(url)
                if len(fotos) >= cantidad:
                    break
            if len(fotos) >= cantidad:
                break
        page += 1

    if not fotos:
        st.error("No se encontraron imágenes con los filtros aplicados.")
    else:
        progreso = st.progress(0)
        for i, url in enumerate(fotos):
            ext = url.split('.')[-1]
            img_data = requests.get(url).content
            with open(carpeta_destino / f"{nombre_cientifico.replace(' ', '_')}_{i}.{ext}", "wb") as f:
                f.write(img_data)
            progreso.progress((i + 1) / len(fotos))

        st.success(f"✅ {len(fotos)} imágenes descargadas correctamente.")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for img_file in carpeta_destino.glob("*.*"):
                zip_file.write(img_file, arcname=img_file.name)
        zip_buffer.seek(0)

        st.download_button(
            label="📥 Descargar imágenes como ZIP",
            data=zip_buffer,
            file_name=f"{nombre_cientifico.replace(' ', '_')}_imagenes.zip",
            mime="application/zip"
        )
