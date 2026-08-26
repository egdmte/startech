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

Also remove `Learn how to update your code →`; it is currently displayed as an action without an implemented destination.

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

Use the shared welcome pattern `Hello {name}` / `Merhaba {isim}`.

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

Use `Go back` / `Geri dön` for the remaining return action.

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
| SBC and services | Choose startup validation and enabled STARTECH modules. | TKB ve servisleri | Başlangıç onaylarını ve çalışan STARTECH modüllerini yönetin. |
| Camera | Choose capture, orientation and recognition intent. | Kamera | Yakalama, oranlama ve tespit hedeflerini değiştirin. |
| Drive and steering | Set command-loss policy and steering limits. | Sürüş ve dönüş | Kod kaybı ve dönüş limitlerini belirleyin. |
| Wheels | Set wheel correction and direction intent. | Tekerler | Teker dönüşü ve düzeltme oranlarını belirleyin. |

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

Status: wording completed; implementation pending.

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

Remaining camera labels:

| English | Turkish |
| --- | --- |
| Capture profile | Yakalama profili |
| Recognition sensitivity | Tespit hassasiyeti |
| Prioritize Raspberry Pi Camera before USB | USB'den önce Raspberry Pi kamerasını kullan |

## Page 7C — SBC and services editor

Status: wording approved; implementation pending.

The Turkish component name `TKB ve servisleri` replaces the earlier `TKD` wording throughout the component-selection page, checklist, accessibility labels, and editor.

Replace the existing repeated descriptions with these two paragraphs:

| Location | English | Turkish |
| --- | --- | --- |
| Component title | SBC and services | TKB ve servisleri |
| Implementation explanation | These options can be changed now, but the features will work once they are integrated into the car code. | Bu seçenekler şu anda değiştirilebilir ancak özellikler, araç koduna entegre edildiklerinde çalışacaktır. |
| Responsibility explanation | KERİM will only manage how the systems should operate; it will not change the car's own safety measures. | KERİM yalnızca sistemlerin nasıl çalışması gerektiğini yönetecektir; aracın kendi güvenlik önlemlerini değiştirmeyecektir. |

### Start-up approval

| English | Turkish |
| --- | --- |
| Approve everything manually | Her şeyi elle onayla |
| Manually approve startup only | Sadece başlangıcı elle onayla |
| Allow remote approval | Uzaktan onaylamaya izin ver |

### Service status

| English | Turkish |
| --- | --- |
| At startup | Açılışta |
| Manually | El ile |

### M3TH response

| English | Turkish |
| --- | --- |
| Errors end the run | Hatalar turu sonlandırır |
| Errors pause the run | Hatalar turu durdurur |
| Errors are only logged | Hatalar sadece kaydedilir |

| Location | English | Turkish |
| --- | --- | --- |
| Feature selector heading | Enabled features | Açık özellikler |

The STARTECH feature names remain language-neutral: `YAREN`, `ARDA`, `KASIM`, `KADER`, `KEREM`, `OSMAN`, and `M3TH`.

## Page 7D — Drive editor

Status: wording completed; implementation pending.

Replace the repeated existing description with this single explanation:

| Location | English | Turkish |
| --- | --- | --- |
| Component title | Command management | Komut yönetimi |
| Explanation | The settings here will be used to determine the calibration status; these options will not affect how the car operates. | Buradaki ayarlar kalibrasyonun durumunu belirlemek için kullanılacaktır; bu seçenekler aracın çalışmasını etkilemeyecektir. |
| Command-loss heading | When a command is lost | Komut kaybetme durumunda |
| Reject option | Reject the request | İsteği reddet |
| Stop option | Stop and wait | Durdur ve bekle |
| Previous-command option | Follow previous commands | Önceki komutlara uy |
| No-output option | No motor output | Motor çıkışı yok |
| Steering-only option | Turning only | Sadece dönüş |
| Full-output option | Full car control | Tam araç kontrolü |
| Center control | Driving center point | Sürüş orta noktası |
| Maximum-turn control | Maximum wheel turning angle | Azami teker dönme açısı |
| Full-output heading | Full driving requires approval. | Tam sürüş onay bekler. |
| Full-output acknowledgement | I approve this profile. | Bu profili onaylıyorum. |

