from flask import Flask, render_template, request, make_response, redirect, url_for
import os
from datetime import datetime
import math
from database import init_db, add_scan_result, get_all_scans

# Definisi konstanta
PER_PAGE = 20

# Tentukan jalur absolut ke folder 'templates'
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir) 

# =======================
# ENDPOINT UNTUK UPTIMEROBOT
# =======================
@app.route('/ping')
def ping():
    """Gunakan URL ini di UptimeRobot: https://cyberwebscanner.onrender.com/ping"""
    return "OK", 200

# =======================
# HALAMAN UTAMA
# =======================
@app.route('/')
def index():
    return render_template('index.html')

# =======================
# JALANKAN PEMINDAIAN
# =======================
@app.route("/scan", methods=["GET", "POST"])
def scan():
    # PROTEKSI: Jika diakses via GET (UptimeRobot atau ketik manual), alihkan ke Home.
    # Ini mencegah "Internal Server Error" karena request kosong.
    if request.method == "GET":
        return redirect(url_for('index'))

    # JIKA DIAKSES VIA POST (User menekan tombol Scan)
    try:
        url = request.form.get("url", "").strip()

        # Jika input URL kosong, jangan diproses
        if not url:
            return redirect(url_for('index'))

        # Tambahkan protokol otomatis jika user lupa
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        # Jalankan mesin scanner
        from scanner import run_full_scan
        result = run_full_scan(url)

        # Simpan hasil ke database
        try:
            score_data = result.get("score_info", {})
            score = score_data.get("score", 0)
            grade = score_data.get("grade", "N/A")
            add_scan_result(url, score, grade, result)
        except Exception as db_err:
            print(f"[DB ERROR] {db_err}")

        # Tampilkan hasil akhir
        return render_template("scan_result.html", results=result)

    except Exception as e:
        error_type = type(e).__name__
        error_detail = str(e)
        
        # Tampilan Error 500 yang informatif jika mesin scanner crash
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Kesalahan Server</title></head>
        <body style="font-family:sans-serif; text-align:center; padding-top:50px; background:#f4f4f4;">
            <div style="display:inline-block; background:white; padding:30px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1); max-width:500px;">
                <h1 style="color:#e74c3c;">❌ TERJADI KESALAHAN INTERNAL (500)</h1>
                <p>Aplikasi gagal melakukan scanning pada URL tersebut.</p>
                <div style="text-align:left; background:#eee; padding:10px; font-family:monospace; font-size:12px; margin-bottom:20px;">
                    <strong>Tipe:</strong> {error_type}<br>
                    <strong>Detail:</strong> {error_detail}
                </div>
                <a href="/" style="text-decoration:none; color:#3498db; font-weight:bold;">← Kembali ke Beranda</a>
            </div>
        </body>
        </html>
        """
        return make_response(html_content, 500)

# =======================
# HALAMAN RIWAYAT PEMINDAIAN
# =======================
@app.route('/history')
def history():
    page = request.args.get('page', 1, type=int) 
    all_scans = get_all_scans() 
    
    if all_scans is None:
        all_scans = []
        
    total_scans = len(all_scans)
    offset = (page - 1) * PER_PAGE
    scans_for_page = all_scans[offset:offset + PER_PAGE]

    total_pages = math.ceil(total_scans / PER_PAGE) if total_scans > 0 else 0
    
    scans_list = [
        {
            "id": row["id"],
            "url": row["url"],
            "scan_date": row["scan_date"],
            "score": row["score"],
            "grade": row["grade"]
        }
        for row in scans_for_page
    ]
    
    return render_template("history.html", 
                           scans=scans_list,
                           page=page,
                           total_pages=total_pages)

# =======================
# HALAMAN DOKUMENTASI
# =======================
@app.route('/docs')
def docs():
    return render_template('docs.html', datetime=datetime)

# =======================
# JALANKAN APP
# =======================
if __name__ == "__main__":
    init_db()
    # Port dinamis untuk Render
    port = int(os.environ.get("PORT", 5000))
    # Matikan debug=True untuk penggunaan produksi yang lebih stabil
    app.run(host="0.0.0.0", port=port, debug=False)
