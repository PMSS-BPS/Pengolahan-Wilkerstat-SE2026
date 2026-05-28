import os
import warnings
import zipfile

import geopandas as gpd
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")


# =========================================================
# AUTO READ FILE
# =========================================================
def read_spatial_file(path):

    ext = os.path.splitext(path)[1].lower()

    # spatial
    if ext in [".shp", ".geojson", ".gpkg"]:

        return gpd.read_file(path)

    # csv
    elif ext == ".csv":

        df = pd.read_csv(path)

        # geometry WKT
        if "geometry" in df.columns:

            return gpd.GeoDataFrame(
                df,
                geometry=gpd.GeoSeries.from_wkt(
                    df["geometry"]
                ),
                crs="EPSG:4326"
            )

        # longitude latitude
        elif {"longitude", "latitude"}.issubset(df.columns):

            return gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(
                    df["longitude"],
                    df["latitude"]
                ),
                crs="EPSG:4326"
            )

        elif {"lon", "lat"}.issubset(df.columns):

            return gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(
                    df["lon"],
                    df["lat"]
                ),
                crs="EPSG:4326"
            )

        else:

            raise ValueError(
                "CSV tidak punya geometry/lon/lat"
            )

    else:

        raise ValueError(
            f"Format file tidak didukung: {ext}"
        )