Remove the second full-output checkbox and its corresponding server-side validation requirement:

- `I understand that KERİM does not arm or physically test the car.`

Use `Motor output mode` / `Motor çıkış modu` for the remaining output group heading.

## Page 7E — Wheels editor

Status: wording approved; implementation pending.

The latest `Tekerler` wording replaces `Tekerlekler` on the component-selection page, checklist, accessibility labels, and editor.

Replace the repeated existing description with this single explanation:

| Location | English | Turkish |
| --- | --- | --- |
| Component title | Wheels | Tekerler |
| Implementation explanation | The car will read these settings in future updates. | Araç bu ayarları ileriki güncellemelerde okuyacaktır. |
| Left diagram label | LEFT | SOL |
| Right diagram label | RIGHT | SAĞ |
| Left-correction control | Left correction | Sol düzeltmesi |
| Right-correction control | Right correction | Sağ düzeltmesi |
| Left-direction control | Left wheel direction | Sol teker yönü |
| Right-direction control | Right wheel direction | Sağ teker yönü |
| Camera-facing direction | Toward the camera | Kameraya doğru |
| Battery-facing direction | Toward the battery holders | Pil yataklarına doğru |

## Page 8 — SAC summary

Status: wording approved; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Welcome line | Hello {name} | Merhaba {isim} |
| Main heading | Calibration is about to be created. | Kalibrasyon oluşturulmak üzere. |
| Instructions | Please review the calibration before it is saved. | Lütfen kaydedilmeden önce kalibrasyonu gözden geçirin. |
| Name label | Name | İsim |
| Source label | Source | Kaynak |
| Schema label | Schema | Şema |
| Reviewed label | Reviewed | Değerlendirilenler |
| Schema-value pattern | Merged v{schema_version} / SAC Contract v{contract_version} | Birleşik v{şema_sürümü} / SAC sözleşmesi v{sözleşme_sürümü} |
| Empty reviewed value | empty | boş |
| Blocked heading | Cannot be created | Oluşturulamıyor |
| Missing-review label | Review required: | İncelenmesi gerekli: |
| Create action | Create | Oluştur |
| Return action | Go back | Geri dön |
| Review-region label | Calibration summary | Kalibrasyon özeti |
| Browser title | Review calibration · STARTECH | Kalibrasyonu incele |

## Page 9 — SAC created

Status: wording approved; implementation pending.

Reuse the approved summary-screen welcome line: `Hello {name}` / `Merhaba {isim}`.

| Location | English | Turkish |
| --- | --- | --- |
| Main heading | Created! | Oluşturuldu! |
| Created message | The calibration tagged {tag} has been created. | {etiket} etiketli kalibrasyon oluşturuldu. |
| MAC explanation | Some values cannot be changed through Service Assisted Calibration. | Servis Asistanlı Kalibrasyon üzerinden değiştirilemeyecek değerler yer alıyor. |
| MAC action | Edit {tag} with MAC | {etiket} etiketini MAC ile düzenle |
| Pi-transfer action | Send this inactive profile to the Pi | Bu inaktif profili Pi'ye gönder |
| Download action | Download the JSON | JSON'u indir |
| Menu action | Main Menu | Ana Menü |
| Transfer-status pattern | Sharing status: {status}. The profile is not active. | Paylaşım durumu: {durum}. Profil aktif değil. |
| Browser title | Created - STARTECH | Oluşturuldu - STARTECH |

## Page 10 — Start a MAC

