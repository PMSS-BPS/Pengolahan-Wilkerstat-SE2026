# Geotagging Repair & Muatan Pipeline

Pipeline pengolahan titik bangunan SE2026 untuk:

1. Repair geotagging titik bangunan
2. Overlay dengan peta wilkerstat 2026 semester 1
3. Pembuatan output upload Geospasial System (GS)
4. Perhitungan muatan sub-SLS

---

# Struktur Project

```bash
.
├── 00 - module/
│   ├── s02_repair_geotagging.py
│   └── s03_perhitungan_muatan.py
│
├── 01 - data/
│   ├── 01-peta-251/
│   ├── 02-geotagging/
│   ├── 03-geotagging-edited/
│   ├── 04-output-gs/
│   └── 05-output-muatan/
│
└── main.ipynb
```

---

# Workflow

Pipeline terdiri dari 2 proses utama:

1. Split & merge data untuk petugas pengolahan
2. Editing titik bangunan & perhitungan muatan

---

# 1. Split & Merge Data Petugas Pengolahan

Tahapan ini digunakan untuk:

* membagi data geotagging berdasarkan wilayah/petugas
* mendistribusikan file pengolahan
* menggabungkan kembali hasil pengolahan
* memastikan struktur field konsisten

Workflow:

```text
Raw Geotagging
        ↓
Split per wilayah/petugas
        ↓
Distribusi pengolahan
        ↓
Editing/repair titik
        ↓
Merge hasil pengolahan
        ↓
Output final geotagging
```

---

## Input Split Data

### Folder Geotagging

Berisi file titik bangunan hasil geotagging.

Contoh:

```bash
01 - data/02-geotagging/
```

Format file:

```bash
5104010001_geotagging.geojson
5104010002_geotagging.geojson
```

---

## Proses Split

Tahapan split dilakukan untuk mendukung distribusi pekerjaan pengolahan Wilkerstat hasil SE2026 secara otomatis kepada masing-masing petugas pengolahan.

Data yang digunakan terdiri atas:

1. Peta geotagging SE2026

   * titik hasil geotagging lapangan
   * memuat kode wilayah SUBSLS

2. Peta SLS/SubSLS Periode 2025 Semester 2

   * batas wilayah kerja statistik level SUBSLS

---

### Tujuan Pembagian

Pembagian dilakukan agar:

* distribusi pekerjaan lebih teratur;
* beban kerja antar petugas lebih merata;
* monitoring pengolahan lebih mudah;
* wilayah kerja antar petugas saling berdekatan atau menyambung secara spasial.

---

### Mekanisme Pembagian

Sistem melakukan pembagian wilayah kerja secara otomatis dengan mempertimbangkan:

* kedekatan spasial antar desa;
* jumlah desa;
* jumlah geotagging;
* jumlah SLS/SubSLS.

Dengan pendekatan ini:

* wilayah kerja petugas diupayakan berdekatan;
* beban pengolahan lebih seimbang;
* distribusi data lebih efisien.

---

### Parameter Pembagian

Proses bersifat fleksibel dan dapat disesuaikan dengan:

```text
jumlah petugas pengolahan Wilkerstat
```

Jumlah petugas dimasukkan sebagai parameter saat proses dijalankan.

Sistem kemudian:

1. menghitung total beban kerja;
2. membagi desa secara otomatis;
3. menetapkan nomor petugas;
4. menghasilkan pembagian wilayah kerja.

---

### Informasi Hasil Pembagian

Sistem menghasilkan template pembagian petugas yang memuat:

* nama desa;
* jumlah geotagging;
* jumlah SLS/SubSLS;
* nomor petugas.

Contoh:

| Desa   | Geotagging | SLS/SubSLS | Petugas |
| ------ | ---------- | ---------- | ------- |
| Desa A | 120        | 14         | 1       |
| Desa B | 135        | 12         | 1       |
| Desa C | 98         | 10         | 2       |

---

### Visualisasi Pembagian

Sistem juga menghasilkan visualisasi peta pembagian wilayah untuk:

* monitoring distribusi pekerjaan;
* evaluasi keseimbangan wilayah;
* validasi kedekatan spasial wilayah kerja.

Visualisasi membantu BPS Kabupaten/Kota dalam memastikan pembagian kerja lebih optimal.

---

### Output Split Data

Pada tahap akhir:

* file geotagging dipisahkan otomatis per wilayah kerja;
* file peta dipisahkan otomatis per wilayah kerja;
* seluruh file digabungkan kembali menjadi file ZIP per petugas.

