# KERİM interface copy

This file is the authoritative working record for KERİM interface wording and translation.
Future work must refer to this file instead of reconstructing approved copy from chat history.

## Working rules

- Review and approve the interface one page at a time.
- Retained English text stays unchanged unless the user explicitly replaces it.
- Add Turkish translations for retained text.
- When the user supplies new wording, correct only grammar and clarity before implementation.
- Keep the status `PHYSICALLY UNVERIFIED`.
- A feature that does not exist must say `Will be implemented.`
- An implemented feature without physical verification must say `Please refer to the car for more information.`
- Remove unnecessary defensive or legalistic commentary from ordinary interface copy.
- Do not implement this ledger piecemeal unless requested. Apply the approved copy after the page review is complete.

## Page 1 — Login

Status: wording approved; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | Calibrate your STARTECH instance | STARTECH aracınızı kalibre edin. |
| Description | Any car with a proper code can sideload new calibrations without a file transfer. | Yeterli koda sahip her araç, dosya paylaşımına gerek kalmadan kalibrasyon yükleyebilir. |
| Legal-name label | Your full legal name | Yasal isminiz |
| Password label | Password provided | Verilen şifre |
| Submit button | Log in | Giriş yap |
| Browser title | Calibrate your STARTECH instance · STARTECH | STARTECH Giriş Ekranı |

Remove from the page:

- `Sign in to continue securely →`

Still awaiting a decision:

- `Learn how to update your code →`

## Page 2 — Dashboard

Status: wording approved; implementation pending.

### Persistent account bar

| Location | English | Turkish |
| --- | --- | --- |
| Home | KERİM | KERİM |
| Connect action | Connect YAREN | YAREN'e bağlan |
| Connected state | Remote-controlled | Uzaktan erişimli |
| Logout action | Log out | Çıkış yap |

### Dashboard actions

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | Welcome to Kalibrasyon Erişim, Revizyon İnceleme Merkezi (KERİM) | Kalibrasyon Erişim, Revizyon İnceleme Merkezi'ne (KERİM) hoş geldiniz. |
| Instruction | Select an option to begin. | Başlamak için bir seçenek seçin. |
| SAC action | Create a SAC (Service Assisted Calibration) | Servis Asistanlı Kalibrasyon oluştur (SAC) |
| MAC action | Create a MAC (Manual Assisted Calibration) | Manuel Asistanlı Kalibrasyon oluştur (MAC) |
| Camera action | Calibrate the camera remotely | Kamerayı uzaktan yönet |
| YAREN connection action | Connect YAREN | YAREN'e bağlan |
| YAREN management action | Manage YAREN | YAREN ayarları |
| Vehicle package action | Build package for migration | Bakım paketi oluştur |
| Open-source action | FOS Licenses | FOS Lisansları |
| History action | Version history | Sürüm geçmişi |
| Diagnostic action | Download diagnostic bundle | Önyükleme örneğini indir |

### New-configuration message

| Case | English | Turkish |
| --- | --- | --- |
| Singular | Since your last login, 1 new configuration has been added. | Siz yokken 1 yeni kalibrasyon eklendi. |
| Plural | Since your last login, {count} new configurations have been added. | Siz yokken {count} yeni kalibrasyon eklendi. |

Implementation requirement: calculate this message from the configurations added since the user's previous login. Do not display the total number of configurations as though they were all new.

The browser title remains unchanged: `KERİM · STARTECH`.

## Page 3 — YAREN connection

Status: wording approved; implementation pending.

### Always visible

| Location | English | Turkish |
| --- | --- | --- |
| Reassurance | You can always change your mind. | Her zaman fikrinizi değiştirebilirsiniz. |

Still awaiting a decision:

- The `Welcome` and legal-name block.

### Disconnected state

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | Connect to YAREN for remote configuration. | Uzaktan kontrol için YAREN'e bağlan. |
| Instructions | In YAREN, select the first option and enter the one-time code here. | YAREN üzerinden ilk seçeneği seçin ve tek seferlik kodu buraya girin. |
| Skip action | Skip for now → | Atla → |