Status: translation delegated and drafted; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Interface label | Manual Assisted Calibration - Interface v0.1 | Manuel Asistanlı Kalibrasyon - Arayüz v0.1 |
| Step label | Choose a source | Kaynak seç |
| Main heading | Please enter a name for this calibration. | Kalibrasyon için bir isim girin. |
| Ownership explanation | Your legal name determines the owner. The name helps organize versions and does not change the schema. | Yasal isminiz kalibrasyon sahibini belirler. Kalibrasyon ismi sürümleri düzenlemenize yardımcı olur ve şemayı değiştirmez. |
| Name field | Configuration name | Kalibrasyon ismi |
| Placeholder | MyMAC | Benim MAC'im |
| Source group | Starting point | Başlangıç noktası |
| Default source | Use the default model | Varsayılan modeli kullan |
| Previous source | Copy an old version | Eski bir sürümü kopyala |
| Previous-source label | Previous configuration | Önceki kalibrasyon |
| Upload source | Upload merged v2 JSON | Birleşik v2 JSON yükle |
| Car source | Load from the car | Arabadan yükle |
| YAREN requirement | YAREN connection required | YAREN bağlantısı gerekli |
| Submit action | Approve | Onayla |
| Return action | Go back | Geri dön |
| Browser title | New MAC · STARTECH | Yeni MAC · STARTECH |

## Page 11 — MAC editor

Status: translation delegated and drafted; implementation pending.

### Shared editor interface

| Location | English | Turkish |
| --- | --- | --- |
| Interface label | Manual Assisted Calibration - Interface v0.1 | Manuel Asistanlı Kalibrasyon - Arayüz v0.1 |
| Publish action | Review and publish | İncele ve yayımla |
| Editor label | MAC editor | MAC düzenleyici |
| Saved-state label | saved | kaydedildi |
| Variable action | Variable manager | Değişken yönetimi |
| Summary action | Review summary | Özeti incele |
| Save action | Save and continue | Kaydet ve devam et |
| Current-values action | Review current values | Mevcut değerleri incele |
| Unknown measurement | Unknown | Bilinmiyor |
| Missing measurement | Not measured | Ölçülmedi |
| Recorded measurement | Measured — evidence exists | Ölçüldü — kayıt mevcut |

The browser-title pattern remains `MAC · {section} · STARTECH`.

### Overview

| English | Turkish |
| --- | --- |
| Overview | Genel bakış |
| Configuration identity and ownership. | Kalibrasyon kimliği ve sahibi. |
| Configuration name | Kalibrasyon ismi |

### Camera

| English | Turkish |
| --- | --- |
| Camera | Kamera |
| Physical camera values used by the v1 calibration contract. | v1 kalibrasyon sözleşmesinde kullanılan fiziksel kamera değerleri. |
| Width | Genişlik |
| Height | Yükseklik |
| BGR output | BGR çıkışı |
| Rotate 180° | 180° döndür |

### Perspective

| English | Turkish |
| --- | --- |
| Perspective | Perspektif |
| Perspective points must match the measured resolution. | Perspektif noktaları ölçülen çözünürlükle eşleşmelidir. |
| Measured resolution [width, height] | Ölçülen çözünürlük [genişlik, yükseklik] |
| Source points | Kaynak noktaları |
| Top ROI ratio | Üst ROI oranı |

### Recognition

| English | Turkish |
| --- | --- |
| Recognition | Tespit |
| Lane-recognition thresholds and lighting profiles. | Şerit tespit eşikleri ve aydınlatma profilleri. |
| White lane profiles | Beyaz şerit profilleri |
| Profile thresholds | Profil eşikleri |
| Minimum signal | Asgari sinyal |
| Signal quality ratio | Sinyal kalite oranı |
| Default lane width | Varsayılan şerit genişliği |
| Continuity ratio | Süreklilik oranı |
| CLAHE limit | CLAHE limiti |
| CLAHE tile size | CLAHE kutucuk boyutu |

### Colors

| English | Turkish |
| --- | --- |
| Colors | Renkler |
| HSV ranges and minimum valid areas for detected objects. | Tespit edilen nesnelerin HSV aralıkları ve asgari geçerli alanları. |
| Color definitions | Renk tanımları |

### Motors

| English | Turkish |
| --- | --- |
| Motors | Motorlar |
| Motor calibration values. Use PHYSICALLY UNVERIFIED until they are measured on the car. | Motor kalibrasyon değerleri. Araçta ölçülene kadar FİZİKSEL OLARAK DOĞRULANMADI seçeneğini kullanın. |
| Measured | Ölçüldü |
| Left low trim | Sol düşük düzeltme |
| Left high trim | Sol yüksek düzeltme |
| Right low trim | Sağ düşük düzeltme |
| Right high trim | Sağ yüksek düzeltme |
| Dead-zone minimum PWM | Ölü bölge asgari PWM |
| Dead-zone % | Ölü bölge % |