Dengan mekanisme ini:

* setiap petugas langsung menerima seluruh data tanggung jawabnya;
* tidak diperlukan pemilahan manual;
* distribusi data lebih cepat dan efisien.

Contoh output:

```bash
01 - data/split-petugas/
├── petugas_01.zip
├── petugas_02.zip
├── petugas_03.zip
```

Isi masing-masing ZIP:

```bash
petugas_01/
├── geotagging/
├── peta_sls/
├── daftar_desa.xlsx
└── visualisasi_peta.png
```

---

## Output Split

Contoh struktur:

```bash
01 - data/split-petugas/
├── petugas_01/
├── petugas_02/
├── petugas_03/
```

Setiap folder berisi subset wilayah pengolahan.

---

## Proses Merge

Setelah pengolahan selesai:

* membaca seluruh hasil pengolahan
* validasi field
* standardisasi tipe data
* merge seluruh file
* menghasilkan geotagging final

Tahapan merge otomatis:

* cleaning geometry
* cleaning whitespace
* cleaning .0
* standardisasi kode wilayah
* menjaga leading zero

---

## Output Merge

Output merge:

```bash
01 - data/03-geotagging-edited/
```

Format output:

```bash
{iddesa}_geotagging_edited.geojson
```

---

# 2. Editing Titik Bangunan & Perhitungan Muatan

Tahapan utama pipeline:

1. repair titik bangunan
2. overlay wilkerstat
3. pembuatan output GS
4. agregasi bangunan
5. agregasi sub-SLS
6. perhitungan muatan

Workflow:

```text
Geotagging Edited
        ↓
Overlay Wilkerstat 261
        ↓
Penentuan IDSUBSLS_261
        ↓
Output Upload GS
        ↓
Aggregate Bangunan
        ↓
Aggregate Sub-SLS
        ↓
Join Master Sub-SLS
        ↓
Output Muatan
```

---

## Tahap Repair Titik Bangunan

Tahapan:

* membaca polygon SLS/sub-SLS
* membaca titik geotagging
* mendeteksi titik di luar polygon
* melakukan repair posisi titik
* refactor field
* menyimpan output hasil repair

Output:

```bash
01 - data/03-geotagging-edited/
```

---

## Tahap Overlay Wilkerstat

Tahapan:

* membaca peta wilkerstat 2026 semester 1
* reprojection CRS otomatis
* overlay titik dengan polygon
* mendapatkan:

```text
idsubsls_261
```

Spatial join menggunakan:

```python
predicate="intersects"
```

untuk mengurangi kegagalan overlay pada titik boundary.

---

## Tahap Output GS

Tahapan:

* membuat unique bangunan
* menentukan flag editing titik
* standardisasi tipe data
* cleaning geometry
* export GeoJSON

Output:

```bash
01 - data/04-output-gs/
```

Format:

```bash
output_gs_5104.geojson
```

---

## Tahap Aggregate Bangunan

Tahapan:

* agregasi berdasarkan unique bangunan
* perhitungan:

  * jumlah KK
  * bangunan tempat tinggal
  * bangunan kosong
  * bangunan usaha
  * jumlah usaha

---

## Tahap Aggregate Sub-SLS

Tahapan:

* agregasi seluruh bangunan
* perhitungan total muatan sub-SLS

Output sementara:

```text
idsubsls_261 level
```

---

## Tahap Join Master Sub-SLS

Tahapan:

* membaca master sub-SLS
* cleaning tipe data
* menjaga leading zero
* join berdasarkan:

```text
idsubsls_261
```

Atribut administrasi:

* kdprov
* nmprov
* kdkab
* nmkab
* kdkec
* nmkec
* kddesa
* nmdesa
* idsls
* nmsls

bersumber dari:

```text
master_subsls_26_1.csv
```

---

## Tahap Output Muatan

Output akhir:

```bash
01 - data/05-output-muatan/
```

Format:

```bash
output_muatan_5104.csv
```

---

# Requirements

Sebelum menjalankan pipeline, pastikan environment Python dan package berikut sudah terinstall.

---

## Python Version

Disarankan menggunakan:

```bash
Python >= 3.10
```

---

## Package Python

Install seluruh dependency menggunakan:

```bash
pip install geopandas pandas numpy shapely pyogrio fiona rtree jupyter openpyxl matplotlib
```

---

## Penjelasan Package

