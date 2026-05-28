import geopandas as gpd
import pandas as pd
import numpy as np
import os
import glob


# =========================================================
# 1. AUTO READ SPATIAL
# =========================================================

def read_spatial(path):

    path_lower = path.lower()

    if path_lower.endswith(".geojson"):

        return gpd.read_file(path)

    elif path_lower.endswith(".gpkg"):

        return gpd.read_file(path)

    elif path_lower.endswith(".shp"):

        return gpd.read_file(path)

    else:

        raise ValueError(
            f"Format tidak didukung: {path}"
        )


# =========================================================
# 2. AUTO READ CSV
# =========================================================

def read_csv_auto(path):

    return pd.read_csv(
        path,
        sep=None,
        engine="python",
        encoding_errors="ignore",
        on_bad_lines="skip",
        dtype=str
    )


# =========================================================
# 3. CLEAN GEOMETRY
# =========================================================

def clean_geometry_columns(gdf):

    geometry_cols = []

    active_geometry = gdf.geometry.name

    for col in gdf.columns:

        if col == active_geometry:
            continue

        try:

            if hasattr(gdf[col], "geom_type"):

                geometry_cols.append(col)

        except:
            pass

    if len(geometry_cols) > 0:

        gdf = gdf.drop(
            columns=geometry_cols,
            errors="ignore"
        )

    return gdf


# =========================================================
# 4. STANDARDIZE COLUMNS
# =========================================================