### Steering

| English | Turkish |
| --- | --- |
| Steering | Dönüş |
| PD/PID controller values. | PD/PID denetleyici değerleri. |
| Integral maximum | Azami integral |
| Derivative cap | Türev sınırı |

`KP`, `KD`, and `KI` remain language-neutral.

### Speed

| English | Turkish |
| --- | --- |
| Speed | Hız |
| Minimum, target, and maximum PWM command percentages used by the car. | Aracın kullandığı asgari, hedef ve azami PWM komut yüzdeleri. |
| Minimum | Asgari |
| Target | Hedef |
| Maximum | Azami |
| Speed correction gain | Hız düzeltme kazancı |

### Event response

| English | Turkish |
| --- | --- |
| Event response | Olay tepkisi |
| Near-region threshold used by event handling. | Olay yönetiminde kullanılan yakın bölge eşiği. |
| Near ROI ratio | Yakın ROI oranı |

## Page 12 — Variable manager

Status: translation delegated and drafted; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Browser title | Variable manager · STARTECH | Değişken yönetimi · STARTECH |
| Main heading | Variable management | Değişken yönetimi |
| Instructions | Edit the merged v2 JSON directly. Invalid values will be rejected. | Birleşik v2 JSON'u doğrudan düzenleyin. Geçersiz değerler reddedilecektir. |
| Save action | Validate and save | Doğrula ve kaydet |
| Summary action | Review summary | Özeti incele |

## Page 13 — MAC summary

Status: translation delegated and drafted; implementation pending.

Reuse the approved Page 8 creation heading, instructions, create action, and return action.

| Location | English | Turkish |
| --- | --- | --- |
| Workflow label | Workflow | İş akışı |
| Source label | Source | Kaynak |
| Schema label | Schema | Şema |
| Saved-sections label | Saved sections | Kaydedilen bölümler |
| Sections heading | Sections | Bölümler |
| JSON preview | Validated merged JSON | Doğrulanmış birleşik JSON |
| Unused-contract value | not used | kullanılmıyor |
| Empty value | none | boş |
| Blocked heading | Cannot be created | Oluşturulamıyor |
| Missing-review heading | Review required | İnceleme gerekli |
| Missing-review message | Some sections still need review: {sections}. | Bazı bölümlerin hâlâ incelenmesi gerekiyor: {bölümler}. |
| Browser-title pattern | {workflow} summary · STARTECH | {iş_akışı} özeti · STARTECH |

## Page 14 — MAC created

Status: translation delegated and drafted; implementation pending.

Reuse the approved Page 9 created-screen copy. The created message includes the workflow: `{workflow} calibration tagged {tag} has been created.` / `{etiket} etiketli {iş_akışı} kalibrasyonu oluşturuldu.`

## Page 15 — Live SAC checks

Status: translation delegated and drafted; implementation pending.

This page can issue a real bounded motor command. Its countdown and physical setup warnings remain prominent.