| Package    | Fungsi                              |
| ---------- | ----------------------------------- |
| geopandas  | pengolahan data spasial             |
| pandas     | manipulasi tabular data             |
| numpy      | komputasi numerik                   |
| shapely    | operasi geometry                    |
| pyogrio    | engine read/write geospatial        |
| fiona      | read/write shapefile dan geojson    |
| rtree      | spatial indexing untuk spatial join |
| jupyter    | menjalankan notebook                |
| openpyxl   | export/import excel                 |
| matplotlib | visualisasi dan plotting            |

---

## Optional Package

Untuk percepatan processing data besar:

```bash
pip install pyarrow
```

---

## Test Installation

Pastikan seluruh package berhasil terinstall:

```python
import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
import pyogrio
import fiona
```

Jika tidak muncul error, maka environment siap digunakan.

---

## Python

Minimal:

```bash
Python >= 3.10
```

---

## Library

Install dependency:

```bash
pip install geopandas pandas numpy shapely pyogrio fiona rtree
```

---

# Module

## s02_repair_geotagging.py

Module untuk repair titik geotagging.

### Function Utama

```python
batch_repair_geotagging()
```

### Contoh Penggunaan

```python
from s02_repair_geotagging import *

result = batch_repair_geotagging(
    folder_polygon="01 - data/01-peta-251",
    folder_geotagging="01 - data/02-geotagging"
)
```

---

## s03_perhitungan_muatan.py

Module untuk:

* overlay wilkerstat
* pembuatan output GS
* perhitungan muatan

### Function Utama

```python
proses_muatan()
```

---

# Contoh Penggunaan

```python
from s03_perhitungan_muatan import *

result = proses_muatan(

    geotagging_folder="01 - data/03-geotagging-edited",

    idkab="5104",

    wilkerstat_261_path="01 - data/wilkerstat_261.geojson",

    msubsls_26_1_path="01 - data/msubsls_26_1.csv",

    output_path_gs="01 - data/04-output-gs/output_gs_5104.geojson",

    output_path_muatan="01 - data/05-output-muatan/output_muatan_5104.csv"
)
```

---

# Output GS

Format output upload Geospasial System:

| Field            | Tipe    |
| ---------------- | ------- |
| id_assignment    | string  |
| unique_bang      | string  |
| flag_position    | integer |
| idsubsls_origin  | string  |
| idsubsls_261     | string  |
| latitude_origin  | double  |
| longitude_origin | double  |
| latitude_edited  | double  |
| longitude_edited | double  |
| no_bang          | integer |
| kode_bang_value  | integer |
| kk               | integer |
| btt              | integer |
| bku              | integer |
| bttk             | integer |
| bbtt_nonusaha    | integer |
| usaha            | integer |

---

# Output Muatan

Format output muatan:

| Field         | Tipe    |
| ------------- | ------- |
| idsubsls_261  | string  |
| kdprov        | string  |
| nmprov        | string  |
| kdkab         | string  |
| nmkab         | string  |
| kdkec         | string  |
| nmkec         | string  |
| kddesa        | string  |
| nmdesa        | string  |
| idsls         | string  |
| nmsls         | string  |
| kk            | integer |
| btt           | integer |
| bttk          | integer |
| bku           | integer |
| bbtt_nonusaha | integer |
| usaha         | integer |

---

# Standardisasi Data

Pipeline secara otomatis melakukan:

* lowercase nama kolom
* cleaning `.0`
* cleaning whitespace
* menjaga leading zero kode wilayah
* konversi integer
* konversi koordinat menjadi float
* cleaning geometry column

Contoh:

| Variabel | Format |
| -------- | ------ |
| kdprov   | 51     |
| kdkab    | 04     |
| kdkec    | 001    |
| kddesa   | 010    |

---

# Spatial Join

Overlay menggunakan:

```python
predicate="intersects"
```

untuk mengurangi kegagalan overlay pada titik yang berada di boundary polygon.

---

# Debugging

Pipeline memiliki debug:

* jumlah file geotagging
* jumlah record
* jumlah NULL idsubsls
* sample idsubsls
* jumlah join match

---

# Catatan

* CRS otomatis disamakan
* CSV master otomatis membaca delimiter
* mendukung `,`, `;`, `|`, dan delimiter lain
* output GS menggunakan format GeoJSON
* output muatan menggunakan CSV

---

# Author

Developed for SE2026 Geotagging & Muatan Processing Pipeline.
