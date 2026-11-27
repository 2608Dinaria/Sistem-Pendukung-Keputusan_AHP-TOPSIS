import io
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np



def generate_ranking_chart(df_results):
    """
    Membuat grafik batang horizontal hasil perangkingan alternatif menggunakan Matplotlib.
    Menerima DataFrame hasil TOPSIS yang berisi kolom 'nama_kelompok' dan 'preferensi' atau 'nilai_preferensi'.
    """
    df_results = df_results.copy()
    if "nilai_preferensi" in df_results.columns:
        df_results = df_results.rename(columns={"nilai_preferensi": "preferensi"})
        
    # Ambil data terurut
    df_results = df_results.sort_values(by="preferensi", ascending=False)
    
    # Ambil Top 30 saja agar grafik tetap bersih dan terbaca (standard SPK)
    num_total = len(df_results)
    if num_total > 30:
        df_plot = df_results.head(30).copy()
        chart_title = f'Grafik Prioritas (Top 30 dari {num_total} Kelompok Tani)'
    else:
        df_plot = df_results.copy()
        chart_title = 'Grafik Prioritas Hasil Rekomendasi (TOPSIS)'
        
    # Urutkan balik untuk plotting barh (agar peringkat 1 ada di paling atas)
    df_plot = df_plot.sort_values(by="preferensi", ascending=True)
    num_elements = len(df_plot)
    
    # Tentukan tinggi grafik secara dinamis (minimal 6 inci, per bar kira-kira 0.4 inci)
    dynamic_height = max(6, num_elements * 0.4)
    
    # Font size yang proporsional
    base_font = 10 if num_elements <= 15 else 9
    
    fig, ax = plt.subplots(figsize=(10, dynamic_height))
    
    # Menentukan warna: terbaik diberi warna hijau tua, lainnya hijau muda/abu-abu
    colors = []
    for i in range(num_elements):
        if i == num_elements - 1:
            colors.append('#1b5e20') # Terbaik
        else:
            colors.append('#81c784') # Lainnya
            
    # Kurangi height bar (ketebalan) agar ada ruang antar bar
    # Gabungkan nama kelompok dan desa untuk label y jika ada data desa
    if "desa_kelurahan" in df_plot.columns:
        df_plot['label_display'] = df_plot.apply(
            lambda x: f"{x['nama_kelompok']} ({x['desa_kelurahan']})" if str(x['desa_kelurahan']).lower() != 'tidak diketahui' else x['nama_kelompok'], 
            axis=1
        )
    else:
        df_plot['label_display'] = df_plot['nama_kelompok']
        
    bars = ax.barh(df_plot['label_display'], df_plot['preferensi'], color=colors, height=0.5)
    
    # Menambahkan nilai preferensi di ujung batang grafik
    for bar in bars:
        width = bar.get_width()
        # Tambahkan sedikit offset x agar tidak menempel di bar
        ax.text(width + 0.02, bar.get_y() + bar.get_height()/2, 
                f'{width:.4f}', 
                va='center', ha='left', fontsize=base_font, fontweight='semibold')
                
    ax.set_title(chart_title, 
                 fontsize=14, pad=15, fontweight='bold', color='#1b5e20')
    ax.set_xlabel('Nilai Preferensi (V)', fontsize=11, labelpad=10)
    ax.tick_params(axis='y', labelsize=base_font)
    ax.set_xlim(0, 1.15) # Beri ruang untuk teks angka di ujung bar
    
    # Mempercantik tampilan grid & spine
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    return fig