| Location | English | Turkish |
| --- | --- | --- |
| Browser title | Live SAC checks · STARTECH | Canlı SAC kontrolleri · STARTECH |
| Main heading | Check the connected car. | Bağlı aracı kontrol edin. |
| Connected message | YAREN is connected. Camera checks use a physical frame; the motor check uses one short bounded command. | YAREN bağlı. Kamera kontrolleri fiziksel bir görüntü, motor kontrolü ise kısa ve sınırlı bir komut kullanır. |
| Disconnected message | No car is connected. Configuration can continue; physical status remains PHYSICALLY UNVERIFIED. | Araç bağlı değil. Yapılandırmaya devam edilebilir; fiziksel durum FİZİKSEL OLARAK DOĞRULANMADI olarak kalır. |
| Camera heading | Camera and lane recognition | Kamera ve şerit tespiti |
| Camera explanation | Results come from the selected profile and connected car. | Sonuçlar seçili profilden ve bağlı araçtan alınır. |
| Camera action | Run camera check | Kamera kontrolünü çalıştır |
| Workshop heading | Workshop motor check | Atölye motor kontrolü |
| Operator line | Operator: {name}. Maximum ±35% for 3 seconds. The active car profile will be used. | Operatör: {isim}. 3 saniye boyunca azami ±%35. Aracın aktif profili kullanılacak. |
| Observed status | OBSERVED PASS | GÖZLEMLENDİ |
| Unobserved status | PHYSICALLY UNVERIFIED | FİZİKSEL OLARAK DOĞRULANMADI |
| Left value | Left motor % | Sol motor % |
| Right value | Right motor % | Sağ motor % |
| Duration value | Duration in seconds | Süre, saniye |
| Inspection heading | Confirm the physical setup | Fiziksel kurulumu doğrulayın |
| Wheels condition | The wheels are secured or the car is restrained. | Tekerler sabitlendi veya araç hareket edemeyecek şekilde tutuluyor. |
| Motor condition | The motors and wiring are mounted. | Motorlar ve kablolar takılı. |
| Area condition | The movement area is clear and the power switch is reachable. | Hareket alanı boş ve güç anahtarına ulaşılabiliyor. |
| Countdown action | Start 7-second countdown | 7 saniyelik geri sayımı başlat |
| Countdown warning | LIVE MOTOR OUTPUT may start in {seconds} seconds. | CANLI MOTOR ÇIKIŞI {saniye} saniye içinde başlayabilir. |
| Cutoff instruction | Stay at the physical power cutoff. Cancel if the car is not secured and clear. | Fiziksel güç anahtarının yanında kalın. Araç sabit değilse veya alan boş değilse iptal edin. |
| Immediate action | Start now | Şimdi başlat |
| Cancel action | Cancel | İptal et |
| Command heading | Command {id} | Komut {kimlik} |
| Status label | Status | Durum |
| Queued warning | LIVE MOTOR OUTPUT IS QUEUED OR MAY BE ACTIVE. Stay at the power cutoff until it ends. | CANLI MOTOR ÇIKIŞI SIRADA VEYA ETKİN OLABİLİR. İşlem bitene kadar güç anahtarının yanında kalın. |
| Issued label | KERİM issued | KERİM gönderdi |
| Applied label | Applied | Uygulanan |
| Duration label | Duration | Süre |
| Stop label | Stop | Durdurma |
| Stop requested | requested | istendi |
| Missing stop record | not recorded | kaydedilmedi |
| Receipt explanation | Command record saved. Please refer to the car for more information. | Komut kaydı oluşturuldu. Daha fazla bilgi için araca bakın. |
| Expected observation | Movement matched | Hareket eşleşti |
| Unexpected observation | Wrong or not observed | Yanlış veya gözlemlenmedi |
| Continue note | Without a physical check: PHYSICALLY UNVERIFIED. | Fiziksel kontrol yapılmadıysa: FİZİKSEL OLARAK DOĞRULANMADI. |
| Continue action | Continue to SAC configuration | SAC yapılandırmasına devam et |

Capability-state labels:

| English | Turkish |
| --- | --- |
| LIVE | CANLI |
| RESPONDED | YANITLADI |
| UNAVAILABLE | KULLANILAMIYOR |
| FAILED | BAŞARISIZ |
| UNVERIFIED | DOĞRULANMADI |
| CONFIGURED | YAPILANDIRILDI |

## Page 16 — Start linked-camera calibration

Status: translation delegated and drafted; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Browser title | Live camera calibration · STARTECH | Canlı kamera kalibrasyonu · STARTECH |
| Main heading | Calibrate from the connected car | Bağlı araçtan kalibrasyon yap |
| Explanation | KERİM copies YAREN's active configuration and captures one real frame into a new profile. The existing profile remains unchanged. | KERİM, YAREN'in aktif yapılandırmasını kopyalar ve gerçek bir görüntüyü yeni bir profile kaydeder. Mevcut profil değişmez. |
| Name field | New profile name | Yeni profil ismi |
| Placeholder | Workshop camera calibration | Atölye kamera kalibrasyonu |
| Evidence heading | What this uses | Kullanılan veri |
| Evidence explanation | A real frame from the connected YAREN camera. Please refer to the car for more information. | Bağlı YAREN kamerasından gerçek bir görüntü. Daha fazla bilgi için araca bakın. |
| Continue action | Continue to live frame | Canlı görüntüye devam et |
| Return action | Go back | Geri dön |

