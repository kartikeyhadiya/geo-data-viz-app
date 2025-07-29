from os.path import (
    join,
    basename,
    exists,
    splitext,
    getsize,
    getmtime
)
from typing import Literal
from datetime import datetime

import streamlit as st
import boto3
import numpy as np
import rasterio
import leafmap.foliumap as leafmap

@st.cache_data
def calculate_vmin_vmax(
    image_path,
    method: Literal['std_dev', 'min_max', 'percent_clip']='min_max',
    percent_clip=(2, 98),
    std_factor=2
):
    """
    Compute vmin and vmax for raster visualization.

    Parameters:
        image_path (str): Path to the raster image.
        method (str): Method for computing min/max ('min_max', 'percent_clip', 'std_dev').
        percent_clip (tuple): Percentile clip values (low, high) for 'percent_clip' method.
        std_factor (float): Standard deviation factor for 'std_dev' method.

    Returns:
        tuple: (vmin, vmax)
    """
    with rasterio.open(image_path) as src:
        data = src.read(1).astype(np.float64)  # Read first band
        nodata = src.nodata

    # Mask NoData, NaN, and Inf values
    valid_data = data[~np.isnan(data) & ~np.isinf(data)]
    if nodata is not None:
        valid_data = valid_data[valid_data != nodata]

    if valid_data.size == 0:
        raise ValueError("No valid pixel values found in the raster.")

    if method == 'min_max':
        vmin, vmax = np.min(valid_data), np.max(valid_data)
    elif method == 'percent_clip':
        vmin, vmax = np.percentile(valid_data, percent_clip)
    elif method == 'std_dev':
        mean, std = np.mean(valid_data), np.std(valid_data)
        vmin, vmax = mean - std_factor * std, mean + std_factor * std
    else:
        raise ValueError("Invalid method. Choose from 'min_max', 'percent_clip', or 'std_dev'.")

    return vmin, vmax

def visualize_vector(vector_path, layer_name=None):
    """
    Visualize a vector file using leafmap.

    Parameters:
        vector_path (str): Path to the vector file.
        layer_name (str): Name for the layer in the map.
    """
    if layer_name is None:
        layer_name = splitext(basename(vector_path))[0]

    m = leafmap.Map(center=[20, 0], zoom=2)
    m.add_geojson(vector_path, layer_name=layer_name)

    return m

def visualize_raster(
    img_path,
    layer_name=None,
    colormap='binary',
    vmin=None,
    vmax=None,
    build_overviews=False,
    overviews_levels=[2, 4, 8, 16, 32, 64]
):
    """
    Visualize a raster image using leafmap.

    Parameters:
        img_path (str): Path to the raster image.
        layer_name (str): Name for the layer in the map.
        colormap (str): Colormap for the visualization.
        vmin (float): Minimum value for the
        vmax (float): Maximum value for the visualization.
    """

    m = leafmap.Map(center=[20, 0], zoom=2)
    if layer_name is None:
        layer_name = splitext(basename(img_path))[0]

    if vmin is None or vmax is None:
      v_min, v_max = calculate_vmin_vmax(img_path, method='std_dev')
      print(f"{v_min= }, {v_max= }")

    if build_overviews:
        # Build overviews for .tif and .tiff files
        with rasterio.open(img_path, 'r+') as dst:
            if not dst.overviews(1):
                # height, width = dst.shape
                # overview_level = get_maximum_overview_level(width, height, minsize=256)
                # overviews_levels = [2**j for j in range(1, overview_level + 1)]
                dst.build_overviews(overviews_levels, rasterio.enums.Resampling.nearest)
                dst.update_tags(ns='rio', resampling='nearest')

    vis_params = {'indexes': [1], 'vmin': v_min, 'vmax': v_max, 'opacity': 1.0, 'colormap': colormap}
    m.add_raster(img_path, layer_name=layer_name, **vis_params)

    return m

def create_map(bucket_name, key, layer_name, session_temp_dir):

    # Ensure the file_path is downloaded before adding to the map
    file_path = download_from_s3(bucket_name, key, session_temp_dir)

    ext = key.split('.')[-1].lower()
    if ext in ('tif', 'tiff', 'gtiff'):

        # build_overviews = st.checkbox("Build overviews for raster", value=True)
        build_overviews = False
        if getsize(file_path) > 100 * 1024 * 1024:
            # st.warning("The file is larger than 100MB, which may cause performance issues.")
            build_overviews = True
        
        m = visualize_raster(
            file_path,
            layer_name=layer_name,
            colormap='binary',
            # build_overviews=build_overviews,
        )
    elif ext in ('geojson', 'shp'):
        m = visualize_vector(file_path, layer_name=layer_name)
    else:
        st.error(f"Unsupported file type: {ext}. Please select a valid dataset.")
        return None
    return m

def download_from_s3(bucket_name, key, download_dir):
    s3 = boto3.client('s3')
    file_path = join(download_dir, basename(key))

    # Check if the file already exists and is not older than 24 hours
    # If the file does not exist or is older than 24 hours, download it
    if not exists(file_path) or getmtime(file_path) < datetime.now().timestamp() - 24 * 3600:
        print(f"Downloading from S3: {key}")
        s3.download_file(bucket_name, key, file_path)
        print(f"File downloaded to: {file_path}")
    return file_path

def list_folders(bucket_name, prefix):
    """Lists all folders within a given prefix in an S3 bucket."""
    folders = set()
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
    for page in pages:
        for prefix_data in page.get('CommonPrefixes', []):
            folders.add(prefix_data.get('Prefix').split('/')[-2])
    return folders