def generate_confusion_matrix_chart(tn, fp, fn, tp):
    """
    Membuat visualisasi heatmap confusion matrix 2x2 sederhana menggunakan Matplotlib.
    """
    cm = np.array([[tn, fp],
                   [fn, tp]])
                   
    fig, ax = plt.subplots(figsize=(6, 5))
    
    # Menggambar matriks menggunakan Greens colormap
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Greens)
    fig.colorbar(im, ax=ax, shrink=0.8)
    
    # Teks label untuk sumbu
    classes_x = ['Tidak Direkomendasikan\n(Sistem)', 'Direkomendasikan\n(Sistem)']
    classes_y = ['Bukan Penerima\n(Aktual)', 'Penerima\n(Aktual)']
    
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=classes_x, 
           yticklabels=classes_y,
           title='Confusion Matrix Evaluasi SPK',
           ylabel='Data Aktual Lapangan',
           xlabel='Hasil Rekomendasi Sistem')
           
    # Putar label x agar rapi
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
    
    # Set title color & size
    ax.title.set_fontsize(14)
    ax.title.set_fontweight('bold')
    ax.title.set_color('#1b5e20')
    
    # Loop untuk memasukkan teks ke dalam cell matriks
    thresh = cm.max() / 2.
    labels = [
        [f"True Negative (TN)\n{tn}", f"False Positive (FP)\n{fp}"],
        [f"False Negative (FN)\n{fn}", f"True Positive (TP)\n{tp}"]
    ]
    
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, labels[i][j],
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontweight='bold', fontsize=11)
                    
    plt.tight_layout()
    return fig

def export_to_excel(df_results):
    """
    Mengekspor dataframe hasil ranking ke format Excel.
    Mengembalikan data biner (bytes) yang siap diunduh.
    """
    output = io.BytesIO()
    df_results = df_results.copy()
    if "nilai_preferensi" in df_results.columns:
        df_results = df_results.rename(columns={"nilai_preferensi": "preferensi"})
        
    # Mempersiapkan dataframe yang bersih untuk ekspor (tanpa status_aktual)
    export_df = df_results[[
        'ranking', 'nama_kelompok', 'desa_kelurahan', 'luas_lahan',
        'produktivitas', 'jumlah_petani', 'preferensi'
    ]].copy()
    
    export_df.columns = [
        'Ranking', 'Nama Kelompok Tani', 'Desa/Kelurahan', 'Luas Lahan (Ha)',
        'Produktivitas (Kw/Ha)', 'Jumlah Anggota Petani', 'Nilai Preferensi (V)'
    ]
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Hasil SPK AHP-TOPSIS')
        
    return output.getvalue()

def export_to_csv(df_results):
    """
    Mengekspor dataframe hasil ranking ke format CSV.
    Mengembalikan string data CSV yang siap diunduh.
    """
    df_results = df_results.copy()
    if "nilai_preferensi" in df_results.columns:
        df_results = df_results.rename(columns={"nilai_preferensi": "preferensi"})
        
    # Mempersiapkan dataframe yang bersih untuk ekspor (tanpa status_aktual)
    export_df = df_results[[
        'ranking', 'nama_kelompok', 'desa_kelurahan', 'luas_lahan',
        'produktivitas', 'jumlah_petani', 'preferensi'
    ]].copy()
    
    export_df.columns = [
        'Ranking', 'Nama Kelompok Tani', 'Desa/Kelurahan', 'Luas Lahan (Ha)',
        'Produktivitas (Kw/Ha)', 'Jumlah Anggota Petani', 'Nilai Preferensi (V)'
    ]
    
    return export_df.to_csv(index=False).encode('utf-8')

def generate_excel_template():
    """Membuat template file Excel untuk upload data alternatif (tanpa kolom status_aktual)."""
    output = io.BytesIO()
    # Create sample structure
    df_template = pd.DataFrame([
        {
            "nama_kelompok": "Kelompok Tani Contoh 1",
            "desa_kelurahan": "Desa Makmur",
            "luas_lahan": 5.50,
            "produktivitas": 2.25,
            "jumlah_petani": 25
        },
        {
            "nama_kelompok": "Kelompok Tani Contoh 2",
            "desa_kelurahan": "Desa Sejahtera",
            "luas_lahan": 4.20,
            "produktivitas": 2.33,
            "jumlah_petani": 18
        }
    ])
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_template.to_excel(writer, index=False, sheet_name='Template Data SPK')
        
    return output.getvalue()
