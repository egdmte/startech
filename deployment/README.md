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

## 5. YAREN erişim kodu üret

İlk sürümde kod üretimi yalnız yetkili VPS kabuğundan yapılır. Bu, kimlik
doğrulaması olmayan bir internet uç noktası açılmasını engeller:

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
vadede YAREN entegrasyonu ayrı, kimliği doğrulanmış bir protokol olarak
planlanmalıdır; genel internete anonim kod üretme uç noktası açılmamalıdır.
