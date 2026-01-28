from flask import Flask, render_template, request
from dotenv import load_dotenv
import os
import time

import google.generativeai as genai
import markdown



app = Flask(__name__)


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 # 10 MB Limit
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
load_dotenv()
genai.configure(api_key=os.getenv("GENAI_API_KEY"))


generation_config = {

    "temperature": 0.0,

    "top_p": 1,

    "top_k": 32,

    "max_output_tokens": 4096,
}

model = genai.GenerativeModel(

    model_name="models/gemma-3-12b-it",

    generation_config=generation_config

)



@app.route('/')

def index():

    return render_template('index.html')


@app.route('/analiz', methods=['POST'])

def analiz():

    if 'cv_dosyasi' not in request.files: return "Dosya yok!"

    dosya = request.files['cv_dosyasi']

    if dosya.filename == '': return "Dosya seçilmedi!"

    dosya_yolu = os.path.join(app.config['UPLOAD_FOLDER'], dosya.filename)

    dosya.save(dosya_yolu)

    is_ilani = request.form.get('is_ilani', '').strip()

    ozel_mesaj = request.form.get('ozel_mesaj', '').strip()

    ozel_rapor = request.form.get('ozel_rapor', '').strip()

    secilenler = request.form.getlist('tercihler') 

    prompt = f"""
    
    🛑 EN ÖNCELİKLİ GÖREV: TÜR KONTROLÜ
    Yüklenen dosyayı analiz et. Bu dosya BİR ÖZGEÇMİŞ (CV/Resume) Mİ?
    
    HAYIR İSE (Fatura, Yemek Tarifi, Ders Notu, Kitap Sayfası, Kod Bloğu, Fotoğraf vb.):
    Aşağıdaki hata mesajını BİREBİR yaz ve BAŞKA HİÇBİR ŞEY YAZMA. Analizi derhal sonlandır.
    
    "# ⚠️ Belge Hatası"
    "Yüklenen dosya bir CV (Özgeçmiş) olarak algılanamadı. Lütfen geçerli bir özgeçmiş dosyası yükleyiniz."
    "**Algılanan Tür:** [Buraya belgenin neye benzediğini yaz]"

    EVET İSE (Veya CV'ye benziyorsa):
    Aşağıdaki kurallara ve PUANLAMA CETVELİNE göre analize başla.

    🛑 KRİTİK PUANLAMA KURALLARI:
    1. Her kategori için belirtilen PUAN, o kategoriden alınabilecek EN YÜKSEK (MAKSİMUM) puandır.
    2. ASLA belirtilen maksimum puanı aşma. (Örneğin: Eğitim max 20 ise, Harvard mezunu bile olsa 20 ver, 21 veya 35 verme!).
    3. Puanları topladığında 100'ü geçmesi İMKANSIZDIR.

    --- PUANLAMA CETVELİ (RUBRIC - TOPLAM 100) ---

    1. **Tasarım, Düzen ve ATS Uyumu (MAKSİMUM 15 Puan):**
       - CV'nin temiz, okunabilir ve profesyonel olması.
       - Yazım hatası olmaması.
       - ATS sistemlerinin okuyabileceği formatta olması.

    2. **Teknik Yetkinlikler ve Stack Uyumu (MAKSİMUM 30 Puan):**
       - Adayın bildiği dillerin (Python, Java vb.) iş ilanıyla veya sektörle uyumu.
       - Modern araçların (Git, Docker, SQL vb.) bilinmesi.

    3. **Projeler, GitHub ve Pratik Uygulama (MAKSİMUM 35 Puan):**
       - Somut projelerin kalitesi, GitHub aktivitesi.
       - "Yaptım" diyebilmesi, sadece "biliyorum" dememesi.

    4. **Eğitim, Sertifikalar ve Gelişim Azmi (MAKSİMUM 20 Puan):**  <-- DİKKAT: BURASI EN FAZLA 20 PUANDIR. ASLA 35 VERME!
       - Üniversite eğitimi ve not ortalaması.
       - Ekstra kurslar, sertifikalar.
       - Sürekli öğrenme ve gelişim.

    --- KULLANICI TERCİHLERİ VE ANALİZ FORMATI ---

    Analizini, yorumlarını ve başlıklarını KESİNLİKLE VE SADECE **TÜRKÇE** DİLİNDE YAZ. (CV İngilizce olsa bile Türkçe rapor ver).

    - **DOSYA/GÖRÜNTÜ DURUMU:** CV bir resim veya taranmış PDF ise, görüntü işleme ile içeriği okuduğunu belirt. Eğer metin HİÇ okunamıyorsa "Metin Okuma Hatası" ver.

    🛑 SON KONTROL (ÇIKTI ÜRETMEDEN ÖNCE KENDİNİ DENETLE):
    - Eğitim bölümüne 20'den fazla puan verdin mi? Evetse 20'ye düşür.
    - Proje bölümüne 35'den fazla puan verdin mi? Evetse 35'e düşür.
    - Toplam 100'ü geçiyor mu? Evetse puanları kırparak 100'e eşitle.
    """

   

    if 'ats_puani' in secilenler:

        prompt += "\n- **ATS SKORU:** Yukarıdaki puanlama sistemine göre hesapladığın puanı yaz (X/100). Nereden puan kırdığını veya verdiğini tek tek açıkla."

    if 'guclu_yonler' in secilenler:

        prompt += "\n- **GÜÇLÜ YÖNLER:** Adayı öne çıkaran en net 3 özellik."

    if 'gelistirme' in secilenler:

        prompt += "\n- **GELİŞTİRİLMESİ GEREKENLER:** Kritik hatalar ve eksikler."

    if 'eksik_kelimeler' in secilenler:

        prompt += "\n- **EKSİK ANAHTAR KELİMELER:** Sektör standardı olup CV'de bulunmayan terimler."

    if 'mulakat_sorulari' in secilenler:

        prompt += "\n- **MÜLAKAT SORULARI:** Bu adayı zorlayacak 2 teknik soru."

    

    # Özel rapor talebi

    if ozel_rapor:

        prompt += f"\n- **ÖZEL RAPOR:** {ozel_rapor}"

       

    if is_ilani:

        prompt += f"\n\n--- İŞ İLANI METNİ ---\n{is_ilani}"

    

    # Özel soru - AI sadece buna odaklanacak

    if ozel_mesaj:

        prompt += f"\n\n💬 **KULLANICI SORUSU (SADECE BUNA CEVAP VER):** {ozel_mesaj}"

    if is_ilani:

        prompt += f"\n\n--- İŞ İLANI METNİ ---\n{is_ilani}"



    try:

        yuklenen_dosya = genai.upload_file(dosya_yolu, mime_type="application/pdf")

        time.sleep(2)

       

        response = model.generate_content([yuklenen_dosya, prompt])

        html_icerik = markdown.markdown(response.text)

       

        return f"""

        <!DOCTYPE html>

        <html lang="tr">

        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">

            <style>

                * {{ margin: 0; padding: 0; box-sizing: border-box; }}

                body {{ 

                    font-family: 'Inter', -apple-system, sans-serif;

                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

                    min-height: 100vh;

                    padding: 40px 20px;

                }}

                .report-container {{

                    max-width: 900px;

                    margin: 0 auto;

                    background: rgba(255, 255, 255, 0.98);

                    backdrop-filter: blur(20px);

                    border-radius: 24px;

                    padding: 50px;

                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);

                    animation: slideUp 0.6s ease-out;

                }}

                @keyframes slideUp {{

                    from {{ opacity: 0; transform: translateY(30px); }}

                    to {{ opacity: 1; transform: translateY(0); }}

                }}

                .report-header {{

                    text-align: center;

                    margin-bottom: 40px;

                    padding-bottom: 30px;

                    border-bottom: 3px solid #e5e7eb;

                }}

                .report-header h1 {{

                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

                    -webkit-background-clip: text;

                    -webkit-text-fill-color: transparent;

                    background-clip: text;

                    font-size: 36px;

                    font-weight: 800;

                    letter-spacing: -1px;

                    margin-bottom: 10px;

                }}

                .report-header p {{

                    color: #6b7280;

                    font-size: 16px;

                    font-weight: 500;

                }}

                .report-content {{

                    line-height: 1.8;

                    color: #374151;

                }}

                .report-content h1 {{

                    font-size: 28px;

                    color: #1f2937;

                    margin-top: 40px;

                    margin-bottom: 20px;

                    font-weight: 700;

                }}

                .report-content h2 {{

                    font-size: 24px;

                    color: #374151;

                    margin-top: 35px;

                    margin-bottom: 15px;

                    font-weight: 700;

                    padding-left: 15px;

                    border-left: 4px solid #667eea;

                }}

                .report-content h3 {{

                    font-size: 20px;

                    color: #4b5563;

                    margin-top: 25px;

                    margin-bottom: 12px;

                    font-weight: 600;

                }}

                .report-content p {{

                    margin-bottom: 16px;

                    font-size: 15px;

                    line-height: 1.8;

                }}

                .report-content ul, .report-content ol {{

                    margin-left: 25px;

                    margin-bottom: 20px;

                }}

                .report-content li {{

                    margin-bottom: 10px;

                    font-size: 15px;

                    line-height: 1.7;

                }}

                .report-content strong {{

                    color: #1f2937;

                    font-weight: 700;

                }}

                .report-content em {{

                    color: #6366f1;

                    font-style: normal;

                    font-weight: 600;

                }}

                .report-content code {{

                    background: #f3f4f6;

                    padding: 2px 8px;

                    border-radius: 6px;

                    font-size: 14px;

                    color: #dc2626;

                    font-family: 'Courier New', monospace;

                }}

                .report-content blockquote {{

                    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);

                    border-left: 4px solid #f59e0b;

                    padding: 20px;

                    margin: 25px 0;

                    border-radius: 12px;

                    font-style: italic;

                    color: #92400e;

                }}

                .btn-container {{

                    text-align: center;

                    margin-top: 50px;

                    padding-top: 30px;

                    border-top: 2px solid #e5e7eb;

                }}

                .btn-home {{

                    display: inline-block;

                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

                    color: white;

                    padding: 16px 40px;

                    text-decoration: none;

                    border-radius: 14px;

                    font-weight: 700;

                    font-size: 16px;

                    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);

                    transition: all 0.3s ease;

                    text-transform: uppercase;

                    letter-spacing: 0.5px;

                }}

                .btn-home:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
                }}

                /* Mobile Optimization */
                @media (max-width: 768px) {{
                    body {{
                        padding: 20px 15px;
                    }}
                    
                    .report-container {{
                        padding: 30px 20px;
                        border-radius: 16px;
                    }}

                    .report-header h1 {{
                        font-size: 28px;
                    }}

                    .report-header p {{
                        font-size: 14px;
                    }}

                    .report-content h1 {{
                        font-size: 24px;
                    }}

                    .report-content h2 {{
                        font-size: 20px;
                        margin-top: 25px;
                    }}

                    .report-content h3 {{
                        font-size: 18px;
                    }}

                    .report-content p, .report-content li {{
                        font-size: 14px;
                    }}

                    .btn-home {{
                        width: 100%;
                        padding: 15px;
                        display: block; /* Make it block level to fill width */
                    }}
                }}

            </style>

        </head>

        <body>

            <div class="report-container">

                <div class="report-header">

                    <h1> Detaylı CV Raporu</h1>

                    <p>Yapay Zeka Destekli Profesyonel Analiz Sonuçları</p>

                </div>

                <div class="report-content">

                    {html_icerik}

                </div>

                <div class="btn-container">

                    <a href='/' class="btn-home">🏠 Yeni Analiz Yap</a>

                </div>

            </div>

        </body>

        </html>

        """

    except Exception as e:
        error_msg = str(e)
        friendly_error = ""
        
        if "400" in error_msg and "32 images" in error_msg:
            friendly_error = """
            <h2 style="color: #dc2626; margin-bottom: 20px;">⚠️ Belge Çok Uzun / Sayfa Sınırı Aşıldı</h2>
            <p>Yüklediğiniz CV dosyası çok fazla sayfa veya görsel içeriyor (Maksimum sınır aşıldı).</p>
            <p><strong>Neden bu hatayı alıyorum?</strong></p>
            <ul>
                <li>Yapay zeka modeli bir seferde en fazla 32 sayfa/resim işleyebilir.</li>
                <li>Yüklediğiniz PDF çok uzun olabilir.</li>
            </ul>
            <p style="margin-top: 20px;"><strong>Çözüm Önerisi:</strong> Lütfen daha kısa (özetli) bir versiyonunu veya sayfa sayısı azaltılmış bir PDF yükleyiniz.</p>
            """
        else:
            friendly_error = f"""
            <h2 style="color: #dc2626; margin-bottom: 20px;">⚠️ Beklenmeyen Bir Hata Oluştu</h2>
            <p>Analiz sırasında teknik bir sorun meydana geldi.</p>
            <p style="background: #f3f4f6; padding: 15px; border-radius: 8px; font-family: monospace; color: #b91c1c;">{error_msg}</p>
            """

        return f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Hata - AI Kariyer Asistanı</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Inter', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 20px;
                    margin: 0;
                }}
                .error-container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    max-width: 600px;
                    width: 100%;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }}
                .btn-home {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 12px;
                    font-weight: 600;
                    margin-top: 25px;
                    transition: transform 0.2s;
                }}
                .btn-home:hover {{
                    transform: translateY(-2px);
                }}
                ul {{
                    text-align: left;
                    margin-top: 15px;
                    color: #4b5563;
                }}
                li {{ margin-bottom: 8px; }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div style="font-size: 50px; margin-bottom: 20px;">🤖💥</div>
                {friendly_error}
                <a href='/' class="btn-home">🏠 Ana Sayfaya Dön</a>
            </div>
        </body>
        </html>
        """



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)