def standardize_columns(df):

    # ============================================
    # LOWERCASE COLUMNS
    # ============================================

    df.columns = [
        str(c).lower()
        for c in df.columns
    ]

    # ============================================
    # CHARACTER COLUMNS
    # ============================================

    char_cols = [

        "idsubsls",
        "idsubsls_261",
        "idsubsls_origin",

        "kdprov",
        "nmprov",

        "kdkab",
        "nmkab",

        "kdkec",
        "nmkec",

        "kddesa",
        "nmdesa",

        "idsls",
        "nmsls",

        "id_assignment",
        "unique_bang"

    ]

    for col in char_cols:

        if col in df.columns:

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.replace("nan", "", regex=False)
                .str.replace("None", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.strip()
            )

    # ============================================
    # ZERO PADDING
    # ============================================

    if "kdprov" in df.columns:

        df["kdprov"] = (
            df["kdprov"]
            .str.zfill(2)
        )

    if "kdkab" in df.columns:

        df["kdkab"] = (
            df["kdkab"]
            .str.zfill(2)
        )

    if "kdkec" in df.columns:

        df["kdkec"] = (
            df["kdkec"]
            .str.zfill(3)
        )

    if "kddesa" in df.columns:

        df["kddesa"] = (
            df["kddesa"]
            .str.zfill(3)
        )

    # ============================================
    # INTEGER COLUMNS
    # ============================================

    int_cols = [

        "flag_position",
        "no_bang",
        "kode_bang_value",

        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    for col in int_cols:

        if col in df.columns:

            df[col] = (
                pd.to_numeric(
                    df[col],
                    errors="coerce"
                )
                .fillna(0)
                .astype("int64")
            )

    # ============================================
    # FLOAT COLUMNS
    # ============================================

    float_cols = [

        "latitude_origin",
        "longitude_origin",

        "latitude_edited",
        "longitude_edited"

    ]

    for col in float_cols:

        if col in df.columns:

            df[col] = (
                pd.to_numeric(
                    df[col],
                    errors="coerce"
                )
                .astype(float)
            )
    
    return df


# =========================================================
# 5. READ & MERGE GEOTAGGING
# =========================================================

def read_merge_geotagging(
    folder_path,
    idkab
):

    files = glob.glob(
        os.path.join(
            folder_path,
            "*.geojson"
        )
    )

    files = [
        f for f in files
        if (
            "geotagging"
            in
            os.path.basename(f).lower()
        )
        and
        (
            os.path.basename(f).startswith(
                str(idkab)
            )
        )
    ]

    print(f"Total file geotagging: {len(files)}")

    if len(files) == 0:

        raise ValueError(
            f"Tidak ada file geotagging untuk idkab {idkab}"
        )

    gdfs = []

    for path in files:

        try:

            print(
                f"Loading: {os.path.basename(path)}"
            )

            gdf = gpd.read_file(path)

            gdf = clean_geometry_columns(
                gdf
            )

            gdf = standardize_columns(
                gdf
            )

            gdfs.append(gdf)

        except Exception as e:

            print(
                f"ERROR {os.path.basename(path)}: {e}"
            )

    if len(gdfs) == 0:

        raise ValueError(
            "Tidak ada geotagging berhasil dibaca"
        )

    merged = pd.concat(
        gdfs,
        ignore_index=True
    )

    merged = gpd.GeoDataFrame(
        merged,
        geometry="geometry",
        crs="EPSG:4326"
    )

    print(
        f"Total records: {len(merged)}"
    )

    return merged


# =========================================================
# 6. OVERLAY WILKERSTAT
# =========================================================

def overlay_wilkerstat(
    gdf_titik,
    gdf_wilker
):

    print("Overlay wilkerstat ...")

    gdf_wilker = gdf_wilker.to_crs(
        gdf_titik.crs
    )

    gdf_wilker = standardize_columns(
        gdf_wilker
    )

    if "idsubsls" in gdf_wilker.columns:

        gdf_wilker = gdf_wilker.rename(columns={
            "idsubsls": "idsubsls_261"
        })

    cols_wilker = [
        "idsubsls_261",
        "geometry"
    ]

    cols_exist = [
        c for c in cols_wilker
        if c in gdf_wilker.columns
    ]

    joined = gpd.sjoin(
        gdf_titik,
        gdf_wilker[cols_exist],
        how="left",
        predicate="intersects"
    )

    print(
        "NULL IDSUBSLS:",
        joined["idsubsls_261"]
        .isna()
        .sum()
    )

    joined = standardize_columns(
        joined
    )

    return joined


# =========================================================
# 7. SAVE OUTPUT GS
# =========================================================

def save_output_gs(
    gdf,
    output_path
):

    gdf = clean_geometry_columns(
        gdf
    )

    gdf.to_file(
        output_path,
        driver="GeoJSON"
    )

    print(f"Saved GS: {output_path}")


# =========================================================
# 8. AGGREGATE BANGUNAN
# =========================================================

def aggregate_bangunan(df):

    agg = (
        df
        .groupby("unique_bang")
        .agg({

            "idsubsls_261": "first",

            "kk": "sum",
            "btt": "min",
            "bttk": "max",
            "bku": "sum",
            "bbtt_nonusaha": "max",
            "usaha": "sum"

        })
        .reset_index()
    )

    agg = standardize_columns(
        agg
    )

    return agg


# =========================================================
# 9. AGGREGATE SUBSLS
# =========================================================

def aggregate_subsls(df):

    agg = (
        df
        .groupby("idsubsls_261")
        .agg({

            "kk": "sum",
            "btt": "sum",
            "bttk": "sum",
            "bku": "sum",
            "bbtt_nonusaha": "sum",
            "usaha": "sum"

        })
        .reset_index()
    )

    agg = standardize_columns(
        agg
    )

    return agg


# =========================================================
# 10. JOIN MASTER SUBSLS
# =========================================================

def join_master_subsls(
    master_df,
    agg_df
):

    master_df = standardize_columns(
        master_df
    )

    agg_df = standardize_columns(
        agg_df
    )

    print("MASTER IDSUBSLS SAMPLE:")
    print(master_df["idsubsls"].head())

    print("AGG IDSUBSLS SAMPLE:")
    print(agg_df["idsubsls_261"].head())

    print("MATCH COUNT:")

    print(
        agg_df["idsubsls_261"]
        .isin(master_df["idsubsls"])
        .sum()
    )

    master_cols = [

        "idsubsls",
        "kdprov",
        "nmprov",
        "kdkab",
        "nmkab",
        "kdkec",
        "nmkec",
        "kddesa",
        "nmdesa",
        "idsls",
        "nmsls"

    ]

    master_cols = [
        c for c in master_cols
        if c in master_df.columns
    ]

    master_df = master_df[
        master_cols
    ].copy()

    agg_cols = [

        "idsubsls_261",
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    agg_cols = [
        c for c in agg_cols
        if c in agg_df.columns
    ]

    agg_df = agg_df[
        agg_cols
    ].copy()

    result = master_df.merge(
        agg_df,
        left_on="idsubsls",
        right_on="idsubsls_261",
        how="left"
    )

    numeric_cols = [
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"
    ]

    for col in numeric_cols:

        if col in result.columns:

            result[col] = (
                pd.to_numeric(
                    result[col],
                    errors="coerce"
                )
                .fillna(0)
                .astype("int64")
            )

    result = standardize_columns(
        result
    )

    return result


# =========================================================
# 11. REFACTOR MUATAN
# =========================================================

def refactor_muatan(df):

    cols = [

        "idsubsls",
        "kdprov",
        "nmprov",
        "kdkab",
        "nmkab",
        "kdkec",
        "nmkec",
        "kddesa",
        "nmdesa",
        "idsls",
        "nmsls",
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    cols = [
        c for c in cols
        if c in df.columns
    ]

    output = df[cols].copy()

    output = output.rename(columns={
        "idsubsls": "idsubsls_261"
    })

    output = standardize_columns(
        output
    )

    final_cols = [

        "idsubsls_261",
        "kdprov",
        "nmprov",
        "kdkab",
        "nmkab",
        "kdkec",
        "nmkec",
        "kddesa",
        "nmdesa",
        "idsls",
        "nmsls",
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha"

    ]

    final_cols = [
        c for c in final_cols
        if c in output.columns
    ]

    output = output[
        final_cols
    ].copy()

    return output


# =========================================================
# 12. SAVE MUATAN
# =========================================================

def save_output_muatan(
    df,
    output_path
):

    df.to_csv(
        output_path,
        index=False
    )

    print(f"Saved Muatan: {output_path}")


# =========================================================
# 13. MAIN PROCESS
# =========================================================

def proses_muatan(
    geotagging_folder,
    idkab,
    wilkerstat_261_path,
    msubsls_26_1_path,
    output_path_gs,
    output_path_muatan
):

    print("=" * 60)
    print("READ GEOTAGGING")
    print("=" * 60)

    gdf_titik = read_merge_geotagging(
        geotagging_folder,
        idkab
    )

    print("=" * 60)
    print("READ WILKERSTAT")
    print("=" * 60)

    gdf_wilker = read_spatial(
        wilkerstat_261_path
    )

    print("=" * 60)
    print("OVERLAY")
    print("=" * 60)

    joined = overlay_wilkerstat(
        gdf_titik,
        gdf_wilker
    )

    joined = standardize_columns(
        joined
    )

    print("=" * 60)
    print("PREPARE GS")
    print("=" * 60)

    gs_internal = joined.copy()

    gs_internal["unique_bang"] = (
        gs_internal["level_6_full_code"].astype(str)
        + "#"
        + (
            gs_internal["no_bang"]
            .astype(int)
            .astype(str)
            .str.zfill(4)
        )
    )

    gs_internal["flag_position"] = np.where(
        (
            gs_internal["latitude_origin"]
            ==
            gs_internal["latitude_edited"]
        )
        &
        (
            gs_internal["longitude_origin"]
            ==
            gs_internal["longitude_edited"]
        ),
        0,
        1
    )

    gs_upload = gs_internal[
        [
            "id_assignment",
            "unique_bang",
            "flag_position",
            "level_6_full_code",
            "idsubsls_261",
            "latitude_origin",
            "longitude_origin",
            "latitude_edited",
            "longitude_edited",
            "no_bang",
            "kode_bang_value",
            "kk",
            "btt",
            "bku",
            "bttk",
            "bbtt_nonusaha",
            "usaha",
            "geometry"
        ]
    ].copy()

    gs_upload = gs_upload.rename(columns={
        "level_6_full_code":
        "idsubsls_origin"
    })

    gs_upload = standardize_columns(
        gs_upload
    )

    save_output_gs(
        gs_upload,
        output_path_gs
    )

    print("=" * 60)
    print("AGGREGATE BANGUNAN")
    print("=" * 60)

    bangunan = aggregate_bangunan(
        gs_internal
    )

    print("=" * 60)
    print("AGGREGATE SUBSLS")
    print("=" * 60)

    subsls = aggregate_subsls(
        bangunan
    )

    print("=" * 60)
    print("READ MASTER SUBSLS")
    print("=" * 60)

    master_subsls = read_csv_auto(
        msubsls_26_1_path
    )

    print("=" * 60)
    print("JOIN MASTER")
    print("=" * 60)

    muatan = join_master_subsls(
        master_subsls,
        subsls
    )

    print("=" * 60)
    print("REFACTOR MUATAN")
    print("=" * 60)

    muatan = refactor_muatan(
        muatan
    )

    muatan['idsls'] = muatan['idsubsls_261'].str[:14]
    
    save_output_muatan(
        muatan,
        output_path_muatan
    )

    print("=" * 60)
    print("SELESAI")
    print("=" * 60)

    return {
        "gs_upload": gs_upload,
        "muatan": muatan
    }