## Page 17 — Live camera editor

Status: translation delegated and drafted; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Eyebrow | YAREN LIVE FRAME | YAREN CANLI GÖRÜNTÜ |
| Main heading | Perspective and HSV calibration | Perspektif ve HSV kalibrasyonu |
| Save explanation | Saving creates a new inactive profile. | Kaydetmek yeni ve inaktif bir profil oluşturur. |
| Waiting heading | Waiting for YAREN | YAREN bekleniyor |
| Job-status pattern | Job status: {status}. Keep YAREN connected with a camera available. | İş durumu: {durum}. YAREN'i kamera kullanılabilir şekilde bağlı tutun. |
| Failure heading | The frame was not captured | Görüntü yakalanamadı |
| Failure message | YAREN reported {status}. | YAREN şu durumu bildirdi: {durum}. |
| Request heading | Request a current frame | Güncel görüntü iste |
| Request explanation | KASIM captures one frame from the configured camera and returns it to KERİM. | KASIM, yapılandırılmış kameradan bir görüntü yakalar ve KERİM'e gönderir. |
| Initial request | Capture live frame | Canlı görüntü yakala |
| Repeat request | Request another live frame | Başka bir canlı görüntü iste |
| Cancel action | Cancel | İptal et |
| Source label | Source | Kaynak |
| Frame label | Frame | Görüntü |
| Resolution label | Resolution | Çözünürlük |
| Image alternative | Live YAREN camera frame | Canlı YAREN kamera görüntüsü |
| Perspective heading | Perspective points | Perspektif noktaları |
| Perspective instructions | Drag the four handles around the road: top-left, top-right, bottom-left, bottom-right. | Dört tutamacı yolun çevresine sürükleyin: sol üst, sağ üst, sol alt, sağ alt. |
| Mask heading | HSV mask preview | HSV maske önizlemesi |
| Mask explanation | White pixels match the selected recognition range; black pixels do not. | Beyaz pikseller seçilen tespit aralığıyla eşleşir; siyah pikseller eşleşmez. |
| Target label | Recognition target | Tespit hedefi |
| Lower H | Lower H | Alt H |
| Upper H | Upper H | Üst H |
| Lower S | Lower S | Alt S |
| Upper S | Upper S | Üst S |
| Lower V | Lower V | Alt V |
| Upper V | Upper V | Üst V |
| Result explanation | Creates one inactive KERİM calibration and queues the profile for YAREN. | Bir inaktif KERİM kalibrasyonu oluşturur ve profili YAREN için sıraya alır. |
| Create action | Create inactive profile | İnaktif profil oluştur |
| Discard action | Discard this frame | Bu görüntüyü sil |

`SHA-256` remains language-neutral.

## Page 18 — Version history

Status: translation delegated and drafted; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Browser title and heading | Version history | Sürüm geçmişi |
| Explanation | Finalized configurations cannot be overwritten. Download one or open it in MAC. | Tamamlanan kalibrasyonların üzerine yazılamaz. Kalibrasyonu indirin veya MAC ile açın. |
| Parent pattern | From {tag} | Kaynak: {etiket} |
| Download action | Download | İndir |
| MAC action | Open in MAC | MAC ile aç |
| Empty state | No finalized configurations exist yet. | Henüz tamamlanmış bir kalibrasyon yok. |
| Menu action | Main menu | Ana menü |

## Page 19 — FOS licenses

Status: translation delegated and drafted; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Browser title | FOS Licenses · KERİM | FOS Lisansları · KERİM |
| Main heading | Free and open-source software | Özgür ve açık kaynaklı yazılımlar |
| Introduction | Projects used by KERİM or published by STARTECH. | KERİM tarafından kullanılan veya STARTECH tarafından yayımlanan projeler. |
| Reicon description | KERİM uses Reicon 1.2.0 for interface action icons. | KERİM, arayüz işlem simgeleri için Reicon 1.2.0 kullanır. |
| 3awnt description | STARTECH's Third-Party Threat Analysis, Warning and Neutralize Threats tool. Development continues. | STARTECH Üçüncü Parti Tehdit Algılama, Uyarma ve Tehdit Nötrleştirme Aracı. Geliştirme devam ediyor. |
| Website action | Project website | Proje sitesi |
| Source action | Source code | Kaynak kodu |
| Return action | Return to KERİM | KERİM'e dön |