### Connected state

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | YAREN is connected. | YAREN bağlandı. |
| Availability explanation | YAREN will continue to work as long as the car is available and the process is not terminated. | YAREN, araç kullanılabilir olduğu ve işlem sonlandırılmadığı sürece çalışmaya devam eder. |
| Return action | Open KERİM | KERİM'i aç |
| Disconnect action | Disconnect YAREN | Bağlantıyı kes |

### Browser and accessibility text

| Location | English | Turkish |
| --- | --- | --- |
| Browser title | Prove that you possess the code · STARTECH | Aracın kodunun sizde olduğunu doğrulayın |
| Session label | Current session | Şimdiki oturum |
| School-logo alternative | STARTECH school mark | STARTECH okul logosu |
| Code-field label | Temporary YAREN web code | Geçici YAREN giriş kodu |
| Submit-button label | Verify web code | Giriş kodunu doğrula |

## Page 4 — SAC source selection

Status: wording approved; implementation pending.

Remove from the page:

- The `Abort` action. The existing `Go back` action already provides navigation away from the page.

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | Select a target for the calibration. | Kalibrasyon için bir hedef seçin. |
| Instructions | Please provide a starting point for this calibration. | Lütfen kalibrasyonun başlangıç noktasını belirleyin. |
| Car-source action | Update from the car | Arabadan yükle |
| Default-source action | Use the default model | Varsayılan modeli kullan |
| Previous-source action | Copy an old version | Eski bir sürümü kopyala |
| Version-selector label | Version to copy | Kopyalanacak sürüm |
| Browser title | Select a SAC target · STARTECH | SAC Kaynağı Seçin |

Still awaiting a Turkish translation:

- `Go back`

## Page 5 — Name the SAC

Status: wording approved; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | Please enter a name for this calibration. | Kalibrasyon için bir isim girin. |
| Explanation | Your legal name is used to determine the owner. Naming a calibration helps you organize it; it does not affect how STARTECH references calibrations. | Yasal isminiz, kalibrasyon sahibini belirlemek için kullanılır. Kalibrasyon isimleri işinizi kolaylaştırmak içindir; kod bu isimleri okumaz. |
| Submit action | Agree | Onayla |
| Change-source action | Choose another source | Başka bir hedef seç |
| Name-field label | Calibration name | Kalibrasyon ismi |
| Name-field placeholder | MySAC | Benim SAC'im |
| Progress label | SAC progress | SAC ilerlemesi |
| Browser title | Name this calibration · STARTECH | İsimlendirme |

## Page 6 — SAC component selection

Status: wording approved; implementation pending.

### Main instructions

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | Which part would you like to be assisted with? | Hangi parça hakkında yardım almak istiyorsunuz? |
| Instructions | Click or touch the relevant section to review what can be changed. | İlgili parçanın üzerine dokunarak veya tıklayarak nelerin değiştirilebileceğini görün. |

### Car sections

| Section | English description | Turkish section | Turkish description |
| --- | --- | --- | --- |
| Battery and power | Set minimum and maximum software speed limits. | Batarya ve güç | Maksimum ve minimum hız değerlerini ayarlayın. |
| SBC (Single-board Controller) and Services | Choose startup validation and enabled STARTECH modules. | TKD (Tek kartlı denetleyici) ve servisleri | Başlangıç onaylarını ve çalışan STARTECH modüllerini yönetin. |
| Camera | Choose capture, orientation and recognition intent. | Kamera | Yakalama, oranlama ve tespit hedeflerini değiştirin. |
| Drive and steering | Set command-loss policy and steering limits. | Sürüş ve dönüş | Kod kaybı ve dönüş limitlerini belirleyin. |
| Wheels | Set wheel correction and direction intent. | Tekerlekler | Tekerlek dönüşü ve düzeltme oranlarını belirleyin. |

Use these same approved section names in the checklist and accessibility labels. Do not introduce alternate component names for those locations.

### Selection states and actions

