import numpy as np
import pandas as pd

# Definisi kriteria dan tipenya
# True = Benefit, False = Cost
CRITERIA_TYPES = {
    "luas_lahan": True,       # Benefit (C1)
    "produktivitas": False,   # Cost (C2)
    "jumlah_petani": True     # Benefit (C3)
}

CRITERIA_KEYS = ["luas_lahan", "produktivitas", "jumlah_petani"]
CRITERIA_LABELS = ["Luas Lahan (C1)", "Produktivitas (C2)", "Jumlah Petani (C3)"]

def calculate_topsis(alternatives_list, weights):
    """
    Melakukan perhitungan TOPSIS lengkap berdasarkan data alternatif dan bobot AHP.
    
    Parameters:
    alternatives_list (list of dict): List data alternatif dari database
    weights (numpy.ndarray atau list): Bobot kriteria hasil perhitungan AHP (panjang 4)
    
    Returns:
    dict: Hasil perhitungan detail per tahapan TOPSIS untuk laporan skripsi
    """
    # Jika tidak ada alternatif, kembalikan dict kosong
    if not alternatives_list:
        return {}

    # Konversi data ke DataFrame Pandas
    df_orig = pd.DataFrame(alternatives_list)
    
    # 1. Bentuk Matriks Keputusan (X)
    # Ambil kolom kriteria saja
    X = df_orig[CRITERIA_KEYS].to_numpy(dtype=float)
    m, n = X.shape
    
    # 2. Normalisasi Matriks Keputusan (R)
    # Penyebut untuk normalisasi: akar kuadrat dari jumlah kuadrat setiap elemen per kolom
    denominators = np.sqrt(np.sum(X**2, axis=0))
    
    # Hindari pembagian dengan nol
    denominators = np.where(denominators == 0, 1e-9, denominators)
    
    R = X / denominators
    
    # 3. Normalisasi Terbobot (Y)
    # Kalikan setiap kolom dengan bobotnya
    Y = R * weights
    
    # 4. Menentukan Solusi Ideal Positif (A+) dan Solusi Ideal Negatif (A-)
    A_positive = np.zeros(n)
    A_negative = np.zeros(n)
    
    for j, key in enumerate(CRITERIA_KEYS):
        is_benefit = CRITERIA_TYPES[key]
        column_values = Y[:, j]
        
        if is_benefit:
            A_positive[j] = np.max(column_values)
            A_negative[j] = np.min(column_values)
        else:
            # Jika Cost (C3: produktivitas), maka positif adalah minimum dan negatif adalah maksimum
            A_positive[j] = np.min(column_values)
            A_negative[j] = np.max(column_values)
            
    # 5. Menghitung Jarak ke Solusi Ideal Positif (D+) dan Negatif (D-)
    # Jarak Euclidean
    D_positive = np.sqrt(np.sum((Y - A_positive) ** 2, axis=1))
    D_negative = np.sqrt(np.sum((Y - A_negative) ** 2, axis=1))
    
    # 6. Menghitung Nilai Preferensi (V)
    # V = D- / (D+ + D-)
    sum_D = D_positive + D_negative
    # Hindari pembagian dengan nol
    sum_D = np.where(sum_D == 0, 1e-9, sum_D)
    V = D_negative / sum_D
    
    # 7. Menyusun Hasil Ranking
    df_results = df_orig.copy()
    df_results["D_plus"] = D_positive
    df_results["D_minus"] = D_negative
    df_results["preferensi"] = V
    
    # Urutkan berdasarkan nilai preferensi tertinggi
    df_results = df_results.sort_values(by="preferensi", ascending=False)
    # Tambah kolom ranking
    df_results["ranking"] = range(1, len(df_results) + 1)
    
    # DataFrame Detail Per Tahapan (untuk visualisasi)
    # Gunakan MultiIndex agar Nama Kelompok dan Desa/Kelurahan tampil sebagai label
    index_labels = [df_orig["nama_kelompok"], df_orig["desa_kelurahan"]]
    index_names = ["Nama Kelompok", "Desa/Kelurahan"]
    
    df_X = pd.DataFrame(X, columns=CRITERIA_LABELS, index=index_labels)
    df_X.index.names = index_names
    
    df_R = pd.DataFrame(R, columns=CRITERIA_LABELS, index=index_labels)
    df_R.index.names = index_names
    
    df_Y = pd.DataFrame(Y, columns=CRITERIA_LABELS, index=index_labels)
    df_Y.index.names = index_names
    
    df_ideal = pd.DataFrame(
        [A_positive, A_negative],
        columns=CRITERIA_LABELS,
        index=["Solusi Ideal Positif (A+)", "Solusi Ideal Negatif (A-)"]
    )
    
    df_distances = pd.DataFrame({
        "D+ (Jarak Ideal Positif)": D_positive,
        "D- (Jarak Ideal Negatif)": D_negative,
        "Nilai Preferensi (V)": V
    }, index=index_labels)
    df_distances.index.names = index_names
    
    # Urutkan df_distances berdasarkan preferensi untuk presentasi
    df_distances_sorted = df_distances.sort_values(by="Nilai Preferensi (V)", ascending=False)
    df_distances_sorted["Ranking"] = range(1, len(df_distances_sorted) + 1)
    
    return {
        "df_X": df_X,
        "df_R": df_R,
        "df_Y": df_Y,
        "df_ideal": df_ideal,
        "df_distances": df_distances,
        "df_distances_sorted": df_distances_sorted,
        "results_dataframe": df_results
    }