# =========================================================
# TEMPLATE PEMBAGIAN PETUGAS
# =========================================================
def create_template_petugas(
    geotagging_gdf,
    peta_gdf,
    jumlah_petugas,
    output_excel,
    output_geojson=None,
    output_png=None,
    geotagging_id_col="level_6_full_code",
    peta_id_col="idsubsls",
    nmdesa_col="nmdesa",
    underload_tolerance=0.90,
    overload_tolerance=1.10,
    weight_geotag=0.8,
    weight_subsls=0.2
):

    # =====================================================
    # STANDARDISASI ID
    # =====================================================
    geotagging_gdf[geotagging_id_col] = (
        geotagging_gdf[geotagging_id_col]
        .astype(str)
        .str.strip()
    )

    peta_gdf[peta_id_col] = (
        peta_gdf[peta_id_col]
        .astype(str)
        .str.strip()
    )

    geotagging_gdf["iddesa"] = (
        geotagging_gdf[
            geotagging_id_col
        ].str[:10]
    )

    peta_gdf["iddesa"] = (
        peta_gdf[
            peta_id_col
        ].str[:10]
    )

    # =====================================================
    # VALIDASI KOLOM NAMA DESA
    # =====================================================
    if nmdesa_col not in peta_gdf.columns:

        kandidat = [
            "nmdesa",
            "NMDESA",
            "nm_desa",
            "nama_desa",
            "NAMOBJ"
        ]

        ditemukan = None

        for col in kandidat:

            if col in peta_gdf.columns:

                ditemukan = col
                break

        if ditemukan is None:

            raise ValueError(
                f"Kolom nama desa tidak ditemukan.\n"
                f"{peta_gdf.columns.tolist()}"
            )

        else:

            nmdesa_col = ditemukan

    # =====================================================
    # JUMLAH GEOTAG
    # =====================================================
    jumlah_geotag = (
        geotagging_gdf
        .groupby("iddesa")
        .size()
        .reset_index(name="jumlah_geotag")
    )

    # =====================================================
    # JUMLAH SUBSLS
    # =====================================================
    jumlah_subsls = (
        peta_gdf
        .groupby("iddesa")
        .size()
        .reset_index(name="jumlah_subsls")
    )

    # =====================================================
    # NAMA DESA
    # =====================================================
    nmdesa = (
        peta_gdf
        .groupby("iddesa")[nmdesa_col]
        .first()
        .reset_index()
    )

    # =====================================================
    # DISSOLVE DESA
    # =====================================================
    desa_gdf = (
        peta_gdf
        .dissolve(
            by="iddesa",
            as_index=False
        )
    )

    # =====================================================
    # AMBIL GEOMETRY SAJA
    # =====================================================
    drop_cols = [
        col for col in desa_gdf.columns
        if col not in ["iddesa", "geometry"]
    ]

    desa_gdf = desa_gdf.drop(
        columns=drop_cols,
        errors="ignore"
    )

    # =====================================================
    # UNION IDDESA
    # =====================================================
    iddesa_union = sorted(
        set(peta_gdf["iddesa"])
        .union(set(geotagging_gdf["iddesa"]))
    )

    template = pd.DataFrame({
        "iddesa": iddesa_union
    })

    # indikator
    template["iddesa_peta"] = np.where(
        template["iddesa"].isin(
            peta_gdf["iddesa"]
        ),
        template["iddesa"],
        None
    )

    template["iddesa_geotag"] = np.where(
        template["iddesa"].isin(
            geotagging_gdf["iddesa"]
        ),
        template["iddesa"],
        None
    )

    # =====================================================
    # MERGE ATRIBUT
    # =====================================================
    template = template.merge(
        nmdesa,
        on="iddesa",
        how="left"
    )

    template = template.merge(
        jumlah_geotag,
        on="iddesa",
        how="left"
    )

    template = template.merge(
        jumlah_subsls,
        on="iddesa",
        how="left"
    )

    # =====================================================
    # FILL NULL
    # =====================================================
    template["jumlah_geotag"] = (
        template["jumlah_geotag"]
        .fillna(0)
        .astype(int)
    )

    template["jumlah_subsls"] = (
        template["jumlah_subsls"]
        .fillna(0)
        .astype(int)
    )

    # =====================================================
    # MERGE GEOMETRY
    # =====================================================
    desa_template = desa_gdf.merge(
        template,
        on="iddesa",
        how="right"
    )

    # =====================================================
    # CRS METRIC
    # =====================================================
    desa_template = desa_template.to_crs(
        3857
    )

    # =====================================================
    # CENTROID
    # =====================================================
    desa_template["cx"] = (
        desa_template.geometry.centroid.x
    )

    desa_template["cy"] = (
        desa_template.geometry.centroid.y
    )

    # =====================================================
    # NORMALISASI
    # =====================================================
    desa_template["geotag_norm"] = (
        desa_template["jumlah_geotag"]
        /
        desa_template["jumlah_geotag"].max()
    )

    desa_template["subsls_norm"] = (
        desa_template["jumlah_subsls"]
        /
        desa_template["jumlah_subsls"].max()
    )

    # =====================================================
    # BEBAN FINAL
    # =====================================================
    desa_template["beban"] = (
        desa_template["geotag_norm"] * weight_geotag
        +
        desa_template["subsls_norm"] * weight_subsls
    )

    # =====================================================
    # TARGET IDEAL
    # =====================================================
    target_beban = (
        desa_template["beban"].sum()
        /
        jumlah_petugas
    )

    min_target = (
        target_beban
        * underload_tolerance
    )

    max_target = (
        target_beban
        * overload_tolerance
    )

    # =====================================================
    # SORT SPASIAL
    # =====================================================
    desa_template = desa_template.sort_values(
        "cy",
        ascending=False
    ).reset_index(drop=True)

    # =====================================================
    # ADJACENCY
    # =====================================================
    adjacency = {}

    for idx, row in desa_template.iterrows():

        touching = desa_template[
            desa_template.geometry.touches(
                row.geometry
            )
        ].index.tolist()

        adjacency[idx] = touching

    # =====================================================
    # SEED AWAL
    # =====================================================
    seed_idx = np.linspace(
        0,
        len(desa_template) - 1,
        jumlah_petugas,
        dtype=int
    )

    desa_template["nomor_petugas"] = -1

    beban_petugas = {
        i + 1: 0
        for i in range(jumlah_petugas)
    }

    frontier = {}

    # assign seed
    for i, idx in enumerate(seed_idx):

        petugas = i + 1

        desa_template.loc[
            idx,
            "nomor_petugas"
        ] = petugas

        frontier[petugas] = set(
            adjacency[idx]
        )

        beban_petugas[petugas] += (
            desa_template.loc[
                idx,
                "beban"
            ]
        )

    # =====================================================
    # UNASSIGNED
    # =====================================================
    unassigned = set(
        desa_template.index[
            desa_template["nomor_petugas"] == -1
        ]
    )

    # =====================================================
    # REGION GROWING
    # =====================================================
    while len(unassigned) > 0:

        underloaded = [
            p for p in beban_petugas
            if beban_petugas[p] < min_target
        ]

        if len(underloaded) > 0:

            urutan_petugas = sorted(
                underloaded,
                key=lambda x: beban_petugas[x]
            )

        else:

            urutan_petugas = sorted(
                beban_petugas,
                key=lambda x: beban_petugas[x]
            )

        assigned = False

        for petugas in urutan_petugas:

            kandidat = list(
                frontier[petugas]
                .intersection(unassigned)
            )

            if len(kandidat) == 0:
                continue

            kandidat_df = desa_template.loc[
                kandidat
            ].copy()

            cluster_geom = desa_template[
                desa_template["nomor_petugas"]
                == petugas
            ]

            cx = cluster_geom["cx"].mean()
            cy = cluster_geom["cy"].mean()

            kandidat_df["distance"] = np.sqrt(
                (kandidat_df["cx"] - cx) ** 2
                +
                (kandidat_df["cy"] - cy) ** 2
            )

            if kandidat_df["distance"].max() > 0:

                kandidat_df["distance_norm"] = (
                    kandidat_df["distance"]
                    /
                    kandidat_df["distance"].max()
                )

            else:

                kandidat_df["distance_norm"] = 0

            current_beban = (
                beban_petugas[petugas]
            )

            if current_beban >= max_target:

                continue

            overload_penalty = (
                current_beban
                / target_beban
            )

            kandidat_df["score"] = (
                kandidat_df["distance_norm"] * 0.45
                +
                kandidat_df["beban"] * 0.15
                +
                overload_penalty * 0.40
            )

            kandidat_df = kandidat_df.sort_values(
                "score"
            )

            chosen = kandidat_df.index[0]

            desa_template.loc[
                chosen,
                "nomor_petugas"
            ] = petugas

            unassigned.remove(chosen)

            frontier[petugas].update(
                adjacency[chosen]
            )

            beban_petugas[petugas] += (
                desa_template.loc[
                    chosen,
                    "beban"
                ]
            )

            assigned = True

            break

        # fallback
        if not assigned:

            chosen = list(unassigned)[0]

            petugas = min(
                beban_petugas,
                key=beban_petugas.get
            )

            desa_template.loc[
                chosen,
                "nomor_petugas"
            ] = petugas

            unassigned.remove(chosen)

            beban_petugas[petugas] += (
                desa_template.loc[
                    chosen,
                    "beban"
                ]
            )

    # =====================================================
    # NAMA PETUGAS
    # =====================================================
    desa_template["nama_petugas"] = ""

    # =====================================================
    # FINAL KOLOM
    # =====================================================
    final_cols = [
        "iddesa_peta",
        "iddesa_geotag",
        "iddesa",
        "nmdesa",
        "jumlah_geotag",
        "jumlah_subsls",
        "nomor_petugas",
        "nama_petugas",
        "geometry"
    ]

    desa_template = desa_template[
        final_cols
    ]

    # =====================================================
    # SUMMARY
    # =====================================================
    summary = (
        desa_template
        .groupby("nomor_petugas")
        .agg(
            jumlah_desa=(
                "iddesa",
                "count"
            ),
            jumlah_geotag=(
                "jumlah_geotag",
                "sum"
            ),
            jumlah_subsls=(
                "jumlah_subsls",
                "sum"
            )
        )
        .reset_index()
    )

    print(summary)

    # =====================================================
    # SAVE EXCEL
    # =====================================================
    excel_df = desa_template.drop(
        columns="geometry"
    )

    excel_df.to_excel(
        output_excel,
        index=False
    )

    # =====================================================
    # SAVE GEOJSON
    # =====================================================
    if output_geojson:

        desa_template.to_crs(4326).to_file(
            output_geojson,
            driver="GeoJSON"
        )

    # =====================================================
    # SAVE PNG
    # =====================================================
    if output_png:

        fig, ax = plt.subplots(
            figsize=(14, 14)
        )

        desa_template.plot(
            column="nomor_petugas",
            categorical=True,
            legend=True,
            linewidth=0.5,
            edgecolor="black",
            ax=ax
        )

        ax.set_axis_off()

        plt.tight_layout()

        plt.savefig(
            output_png,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close()

    return desa_template, summary


# =========================================================
# ZIP PER PETUGAS
# =========================================================
def zip_per_petugas(
    template_excel_path,
    geotagging_dir,
    peta_dir,
    output_zip_dir
):

    os.makedirs(
        output_zip_dir,
        exist_ok=True
    )

    df = pd.read_excel(
        template_excel_path
    )

    for nomor_petugas, group in (
        df.groupby("nomor_petugas")
    ):

        zip_path = os.path.join(
            output_zip_dir,
            f"petugas_{nomor_petugas}.zip"
        )

        with zipfile.ZipFile(
            zip_path,
            "w",
            compression=zipfile.ZIP_DEFLATED
        ) as zipf:

            for _, row in group.iterrows():

                iddesa = str(row["iddesa"])

                # =====================================
                # GEOTAGGING
                # =====================================
                geotag_file = (
                    f"{iddesa}_geotagging.geojson"
                )

                geotag_path = os.path.join(
                    geotagging_dir,
                    geotag_file
                )

                if os.path.exists(
                    geotag_path
                ):

                    zipf.write(
                        geotag_path,
                        arcname=os.path.join(
                            "geotagging",
                            geotag_file
                        )
                    )

                # =====================================
                # PETA
                # =====================================
                peta_file = (
                    f"final_sls_251_{iddesa}.geojson"
                )

                peta_path = os.path.join(
                    peta_dir,
                    peta_file
                )

                if os.path.exists(
                    peta_path
                ):

                    zipf.write(
                        peta_path,
                        arcname=os.path.join(
                            "peta",
                            peta_file
                        )
                    )


# =========================================================
# SPLIT DATA
# =========================================================
def split_data(
    geotagging_path,
    peta_path,
    output_geotagging_dir,
    output_peta_dir,
    output_zip_dir,
    jumlah_petugas,
    output_template_excel,
    output_template_geojson=None,
    output_template_png=None,
    geotagging_id_col="level_6_full_code",
    peta_id_col="idsubsls",
    nmdesa_col="nmdesa",
    underload_tolerance=0.90,
    overload_tolerance=1.10,
    weight_geotag=0.8,
    weight_subsls=0.2
):

    # folder
    os.makedirs(
        output_geotagging_dir,
        exist_ok=True
    )

    os.makedirs(
        output_peta_dir,
        exist_ok=True
    )

    os.makedirs(
        output_zip_dir,
        exist_ok=True
    )

    # read
    gdf_geotagging = read_spatial_file(
        geotagging_path
    )

    gdf_peta = read_spatial_file(
        peta_path
    )

    # iddesa
    gdf_geotagging["iddesa"] = (
        gdf_geotagging[
            geotagging_id_col
        ].astype(str).str[:10]
    )

    gdf_peta["iddesa"] = (
        gdf_peta[
            peta_id_col
        ].astype(str).str[:10]
    )

    # =====================================================
    # TEMPLATE
    # =====================================================
    desa_template, summary = create_template_petugas(
        geotagging_gdf=gdf_geotagging,
        peta_gdf=gdf_peta,
        jumlah_petugas=jumlah_petugas,
        output_excel=output_template_excel,
        output_geojson=output_template_geojson,
        output_png=output_template_png,
        geotagging_id_col=geotagging_id_col,
        peta_id_col=peta_id_col,
        nmdesa_col=nmdesa_col,
        underload_tolerance=underload_tolerance,
        overload_tolerance=overload_tolerance,
        weight_geotag=weight_geotag,
        weight_subsls=weight_subsls
    )

    # =====================================================
    # SPLIT GEOTAGGING
    # =====================================================
    for iddesa, group in (
        gdf_geotagging.groupby("iddesa")
    ):

        output_file = os.path.join(
            output_geotagging_dir,
            f"{iddesa}_geotagging.geojson"
        )

        group.to_file(
            output_file,
            driver="GeoJSON"
        )

    # =====================================================
    # SPLIT PETA
    # =====================================================
    for iddesa, group in (
        gdf_peta.groupby("iddesa")
    ):

        output_file = os.path.join(
            output_peta_dir,
            f"final_sls_251_{iddesa}.geojson"
        )

        group.to_file(
            output_file,
            driver="GeoJSON"
        )

    # =====================================================
    # ZIP PER PETUGAS
    # =====================================================
    zip_per_petugas(
        template_excel_path=output_template_excel,
        geotagging_dir=output_geotagging_dir,
        peta_dir=output_peta_dir,
        output_zip_dir=output_zip_dir
    )

    return desa_template, summary