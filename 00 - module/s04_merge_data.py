import os
import glob

import pandas as pd
import geopandas as gpd


# =========================================================
# MERGE HASIL EDIT PETUGAS
# =========================================================
def merge_hasil_petugas(
    geotagging_edited_dir,
    peta_edited_dir,
    output_dir,
    idkab
):
    """
    Menggabungkan seluruh hasil edit petugas
    menjadi satu file kabupaten.

    Parameters
    ----------
    geotagging_edited_dir : str
        Folder hasil edit geotagging petugas

    peta_edited_dir : str
        Folder hasil edit peta petugas

    output_dir : str
        Folder output hasil merge

    idkab : str
        ID Kabupaten/Kota
    """

    # =====================================================
    # CREATE OUTPUT DIR
    # =====================================================
    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # =====================================================
    # MERGE GEOTAGGING
    # =====================================================
    geotagging_files = glob.glob(
        os.path.join(
            geotagging_edited_dir,
            "*.geojson"
        )
    )

    geotagging_list = []

    for file in geotagging_files:

        try:

            gdf = gpd.read_file(file)

            geotagging_list.append(gdf)

        except Exception as e:

            print(
                f"Gagal membaca geotagging:\n{file}\n{e}"
            )

    if len(geotagging_list) > 0:

        merged_geotagging = pd.concat(
            geotagging_list,
            ignore_index=True
        )

        merged_geotagging = gpd.GeoDataFrame(
            merged_geotagging,
            geometry="geometry",
            crs=geotagging_list[0].crs
        )

        geotagging_output = os.path.join(
            output_dir,
            f"{idkab}_landmark.geojson"
        )

        merged_geotagging.to_file(
            geotagging_output,
            driver="GeoJSON"
        )

        print(
            f"Geotagging merged:\n{geotagging_output}"
        )

    else:

        print(
            "Tidak ada file geotagging ditemukan"
        )

    # =====================================================
    # MERGE PETA
    # =====================================================
    peta_files = glob.glob(
        os.path.join(
            peta_edited_dir,
            "*.geojson"
        )
    )

    peta_list = []

    for file in peta_files:

        try:

            gdf = gpd.read_file(file)

            peta_list.append(gdf)

        except Exception as e:

            print(
                f"Gagal membaca peta:\n{file}\n{e}"
            )

    if len(peta_list) > 0:

        merged_peta = pd.concat(
            peta_list,
            ignore_index=True
        )

        merged_peta = gpd.GeoDataFrame(
            merged_peta,
            geometry="geometry",
            crs=peta_list[0].crs
        )

        peta_output = os.path.join(
            output_dir,
            f"final_sls_251_{idkab}.geojson"
        )

        merged_peta.to_file(
            peta_output,
            driver="GeoJSON"
        )

        print(
            f"Peta merged:\n{peta_output}"
        )

    else:

        print(
            "Tidak ada file peta ditemukan"
        )