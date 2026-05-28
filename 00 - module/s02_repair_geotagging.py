import geopandas as gpd
import pandas as pd
import numpy as np
import math
import os
import glob

from shapely.geometry import Point


# =========================================================
# 1. AUTO READ SPATIAL FILE
# =========================================================

def read_spatial(path,
                 latitude_col="geotag_latitude",
                 longitude_col="geotag_longitude"):

    path_lower = path.lower()

    # ============================================
    # CSV
    # ============================================

    if path_lower.endswith(".csv"):

        df = pd.read_csv(path)

        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(
                df[longitude_col],
                df[latitude_col]
            ),
            crs="EPSG:4326"
        )

        return gdf

    # ============================================
    # GEOJSON
    # ============================================

    elif path_lower.endswith(".geojson"):

        return gpd.read_file(path)

    # ============================================
    # GPKG
    # ============================================

    elif path_lower.endswith(".gpkg"):

        return gpd.read_file(path)

    # ============================================
    # SHP
    # ============================================

    elif path_lower.endswith(".shp"):

        return gpd.read_file(path)

    else:

        raise ValueError(
            f"Format tidak didukung: {path}"
        )


# =========================================================
# 2. SHIFT POINT 5 METER
# =========================================================

def shift_point_5m(base_point,
                   reference_point,
                   polygon,
                   distance=5):

    dx = reference_point.x - base_point.x
    dy = reference_point.y - base_point.y

    length = math.sqrt(dx**2 + dy**2)

    if length == 0:
        dx = 1
        dy = 0
        length = 1

    ux = dx / length
    uy = dy / length

    # ============================================
    # MAJU
    # ============================================

    new_x = reference_point.x + ux * distance
    new_y = reference_point.y + uy * distance

    candidate = Point(new_x, new_y)

    if polygon.contains(candidate):
        return candidate

    # ============================================
    # MUNDUR
    # ============================================

    new_x = reference_point.x - ux * distance
    new_y = reference_point.y - uy * distance

    candidate = Point(new_x, new_y)

    if polygon.contains(candidate):
        return candidate

    return reference_point


# =========================================================
# 3. CLEAN EXTRA GEOMETRY COLUMNS
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
# 4. FUNGSI REPAIR COORDINAT
# =========================================================

def find_repair_coordinate(row,
                           valid_points,
                           gdf_poly):

    target_subsls = str(row["level_6_full_code"])
    target_no = int(row["no_bang"])

    # ============================================
    # POLYGON TARGET
    # ============================================

    poly_match = gdf_poly[
        gdf_poly["idsubsls"].astype(str)
        == target_subsls
    ]

    if len(poly_match) == 0:

        return (
            row["geotag_latitude"],
            row["geotag_longitude"],
            "subsls_not_found"
        )

    poly = poly_match.iloc[0].geometry
    poly_proj = poly_match.iloc[0]["geometry_proj"]

    # ============================================
    # SUBSET VALID
    # ============================================

    subset = valid_points[
        valid_points["level_6_full_code"]
        .astype(str)
        == target_subsls
    ].copy()

    # ============================================
    # TIDAK ADA TITIK VALID
    # ============================================

    if len(subset) == 0:

        centroid = poly.centroid

        return (
            centroid.y,
            centroid.x,
            "polygon_centroid"
        )

    # ============================================
    # BEFORE AFTER
    # ============================================

    before = subset[
        subset["no_bang"].astype(int)
        < target_no
    ].sort_values("no_bang", ascending=False)

    after = subset[
        subset["no_bang"].astype(int)
        > target_no
    ].sort_values("no_bang", ascending=True)

    before_pt = before.iloc[0] if len(before) > 0 else None
    after_pt = after.iloc[0] if len(after) > 0 else None

    # ============================================
    # INTERPOLASI
    # ============================================

    if before_pt is not None and after_pt is not None:

        lat = (
            before_pt["geotag_latitude"]
            + after_pt["geotag_latitude"]
        ) / 2

        lon = (
            before_pt["geotag_longitude"]
            + after_pt["geotag_longitude"]
        ) / 2

        candidate = Point(lon, lat)

        if poly.contains(candidate):

            return (
                lat,
                lon,
                "interpolated"
            )

        centroid = poly.centroid

        return (
            centroid.y,
            centroid.x,
            "fallback_centroid"
        )

    # ============================================
    # HANYA BEFORE
    # ============================================

    elif before_pt is not None:

        ref_point = before_pt.geometry_proj

        before2 = subset[
            subset["no_bang"].astype(int)
            < int(before_pt["no_bang"])
        ].sort_values("no_bang", ascending=False)

        if len(before2) > 0:
            base_point = before2.iloc[0].geometry_proj
        else:
            base_point = poly_proj.centroid

        shifted = shift_point_5m(
            base_point,
            ref_point,
            poly_proj,
            distance=5
        )

        shifted_geom = gpd.GeoSeries(
            [shifted],
            crs=3857
        ).to_crs(4326).iloc[0]

        return (
            shifted_geom.y,
            shifted_geom.x,
            "shift_after_last"
        )

    # ============================================
    # HANYA AFTER
    # ============================================

    elif after_pt is not None:

        ref_point = after_pt.geometry_proj

        after2 = subset[
            subset["no_bang"].astype(int)
            > int(after_pt["no_bang"])
        ].sort_values("no_bang", ascending=True)

        if len(after2) > 0:
            base_point = after2.iloc[0].geometry_proj
        else:
            base_point = poly_proj.centroid

        shifted = shift_point_5m(
            base_point,
            ref_point,
            poly_proj,
            distance=5
        )

        shifted_geom = gpd.GeoSeries(
            [shifted],
            crs=3857
        ).to_crs(4326).iloc[0]

        return (
            shifted_geom.y,
            shifted_geom.x,
            "shift_before_first"
        )

    # ============================================
    # FINAL FALLBACK
    # ============================================

    centroid = poly.centroid

    return (
        centroid.y,
        centroid.x,
        "final_fallback"
    )


