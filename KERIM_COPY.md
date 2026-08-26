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