| Location | English | Turkish |
| --- | --- | --- |
| Empty-state heading | NO PARTS SELECTED | PARÇA SEÇİLMEDİ |
| Empty-state instructions | Select a blue area to inspect or edit that part. | İlgili mavi alana dokunarak bilgi alın. |
| Complete-state heading | ALL PARTS REVIEWED | TÜM PARÇALAR İNCELENDİ |
| Complete-state instructions | You can now review and create this calibration. | Bu kalibrasyonu inceleyebilir ve oluşturabilirsiniz. |
| Review action | Review calibration | Kalibrasyonu incele |
| Incomplete action | Review every section first | Önce tüm parçaları denetleyin |
| Browser title | Choose a car section · STARTECH | Araç parçası seç |

Reuse the already approved `SAC ilerlemesi` translation for the progress label.

## Page 7 — SAC editor shared copy

Status: wording approved; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Return action | Return to the car | Arabaya geri dön |
| Heading pattern | Edit {component} settings | {component} ayarlarını değiştir |
| Save action | Save changes and return | Kaydet ve devam et |
| Progress label | SAC progress | SAC ilerlemesi |
| Runtime-backed flag | RUNTIME-BACKED | SÜRÜŞ ONAYLI |
| Publishing-policy flag | PUBLISHING POLICY ONLY | PAYLAŞIM AMAÇLI |
| Recorded-intent flag | RECORDED INTENT ONLY | KAYIT AMAÇLI |
| Storage explanation | KERİM will save these settings in SAC v1 so they are not affected by later calibration versions. | KERİM bu ayarları, sonraki kalibrasyon sürümlerinden etkilenmemeleri için SAC v1'e kaydedecektir. |

The existing browser-title pattern remains unchanged: `SAC · {component} · STARTECH`.

## Page 7A — Power editor

Status: wording approved with the displayed unit corrected to match the vehicle code; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Component title | Power limits | Güç limitleri |
| Description | These settings are applied in the car. (See `ayarlar.hiz`.) | Bu ayarlar araçta uygulanır. (Bakınız: `ayarlar.hiz`.) |
| PWM explanation | These limits do not change the battery voltage. The driver uses a fixed 100 Hz PWM frequency; these controls change the minimum and maximum PWM command percentages that determine the duty cycle. | Bu limitler batarya voltajını değiştirmez. Sürücü sabit 100 Hz PWM frekansı kullanır; bu kontroller, görev oranını belirleyen asgari ve azami PWM komut yüzdelerini değiştirir. |
| Minimum control | Minimum speed | Asgari hız |
| Maximum control | Maximum speed | Azami hız |
| Scale minimum | 0% | 0% |
| Scale maximum | 100% | 100% |

Technical basis: `ayarlar.hiz` contains percentage-based PWM commands. The vehicle's PWM frequency is configured separately and is currently fixed at 100 Hz. Do not label these controls as Hertz.

## Page 7B — Camera editor

Status: wording partially approved; implementation pending.

Replace both existing camera implementation disclaimers with this single explanation:

| Location | English | Turkish |
| --- | --- | --- |
| Component title | Camera | Kamera |
| Implementation explanation | These options are not currently used by the car code. The settings here will take effect when their implementation is complete. You can continue changing them in the meantime. | Bu seçenekler şu anda araç kodunda kullanılmıyor. Buradaki ayarlar, ilgili kod tamamlandığında çalışacak. Bu süreç boyunca değişiklik yapmaya devam edebilirsiniz. |
| Orientation heading | Frame orientation | Görüntü yönü |
| Performance profile | 640×480 — maximum performance | 640×480 — Azami performans |
| Balanced profile | 1280×720 — balanced | 1280×720 — Dengeli |
| Quality profile | 1920×1080 — maximum quality | 1920×1080 — Azami kalite |
| Minimum sensitivity | Conservative | Asgari |
| Balanced sensitivity | Balanced | Dengeli |
| Maximum sensitivity | Sensitive | Azami |

The orientation values remain language-neutral: `0°`, `90°`, `180°`, and `270°`.

Still awaiting Turkish translations:

- `Capture profile`
- `Recognition sensitivity`
- `Prioritize Raspberry Pi Camera before USB`