# =========================================================
# 5. MAIN FUNCTION
# =========================================================

def repair_geotagging(path_polygon,
                      path_geotagging):

    print("Membaca data ...")

    gdf_poly = read_spatial(path_polygon)
    gdf_point = read_spatial(path_geotagging)

    # ============================================
    # CRS
    # ============================================

    gdf_poly = gdf_poly.to_crs(gdf_point.crs)

    # ============================================
    # SPATIAL JOIN
    # ============================================

    print("Spatial join ...")

    joined = gpd.sjoin(
        gdf_point,
        gdf_poly,
        how="left",
        predicate="within"
    )

    joined = joined.rename(columns={
        "idsubsls": "idsubsls_overlay"
    })

    # ============================================
    # FLAG REPAIR
    # ============================================

    joined["flag_repair"] = np.where(
        joined["idsubsls_overlay"].astype(str)
        ==
        joined["level_6_full_code"].astype(str),
        0,
        1
    )

    # ============================================
    # UNIQUE BANG
    # ============================================

    joined["no_bang_str"] = (
        joined["no_bang"]
        .astype(int)
        .astype(str)
        .str.zfill(4)
    )

    joined["unique_bang"] = (
        joined["level_6_full_code"].astype(str)
        + "#"
        + joined["no_bang_str"]
    )

    # ============================================
    # MEDIAN KOORDINAT
    # ============================================

    median_coord = (
        joined
        .groupby("unique_bang")
        .agg({
            "geotag_latitude": "median",
            "geotag_longitude": "median"
        })
        .reset_index()
        .rename(columns={
            "geotag_latitude": "latitude_edited",
            "geotag_longitude": "longitude_edited"
        })
    )

    joined = joined.merge(
        median_coord,
        on="unique_bang",
        how="left"
    )

    joined["repair_status"] = "original"

    # ============================================
    # PROJECT TO METER
    # ============================================

    gdf_point_proj = joined.to_crs(3857)
    gdf_poly_proj = gdf_poly.to_crs(3857)

    joined["geometry_proj"] = gdf_point_proj.geometry.values
    gdf_poly["geometry_proj"] = gdf_poly_proj.geometry.values

    # ============================================
    # VALID POINTS
    # ============================================

    valid_points = joined[
        joined["flag_repair"] == 0
    ].copy()

    # ============================================
    # REPAIR
    # ============================================

    print("Repair titik ...")

    repair_idx = joined["flag_repair"] == 1

    for idx, row in joined[repair_idx].iterrows():

        lat_new, lon_new, status = find_repair_coordinate(
            row,
            valid_points,
            gdf_poly
        )

        joined.at[idx, "latitude_edited"] = lat_new
        joined.at[idx, "longitude_edited"] = lon_new
        joined.at[idx, "repair_status"] = status

    # ============================================
    # GEOMETRY BARU
    # ============================================

    joined["geometry"] = gpd.points_from_xy(
        joined["longitude_edited"],
        joined["latitude_edited"]
    )

    gdf_result = gpd.GeoDataFrame(
        joined,
        geometry="geometry",
        crs="EPSG:4326"
    )

    # ============================================
    # CLEAN EXTRA GEOMETRY
    # ============================================

    gdf_result = clean_geometry_columns(
        gdf_result
    )

    # ============================================
    # AUTO SAVE
    # ============================================

    iddesa = os.path.basename(
        path_geotagging
    ).split("_")[0]

    folder_output = "01 - data/03-geotagging-edited"

    os.makedirs(folder_output, exist_ok=True)

    path_output = os.path.join(
        folder_output,
        f"{iddesa}_geotagging_edited.geojson"
    )

    gdf_result.to_file(
        path_output,
        driver="GeoJSON"
    )

    print(f"Output saved: {path_output}")

    print("Selesai")

    return gdf_result


