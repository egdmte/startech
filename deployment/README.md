# CAM VPS kurulumu

Bu klasör, üretim CAM uygulamasını `dymtal.avartech.net` üzerinde çalıştırmak
için gereken örnekleri içerir. CAM yalnız yapılandırma dosyası üretir. Araç
sürücüsünü içe aktarmaz, aracı silahlandırmaz ve motor komutu göndermez.

## 1. Dizinleri hazırla

Bu komutlar VPS üzerinde `egemen` kullanıcısıyla çalıştırılır. `sudo` parolasını
yalnız terminale yazın; hiçbir dosyaya veya sohbete yazmayın.

```bash
sudo install -d -o egemen -g egemen -m 0750 /srv/startech-cam
sudo install -d -o egemen -g egemen -m 0700 /srv/startech-cam/shared
```

Depoyu `/srv/startech-cam/app` olarak klonlayın veya doğrulanmış çalışma ağacını
bu konuma yerleştirin. Ardından bağımlılıkları kurun:

```bash
cd /srv/startech-cam
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/pip install -r app/requirements.txt
```

## 2. Gizli değerleri üret

Oturum anahtarı:

```bash
./venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Parolayı terminalde gizli biçimde alıp hash üretmek için:

```bash
./venv/bin/python -c 'import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass.getpass("CAM password: ")))' 
```

`deployment/startech-cam.env.example` dosyasını `/etc/startech-cam.env` olarak
kopyalayın, iki çıktıyı ilgili alanlara `sudoedit /etc/startech-cam.env` ile
yazın ve izinleri doğrulayın:

```bash
sudo install -o root -g root -m 0600 deployment/startech-cam.env.example /etc/startech-cam.env
sudoedit /etc/startech-cam.env
sudo stat -c '%U:%G %a %n' /etc/startech-cam.env
```

Beklenen son satır: `root:root 600 /etc/startech-cam.env`.

## 3. systemd hizmetini kur

```bash
cd /srv/startech-cam/app
sudo install -o root -g root -m 0644 deployment/startech-cam.service /etc/systemd/system/startech-cam.service
sudo systemctl daemon-reload
sudo systemctl enable --now startech-cam.service
systemctl status startech-cam.service --no-pager
curl --fail --silent http://127.0.0.1:8765/health
```

Sağlık yanıtı `{"status":"ok"}` olmalıdır. Hata varsa:

```bash
journalctl -u startech-cam.service -n 100 --no-pager
```

## 4. Caddy alan adını ekle

Mevcut `/etc/caddy/Caddyfile` dosyasını ezmeyin. Önce yedekleyin, sonra
`deployment/Caddyfile.startech-cam` içindeki site bloğunu mevcut dosyanın sonuna
ekleyin. Cloudflare Origin sertifikası kullanılacaksa sertifikanın
`*.avartech.net` alanını kapsadığı önce doğrulanmalıdır.

```bash
sudo cp -a /etc/caddy/Caddyfile /etc/caddy/Caddyfile.before-startech-cam
sudoedit /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Son doğrulama:

```bash
curl --fail --silent https://dymtal.avartech.net/health
```

## 5. YAREN cihaz kimliğini bir kez oluştur ve kaydet

Özel anahtar araçta kalır. YAREN bilgisayarında veya Raspberry Pi üzerinde şu
komutu çalıştırın:

```bash
python3 -m arac.ayar_cli web-key --device school-car
```

Komut iki dosya üretir:

- `~/.startech/yaren-device.json`: özel kimlik; yalnız araçta kalır ve hiçbir
  zaman CAM'e, Git'e, e-postaya veya sohbete yüklenmez.
- `~/.startech/yaren-device.pub.json`: paylaşılabilir açık kimlik.

Yalnız `.pub.json` dosyasını VPS'e kopyalayın. Örneğin YAREN bilgisayarından:

```bash
scp ~/.startech/yaren-device.pub.json startech-vps:/tmp/school-car.pub.json
```

VPS'te açık kimliği CAM veritabanına kaydedin:

```bash
cd /srv/startech-cam/app
sudo systemd-run --pipe --wait --collect --quiet \
  --uid=egemen --gid=egemen \
  --working-directory=/srv/startech-cam/app \
  --property=EnvironmentFile=/etc/startech-cam.env \
  /srv/startech-cam/venv/bin/flask --app wsgi:app \
  register-yaren-device --identity /tmp/school-car.pub.json --actor Egemen
rm /tmp/school-car.pub.json
```

