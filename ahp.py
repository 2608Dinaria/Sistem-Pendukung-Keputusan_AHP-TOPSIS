import numpy as np
import pandas as pd

# Daftar Random Index (RI) berdasarkan ordo matriks (n) menurut Saaty
RANDOM_INDEX = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49
}

# Nama kriteria untuk visualisasi
CRITERIA_NAMES = [
    "Luas Lahan (C1)",
    "Produktivitas (C2)",
    "Jumlah Petani (C3)"
]

def calculate_ahp(pairwise_matrix):
    """
    Melakukan perhitungan AHP lengkap berdasarkan matriks perbandingan berpasangan.
    
    Parameters:
    pairwise_matrix (numpy.ndarray): Matriks perbandingan berpasangan n x n (4 x 4)
    
    Returns:
    dict: Hasil perhitungan detail untuk kebutuhan laporan skripsi
    """
    n = pairwise_matrix.shape[0]
    
    # 1. Jumlah Kolom Matriks Perbandingan
    col_sums = np.sum(pairwise_matrix, axis=0)
    
    # 2. Normalisasi Matriks
    normalized_matrix = pairwise_matrix / col_sums
    
    # 3. Bobot Prioritas (Eigen Vector) - rata-rata baris dari matriks normalisasi
    weights = np.mean(normalized_matrix, axis=1)
    
    # 4. Perhitungan Uji Konsistensi
    # a. Kalikan matriks perbandingan awal dengan bobot kriteria (A * W)
    weighted_sum_vector = np.dot(pairwise_matrix, weights)
    
    # b. Bagi hasil perkalian tersebut dengan bobot kriteria masing-masing ((A * W) / W)
    consistency_vector = weighted_sum_vector / weights
    
    # c. Nilai Lambda Max (rata-rata dari hasil pembagian)
    lambda_max = np.mean(consistency_vector)
    
    # d. Consistency Index (CI)
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    
    # e. Consistency Ratio (CR)
    ri = RANDOM_INDEX.get(n, 1.0)
    cr = ci / ri if ri > 0 else 0.0
    
    # Menentukan status konsistensi
    is_consistent = cr < 0.1
    
    # Menyusun data ke dalam DataFrame agar rapi ditampilkan di Streamlit
    df_pairwise = pd.DataFrame(pairwise_matrix, columns=CRITERIA_NAMES, index=CRITERIA_NAMES)
    df_normalized = pd.DataFrame(normalized_matrix, columns=CRITERIA_NAMES, index=CRITERIA_NAMES)
    
    df_weights = pd.DataFrame({
        "Kriteria": CRITERIA_NAMES,
        "Bobot Prioritas (W)": weights,
        "Persentase (%)": weights * 100
    })
    
    df_consistency = pd.DataFrame({
        "Kriteria": CRITERIA_NAMES,
        "Bobot (W)": weights,
        "A x W": weighted_sum_vector,
        "CV (A x W / W)": consistency_vector
    })
    
    return {
        "n": n,
        "pairwise_matrix": df_pairwise,
        "column_sums": col_sums,
        "normalized_matrix": df_normalized,
        "weights": weights,
        "weights_dataframe": df_weights,
        "consistency_dataframe": df_consistency,
        "lambda_max": lambda_max,
        "ci": ci,
        "cr": cr,
        "is_consistent": is_consistent
    }