Keep the project names and licence identifiers `Reicon`, `3awnt`, `MIT`, and `GPL-3.0` unchanged. Remove the former role-comparison and security-guarantee disclaimers.

## Page 20 — Maintenance package

Status: translation delegated and drafted; implementation pending.

| Location | English | Turkish |
| --- | --- | --- |
| Browser title | Maintenance package · KERİM | Bakım paketi · KERİM |
| Main heading | Build a maintenance package. | Bakım paketi oluştur. |
| Explanation | KERİM bundles an exact committed car version with one calibration and provides a ZIP download. | KERİM, kaydedilmiş belirli bir araç sürümünü bir kalibrasyonla paketler ve ZIP olarak indirmenizi sağlar. |
| Uncommitted-files note | Uncommitted server files are excluded. | Sunucuda commit edilmemiş dosyalar pakete eklenmez. |
| Calibration selector | Calibration included in the package | Pakete eklenecek kalibrasyon |
| Compare action | Compare | Karşılaştır |
| Missing calibration | No completed calibration exists. Create or import one first. | Tamamlanmış kalibrasyon yok. Önce bir kalibrasyon oluşturun veya içe aktarın. |
| Comparison error | Source comparison unavailable. | Kaynak karşılaştırılamıyor. |
| Selected calibration | Selected calibration | Seçilen kalibrasyon |
| Server revision | Server revision | Sunucu sürümü |
| Repository revision | {repository} revision | {depo} sürümü |
| Cached revision | Cached {repository} revision — unavailable for selection | Önbellekteki {depo} sürümü — seçilemez |
| Dirty-server heading | The server has uncommitted files. | Sunucuda commit edilmemiş dosyalar var. |
| Dirty-server explanation | They are excluded; the package uses commit {commit}. | Bu dosyalar eklenmez; paket {commit} commit'ini kullanır. |
| Refresh failure | {repository} could not be refreshed. The server revision remains available. | {depo} yenilenemedi. Sunucu sürümü kullanılabilir. |
| Repository download | Download from {repository} ({commit}) | {depo} üzerinden indir ({commit}) |
| Server download | Download from server ({commit}) | Sunucudan indir ({commit}) |
| Build action | Build and download | Oluştur ve indir |
| Future server update | Server update — Will be implemented. | Sunucu güncellemesi — Uygulanacak. |
| Package explanation | The ZIP contains the selected code and calibration. Installation is a separate step. | ZIP, seçilen kodu ve kalibrasyonu içerir. Kurulum ayrı bir adımdır. |
| Progress heading | Preparing the package | Paket hazırlanıyor |
| Initial progress | Verifying the selected revision and calibration… | Seçilen sürüm ve kalibrasyon doğrulanıyor… |
| Server recheck | Rechecking the exact revision and calibration on the server… | Sunucudaki sürüm ve kalibrasyon yeniden kontrol ediliyor… |
| Complete progress | Package created and download started. | Paket oluşturuldu ve indirme başladı. |
| Cancelled progress | Package creation cancelled. | Paket oluşturma iptal edildi. |
| Failed progress | The package was not created. | Paket oluşturulamadı. |
| Missing download | No download was produced. | İndirme oluşturulmadı. |
| Cancel action | Cancel | İptal et |
| Return action | Return | Geri dön |

## Page 21 — Generic error

Status: translation delegated and drafted; implementation pending.

The error title and message are supplied by the failing operation and must use the selected interface language. The fixed return action is `Main menu` / `Ana menü`.

## Global status vocabulary

| English | Turkish |
| --- | --- |
| PHYSICALLY UNVERIFIED | FİZİKSEL OLARAK DOĞRULANMADI |
| Will be implemented. | Uygulanacak. |
| Please refer to the car for more information. | Daha fazla bilgi için araca bakın. |

Use these short states instead of adding a new explanatory disclaimer to each page.