# =========================================================
# 6. REFACTOR FIELDS FUNCTION
# =========================================================

def refactor_fields(joined):

    joined["flag_repair_sls"] = np.where(
        joined["idsls"].astype(str)
        ==
        joined["level_5_full_code"].astype(str),
        0,
        1
    )

    joined["latitude_origin"] = joined["geotag_latitude"]
    joined["longitude_origin"] = joined["geotag_longitude"]

    joined["kk"] = np.where(
        joined["ec_keluarga"]
        .astype(str)
        .str.lower() == "true",
        1,
        0
    )

    joined["btt"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        .isin([2, 3]),
        1,
        0
    )

    joined["bttk"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        == 11,
        1,
        0
    )

    joined["bku"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        == 1,
        1,
        0
    )

    joined["bbtt_nonusaha"] = np.where(
        pd.to_numeric(
            joined["kode_bang_value"],
            errors="coerce"
        ).fillna(0).astype(int)
        .isin([4, 5, 6]),
        1,
        0
    )

    joined["usaha"] = pd.to_numeric(
        joined["jumlah_usaha_ditemukan"],
        errors="coerce"
    ).fillna(0).astype(int)

    if "idsubsls_overlay" in joined.columns:

        joined = joined.rename(columns={
            "idsubsls_overlay": "idsubsls"
        })

    final_columns = [
        "id_assignment",
        "flag_repair",
        "flag_repair_sls",
        "level_6_full_code",
        "idsubsls",
        "latitude_origin",
        "longitude_origin",
        "latitude_edited",
        "longitude_edited",
        "repair_status",
        "no_bang",
        "kode_bang_value",
        "ec_keluarga",
        "jumlah_usaha_ditemukan",
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
        "level_5_full_code",
        "sls",
        "kk",
        "btt",
        "bttk",
        "bku",
        "bbtt_nonusaha",
        "usaha",
        "geometry"
    ]

    final_columns = [
        c for c in final_columns
        if c in joined.columns
    ]

    joined = joined[final_columns]

    joined = clean_geometry_columns(
        joined
    )

    return joined


# =========================================================
# 7. BATCH PROCESSING
# =========================================================

def batch_repair_geotagging(
    folder_polygon="01 - data/01-peta-251",
    folder_geotagging="01 - data/02-geotagging"
):

    list_geotagging = glob.glob(
        os.path.join(
            folder_geotagging,
            "*_geotagging.geojson"
        )
    )

    print("=" * 60)
    print(f"TOTAL DESA : {len(list_geotagging)}")
    print("=" * 60)

    success = []
    failed = []

    for i, path_geo in enumerate(list_geotagging):

        try:

            filename = os.path.basename(path_geo)

            iddesa = filename.split("_")[0]

            print("\n")
            print("=" * 60)
            print(f"[{i+1}/{len(list_geotagging)}] PROCESSING {iddesa}")
            print("=" * 60)

            path_polygon = os.path.join(
                folder_polygon,
                f"final_sls_251_{iddesa}.geojson"
            )

            # ============================================
            # CHECK POLYGON
            # ============================================

            if not os.path.exists(path_polygon):

                print(f"Polygon tidak ditemukan")

                failed.append({
                    "iddesa": iddesa,
                    "status": "polygon_not_found"
                })

                continue

            # ============================================
            # REPAIR
            # ============================================

            result = repair_geotagging(
                path_polygon=path_polygon,
                path_geotagging=path_geo
            )

            # ============================================
            # REFACTOR
            # ============================================

            result = refactor_fields(result)

            result = clean_geometry_columns(
                result
            )

            # ============================================
            # OUTPUT
            # ============================================

            folder_output = "01 - data/03-geotagging-edited"

            os.makedirs(folder_output, exist_ok=True)

            path_output = os.path.join(
                folder_output,
                f"{iddesa}_geotagging_edited.geojson"
            )

            # ============================================
            # SAVE
            # ============================================

            result.to_file(
                path_output,
                driver="GeoJSON"
            )

            print(f"Saved: {path_output}")

            success.append({
                "iddesa": iddesa,
                "status": "success"
            })

        except Exception as e:

            print(f"ERROR {iddesa}: {e}")

            failed.append({
                "iddesa": iddesa,
                "status": str(e)
            })

    print("\n")
    print("=" * 60)
    print("SELESAI")
    print("=" * 60)
    print(f"SUCCESS : {len(success)}")
    print(f"FAILED  : {len(failed)}")

    return {
        "success": pd.DataFrame(success),
        "failed": pd.DataFrame(failed)
    }