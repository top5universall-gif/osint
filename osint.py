#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT Toolkit v2
Scan NIK & HP, Dorking, Dukcapil, Komdigi
By ChatGPT & Fariz Project
"""

import requests, re, sys, concurrent.futures, datetime, html
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
init(autoreset=True)

# ===== Database Provider HP =====
PROVIDER_PREFIX = {
    "0811": "Telkomsel", "0812": "Telkomsel", "0813": "Telkomsel",
    "0821": "Telkomsel", "0822": "Telkomsel", "0823": "Telkomsel",
    "0852": "Telkomsel", "0853": "Telkomsel", "0851": "Telkomsel",
    "0814": "Indosat", "0815": "Indosat", "0816": "Indosat",
    "0855": "Indosat", "0856": "Indosat", "0857": "Indosat", "0858": "Indosat",
    "0817": "XL", "0818": "XL", "0819": "XL",
    "0859": "XL", "0877": "XL", "0878": "XL",
    "0831": "Axis", "0832": "Axis", "0833": "Axis", "0838": "Axis",
    "0895": "Three", "0896": "Three", "0897": "Three", "0898": "Three", "0899": "Three",
    "0881": "Smartfren", "0882": "Smartfren", "0883": "Smartfren", "0884": "Smartfren",
    "0885": "Smartfren", "0886": "Smartfren", "0887": "Smartfren", "0888": "Smartfren", "0889": "Smartfren"
}

# ===== Database Kode Wilayah NIK =====
# (Contoh sebagian, versi full bisa di-load dari file eksternal agar rapi)
KODE_WILAYAH = {
    "32": "Jawa Barat",
    "3201": "Kabupaten Bogor",
    "3202": "Kabupaten Sukabumi",
    "3203": "Kabupaten Cianjur",
    "3204": "Kabupaten Bandung",
    "3205": "Kabupaten Garut",
    # ... tambahkan semua kode Indonesia ...
}

# ===== Fungsi Parsing NIK =====
def parse_nik(nik):
    info = {}
    prov = nik[:2]
    kab = nik[:4]
    kec = nik[4:6]
    tgl = int(nik[6:8])
    bln = int(nik[8:10])
    thn = int(nik[10:12])

    gender = "Laki-laki"
    if tgl > 40:
        gender = "Perempuan"
        tgl -= 40

    tahun_lahir = thn + 1900 if thn > 30 else thn + 2000

    info["Provinsi"] = KODE_WILAYAH.get(prov, "Tidak diketahui")
    info["Kab/Kota"] = KODE_WILAYAH.get(kab, "Tidak diketahui")
    info["Kecamatan (kode)"] = kec
    info["Jenis Kelamin"] = gender
    info["Tanggal Lahir"] = f"{tgl:02d}-{bln:02d}-{tahun_lahir}"
    return info

# ===== Parsing HP =====
def parse_hp(hp):
    hp = hp.replace("+62", "0")
    prefix = hp[:4]
    return PROVIDER_PREFIX.get(prefix, "Tidak diketahui")

# ===== Google Dorking =====
def google_dork(query):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://www.google.com/search?q={query}"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for g in soup.select("a"):
            href = g.get("href")
            if href and href.startswith("http") and "google" not in href:
                results.append(href)
        return list(set(results))
    except:
        return []

# ===== Dukcapil (endpoint publik) =====
def cek_dukcapil(nik):
    try:
        # Contoh endpoint publik pemda (ganti jika perlu)
        url = f"https://api-publik-dukcapil.example/cek?nik={nik}"
        r = requests.get(url, timeout=10).json()
        return r.get("status", "Tidak tersedia")
    except:
        return "Tidak tersedia"

# ===== Komdigi =====
def cek_komdigi(data):
    try:
        url = f"https://cekdata.komdigi.go.id/api/check?data={data}"
        r = requests.get(url, timeout=10).json()
        return r.get("status", "Tidak tersedia")
    except:
        return "Tidak tersedia"

# ===== Main =====
def main(targets):
    html_rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {}
        for t in targets:
            if re.fullmatch(r"\d{16}", t):  # NIK
                nik_info = parse_nik(t)
                dukcapil_status = cek_dukcapil(t)
                komdigi_status = cek_komdigi(t)
                futures[executor.submit(google_dork, t)] = ("NIK", t, nik_info, dukcapil_status, komdigi_status)
            elif re.fullmatch(r"(\+628\d{8,11}|08\d{8,11})", t):  # HP
                provider = parse_hp(t)
                dukcapil_status = "-"
                komdigi_status = cek_komdigi(t)
                futures[executor.submit(google_dork, t)] = ("HP", t, {"Provider": provider}, dukcapil_status, komdigi_status)

        for future in concurrent.futures.as_completed(futures):
            tipe, data, info, dukcapil_status, komdigi_status = futures[future]
            results = future.result()
            print(Fore.GREEN + f"[{tipe}] {data}")
            for k, v in info.items():
                print(f"  {k}: {v}")
            print(f"  Dukcapil: {dukcapil_status}")
            print(f"  Komdigi: {komdigi_status}")
            print(f"  Hasil Dorking ({len(results)}):")
            for link in results[:10]:
                print(f"    - {link}")

            # Simpan ke HTML
            html_info = "<br>".join([f"{k}: {v}" for k, v in info.items()])
            html_links = "<br>".join([f'<a href="{l}" target="_blank">{l}</a>' for l in results])
            html_rows.append(f"<tr><td>{tipe}</td><td>{html.escape(data)}</td><td>{html_info}</td><td>{dukcapil_status}</td><td>{komdigi_status}</td><td>{html_links}</td></tr>")

    # Output HTML
    with open("report.html", "w", encoding="utf-8") as f:
        f.write(f"""
        <html><head><meta charset="UTF-8"><title>OSINT Report</title>
        <style>body{{font-family:Arial}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:8px}}</style>
        </head><body>
        <h2>OSINT Report</h2>
        <table>
        <tr><th>Tipe</th><th>Target</th><th>Info</th><th>Dukcapil</th><th>Komdigi</th><th>Hasil Dorking</th></tr>
        {''.join(html_rows)}
        </table></body></html>
        """)
    print(Fore.YELLOW + "\n[+] Report tersimpan ke report.html")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <NIK/HP> [NIK/HP...]")
        sys.exit(1)
    main(sys.argv[1:])
