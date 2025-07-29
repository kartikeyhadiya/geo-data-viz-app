import os
from os.path import join
import tempfile
import streamlit as st
import pandas as pd
from utils import create_map, download_from_s3, list_folders

# Sample dataset dictionary: keys are dataset names, and values are S3 paths
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
BUCKET_NAME = st.secrets["BUCKET_NAME"]
PREFIXES = [
    st.secrets["S3_GIS_DATA_PREFIX"],
    st.secrets["S3_SOCIO_ECONOMIC_DATA_PREFIX"],
    st.secrets["S3_TECHNO_ECONOMIC_DATA_PREFIX"]
]

selected_iso = 'format_iso'
DATASETS = {
    "": None,
    "country_boundaries": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Administrative/Country_boundaries/Country_boundaries.geojson",
    "buffaloes": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Livestock/buffaloes/buffaloes.tif",
    "cattles": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Livestock/cattles/cattles.tif",
    "goats": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Livestock/goats/goats.tif",
    "pigs": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Livestock/pigs/pigs.tif",
    "poultry": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Livestock/poultry/poultry.tif",
    "sheeps": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Livestock/sheeps/sheeps.tif",
    "Temperature": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Temperature/Temperature.tif",
    "Water scarcity": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biogas/Water scarcity/Water scarcity.tif",
    "Forest": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biomass/Forest/Forest.tif",
    "Friction": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Biomass/Friction/Friction.tif",
    "Population": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Demographics/Population/Population.tif",
    "Urban": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Demographics/Urban/Urban.tif",
    "MV_lines": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Electricity/MV_lines/MV_lines.geojson",
    "Night_time_lights": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/Electricity/Night_time_lights/Night_time_lights.tif",
    "Traveltime": f"s3://{BUCKET_NAME}/{PREFIXES[0]}/{selected_iso}/LPG/Traveltime/Traveltime.tif",
    "Socio-economic Private benefits": f"s3://{BUCKET_NAME}/{PREFIXES[1]}/Private benefits/{selected_iso}.csv",
    "Socio-economic Social benefits": f"s3://{BUCKET_NAME}/{PREFIXES[1]}/Social benefits/{selected_iso}.csv",
    "Techno-economic Private benefits": f"s3://{BUCKET_NAME}/{PREFIXES[2]}/Private benefits/{selected_iso}_file_tech_specs.csv",
    "Techno-economic Social benefits": f"s3://{BUCKET_NAME}/{PREFIXES[2]}/Social benefits/{selected_iso}_file_tech_specs.csv",
}

SESSION_TEMP_DIR = join(tempfile.gettempdir(), "streamlit_data_visualizer_app_session")
# print(f"Session temp directory: {SESSION_TEMP_DIR}")

st.set_page_config(layout="wide")
st.title("Geospatial Data Visualizer")

@st.cache_data
def get_iso_list(bucket_name, prefix):
    return [""] + list(list_folders(bucket_name, prefix+'/'))

# Function to reset dataset dropdown when ISO changes
def reset_dataset():
    st.session_state.dataset = list(DATASETS.keys())[0]

@st.fragment
def download_button():
    if st.button("Download Dataset"):
        try:
            s3_url = DATASETS[selected_dataset]
            # Replace placeholder with selected ISO
            s3_url = s3_url.replace('format_iso', selected_iso)
            
            # Download file to a BytesIO buffer
            key = s3_url.replace(f"s3://{BUCKET_NAME}/", "")
            file_path = download_from_s3(BUCKET_NAME, key, join(SESSION_TEMP_DIR, selected_iso))
            with open(file_path, "rb") as f:
                data = f.read()
                st.download_button(
                    label="Click to Save the File",
                    data=data,
                    file_name=key,
                    mime="application/octet-stream"
                )
        except Exception as e:
            st.error(f"Error during download: {e}")

@st.cache_data
def read_csv(file_path):
    """Read a CSV file and return a DataFrame."""
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
        return None

# iso_list = ["", "BDI", "AGO", "BEN", "CAF", "KEN", "ZAF", "TZA", "UGA", "ZMB", "ZWE"]
iso_list = get_iso_list(BUCKET_NAME, PREFIXES[0])

# Initialize session state for the dropdowns if not already set
if "iso" not in st.session_state:
    st.session_state.iso = iso_list[0]
if "dataset" not in st.session_state:
    st.session_state.dataset = list(DATASETS.keys())[0]

# Create two columns: left for controls, right for visualization
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    # ISO Dropdown with on_change callback to reset the dataset dropdown
    selected_iso = st.selectbox("Select ISO", iso_list, key="iso", on_change=reset_dataset)
    os.makedirs(join(SESSION_TEMP_DIR, selected_iso), exist_ok=True)

    # Dataset Dropdown
    selected_dataset = st.selectbox("Select dataset to visualize", list(DATASETS.keys()), key="dataset")
    
    st.markdown("---")
    st.subheader("Download Dataset")
    
    # When download button is clicked, use boto3 to download the file
    download_button()

with col2:
    if selected_iso and selected_dataset:

        s3_url = DATASETS[selected_dataset]
        # Replace placeholder with selected ISO
        s3_url = s3_url.replace('format_iso', selected_iso)
        # print(f"{s3_url= }")

        st.write(f"Visualizing dataset: {selected_dataset} for ISO: {selected_iso}")
        key = s3_url.replace(f"s3://{BUCKET_NAME}/", "")
        ext = key.split('.')[-1].lower()

        if ext == 'csv':
            # Download the CSV file and load it as a dataframe.
            os.makedirs(join(SESSION_TEMP_DIR, selected_iso, selected_dataset), exist_ok=True)
            file_path = download_from_s3(BUCKET_NAME, key, join(SESSION_TEMP_DIR, selected_iso, selected_dataset))
            df = read_csv(file_path)
            # Display the dataframe with a fixed height so about 25 rows are visible.
            st.dataframe(df, height=10*35)

        elif ext in ('tif', 'tiff', 'gtiff', 'geojson', 'shp'):
            m = create_map(BUCKET_NAME, key, selected_dataset, join(SESSION_TEMP_DIR, selected_iso))
            print('map created')
            if m is not None:
                # For maps return from create_map
                m.to_streamlit(width=1200, height=600)
                print('passed to streamlit')

        else:
            st.error(f"Unsupported file type: {ext}. Please select a valid dataset.")
