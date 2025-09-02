import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import os
from typing import List, Optional
import ftplib
import io

# Hosting konfigürasyonunu import et
try:
    from hosting_config import FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH, XML_DOSYA_ADI
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False

class XMLBirlestirici:
    def __init__(self):
        self.merged_products = []
        self.session = requests.Session()
        # User-Agent ekleyerek daha güvenilir istekler yapalım
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def xml_dosyasini_al(self, url: str) -> Optional[ET.Element]:
        """URL'den XML dosyasını alır ve parse eder"""
        try:
            print(f"XML dosyası alınıyor: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # XML içeriğini parse et
            root = ET.fromstring(response.content)
            print(f"✓ XML dosyası başarıyla alındı: {url}")
            return root
            
        except requests.RequestException as e:
            print(f"❌ Hata: {url} adresinden XML alınamadı: {e}")
            return None
        except ET.ParseError as e:
            print(f"❌ XML parse hatası {url}: {e}")
            return None
        except Exception as e:
            print(f"❌ Beklenmeyen hata {url}: {e}")
            return None
    
    def urunleri_birlestir(self, xml_roots: List[ET.Element]) -> ET.Element:
        """Birden fazla XML dosyasındaki ürünleri birleştirir"""
        # Ana products elementi oluştur
        merged_root = ET.Element("products")
        
        # Her XML dosyasından ürünleri al
        for i, root in enumerate(xml_roots):
            if root is None:
                continue
                
            print(f"XML dosyası {i+1} işleniyor...")
            
            # products altındaki tüm product elementlerini bul
            products = root.findall(".//product")
            
            for product in products:
                # Ürünü kopyala ve ana listeye ekle
                merged_root.append(product)
                print(f"  ✓ Ürün eklendi: {product.find('name').text if product.find('name') is not None else 'İsimsiz'}")
        
        print(f"\nToplam {len(merged_root.findall('.//product'))} ürün birleştirildi.")
        return merged_root
    
    def xml_dosyasini_hosting_e_yukle(self, root: ET.Element, dosya_adi: str = "tumurunler2.xml"):
        """Birleştirilmiş XML'i hostinge yükler"""
        try:
            # XML'i güzel formatla
            ET.indent(root, space="  ")
            
            # XML string'ini oluştur
            xml_string = ET.tostring(root, encoding='unicode', xml_declaration=True)
            
            # Hosting bilgilerini al
            if CONFIG_LOADED:
                print("\n=== Konfigürasyon Dosyasından Hosting Bilgileri ===")
                ftp_host = FTP_HOST
                ftp_user = FTP_USER
                ftp_pass = FTP_PASS
                ftp_path = FTP_PATH
                dosya_adi = XML_DOSYA_ADI
                
                print(f"Host: {ftp_host}")
                print(f"Kullanıcı: {ftp_user}")
                print(f"Yol: {ftp_path}")
                print(f"Dosya: {dosya_adi}")
            else:
                print("\n=== Hosting Bilgileri ===")
                ftp_host = input("FTP Host (örn: ftp.example.com): ").strip()
                ftp_user = input("FTP Kullanıcı Adı: ").strip()
                ftp_pass = input("FTP Şifre: ").strip()
                ftp_path = input("FTP Yolu (örn: /public_html/): ").strip()
            
            if not ftp_host or not ftp_user or not ftp_pass:
                print("❌ Hosting bilgileri eksik!")
                return
            
            print(f"\nHostinge yükleniyor: {ftp_host}")
            
            # FTP bağlantısı
            ftp = ftplib.FTP(ftp_host)
            
            # Pasif modu etkinleştir (530 authentication failed hatası için)
            ftp.set_pasv(True)
            
            # Debug modunu aç
            ftp.set_debuglevel(2)
            
            # Login işlemi
            try:
                ftp.login(ftp_user, ftp_pass)
            except ftplib.error_perm as e:
                print(f"❌ FTP Login hatası: {e}")
                print("Lütfen kullanıcı adı ve şifrenizi kontrol edin.")
                return
            
            # Dizine geç
            if ftp_path:
                try:
                    ftp.cwd(ftp_path)
                except ftplib.error_perm as e:
                    print(f"⚠️ Dizin bulunamadı, ana dizinde devam ediliyor: {e}")
            
            # XML dosyasını yükle
            xml_bytes = xml_string.encode('utf-8')
            xml_io = io.BytesIO(xml_bytes)
            
            ftp.storbinary(f'STOR {dosya_adi}', xml_io)
            
            ftp.quit()
            
            print(f"✓ XML dosyası başarıyla hostinge yüklendi: {dosya_adi}")
            print(f"  Dosya boyutu: {len(xml_bytes)} bytes")
            print(f"  Hosting URL: ftp://{ftp_host}{ftp_path}{dosya_adi}")
            
        except ftplib.error_perm as e:
            print(f"❌ FTP hatası: {e}")
        except Exception as e:
            print(f"❌ Hosting yükleme hatası: {e}")
    
    def url_listesinden_birlestir(self, urls: List[str]):
        """URL listesinden XML dosyalarını alır ve birleştirir"""
        print("XML dosyaları birleştirme işlemi başlatılıyor...")
        print(f"Toplam {len(urls)} URL işlenecek\n")
        
        # Tüm XML dosyalarını al
        xml_roots = []
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] İşleniyor...")
            root = self.xml_dosyasini_al(url)
            xml_roots.append(root)
            print()
        
        # Geçerli XML dosyalarını filtrele
        valid_roots = [root for root in xml_roots if root is not None]
        
        if not valid_roots:
            print("❌ Hiçbir geçerli XML dosyası bulunamadı!")
            return
        
        print(f"✓ {len(valid_roots)} geçerli XML dosyası bulundu")
        
        # Ürünleri birleştir
        merged_root = self.urunleri_birlestir(valid_roots)
        
        # Hostinge yükle
        self.xml_dosyasini_hosting_e_yukle(merged_root)
        
        print("\n🎉 İşlem tamamlandı!")

def main():
    print("=== XML Dosyası Birleştirici ===\n")
    
    # URL'leri buraya ekleyin
    urls = [
        "https://www.eterella.com/yasinxml/ani.xml",
        "https://www.eterella.com/yasinxml/imoda.xml"
    ]
    
    print(f"Toplam {len(urls)} URL işlenecek:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    print("\nXML dosyaları birleştirme işlemi başlatılıyor...")
    
    # Birleştirme işlemini başlat
    birlestirici = XMLBirlestirici()
    birlestirici.url_listesinden_birlestir(urls)

if __name__ == "__main__":
    main() 