`list-yaren-devices` komutu açık anahtarları göstermeden kayıt ve devre dışı
durumunu listeler. Anahtarın sızdığından şüphelenilirse araçta `web-key
--replace` ile yeni çift oluşturun ve VPS'te `rotate-yaren-device-key` kullanın.
Kayıp veya emekli bir cihaz için:

```bash
sudo systemd-run --pipe --wait --collect --quiet \
  --uid=egemen --gid=egemen \
  --working-directory=/srv/startech-cam/app \
  --property=EnvironmentFile=/etc/startech-cam.env \
  /srv/startech-cam/venv/bin/flask --app wsgi:app \
  disable-yaren-device --device school-car --actor Egemen
```

## 6. YAREN'den geçici web kodu iste

Kayıt tamamlandıktan sonra araçtaki YAREN tek kullanımlık kodu doğrudan ister:

```bash
python3 -m arac.ayar_cli web-code --server https://dymtal.avartech.net
```

İstek iki adımdır. CAM önce iki dakika geçerli tek kullanımlık bir rastgele değer
üretir. YAREN istek gövdesini Ed25519 özel anahtarıyla imzalar. CAM imzayı kayıtlı
açık anahtarla doğrular, rastgele değeri tüketir ve yalnız bundan sonra sekiz
karakterli erişim kodu üretir. Aynı imza veya rastgele değer tekrar kullanılamaz.

VPS kabuğundan elle kod üretme yolu acil yönetim seçeneği olarak kalır:

```bash
cd /srv/startech-cam/app
sudo systemd-run --pipe --wait --collect --quiet \
  --uid=egemen --gid=egemen \
  --working-directory=/srv/startech-cam/app \
  --property=EnvironmentFile=/etc/startech-cam.env \
  /srv/startech-cam/venv/bin/flask --app wsgi:app \
  issue-access-code --device school-car
```

Çıktı sekiz karakterli, tek kullanımlık ve 15 dakika geçerli koddur. Uzun
kodun düz metni veritabanında tutulmaz. İnternet uç noktası anonim kod üretmez;
yalnız önceden kaydedilmiş ve devre dışı olmayan YAREN anahtarları kabul edilir.

Kod üretildikten sonra YAREN aynı komut içinde dışarı doğru geçici bir HTTPS bağlantısı
açar ve kodun kalan süresi boyunca güvenli yapılandırma işlerini bekler. Terminali açık
tutun. Ctrl+C bağlantıyı CAM tarafında iptal eder. Bu kanal yalnız etkin yapılandırmayı
okuma, sınırlı yetenek raporu ve doğrulanmış yapılandırmayı **etkin olmayan** profil
olarak kurma işlemlerini kabul eder; motor, direksiyon, arm etme veya profil etkinleştirme
işlemi kabul etmez.

## 7. Güncelleme ve geri alma

Her güncellemeden önce paylaşılan veritabanını yedekleyin. Uygulama dizininde
yalnız doğrulanmış commit'i alın, bağımlılıkları eşitleyin ve hizmeti yeniden
başlatın:

```bash
sudo systemctl stop startech-cam.service
cp -a /srv/startech-cam/shared/cam.sqlite3 \
  "/srv/startech-cam/shared/cam.sqlite3.$(date -u +%Y%m%dT%H%M%SZ).bak"
cd /srv/startech-cam/app
git pull --ff-only origin master
/srv/startech-cam/venv/bin/pip install -r requirements.txt
sudo systemctl start startech-cam.service
curl --fail --silent http://127.0.0.1:8765/health
```

Başlatma sırasında mevcut SAC/MAC kalibrasyonları silinmez. Atölye komut türünü
ekleyen geçiş, `device_jobs` tablosunu aynı satırları kopyalayarak yeni kapalı işlem
listesiyle yeniden kurar; bu nedenle güncellemeden önce yukarıdaki veritabanı yedeği
zorunludur. Geri almak gerekirse hizmeti durdurun, önceki commit'e ayrı bir doğrulanmış
çalışma ağacı kurun ve yedek veritabanını kullanın. Çalışan paylaşılan veritabanını
körlemesine eski şemaya açmayın.
