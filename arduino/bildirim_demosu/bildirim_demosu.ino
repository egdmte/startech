// MEB Robot - RGB LED ve pasif buzzer BILDIRIM DEMOSU
// Bu dosya arabanin uretim kodu veya guvenlik sistemi degildir.
// Renk ve ses adaylarini karsilastirir; motorlara veya Pi'ye baglanmaz.
// Hedef: Arduino Uno/Nano. Buzzer D2; RGB LED D3, D5, D6.

#include <Arduino.h>

const uint8_t BUZZER_PIN = 2;
const uint8_t RED_PIN = 3;
const uint8_t GREEN_PIN = 5;
const uint8_t BLUE_PIN = 6;
const bool COMMON_ANODE = true;  // Ortak katot icin false yapin.

struct Note { uint16_t frequency, durationMs, pauseMs; };

template <typename T, size_t N>
constexpr size_t arrayLength(const T (&)[N]) { return N; }

enum Notification : uint8_t {
  OFF, STARTING, PREPARING, READY, WAITING_FOR_GREEN, RUN_STARTED,
  TASK_DETECTED, MANDATORY_WAIT, MANEUVER, TASK_SUCCESS, COURSE_COMPLETE,
  LANE_LOST, CAMERA_OR_CONFIG_ERROR, SHUTTING_DOWN, SAFE_TO_POWER_OFF,
  CALIBRATION_ACTIVE, VALUE_SAVED, INVALID_MEASUREMENT, WRITING_FILE,
  APPLYING_UPDATE, HARDWARE_TEST, MANUAL_COLOR
};

Notification currentNotification = OFF;
uint32_t notificationStartedAt = 0;
uint32_t lastPeriodicSoundAt = 0;
const Note* currentMelody = nullptr;
size_t currentMelodyLength = 0, currentNoteIndex = 0;
uint32_t notePhaseStartedAt = 0;
bool noteIsSounding = false;
bool demoTourActive = false;
size_t demoTourIndex = 0;
uint32_t demoStepStartedAt = 0;
int8_t lastHardwareTestStep = -1;

const Note STARTING_MELODY[] = {
  {392, 110, 35}, {523, 110, 35}, {659, 110, 35}, {784, 230, 0}
};
const Note READY_MELODY[] = {{659, 100, 45}, {988, 190, 0}};
const Note WAITING_MELODY[] = {{740, 75, 80}, {740, 75, 0}};
const Note RUN_STARTED_MELODY[] = {{1175, 120, 0}};
const Note TASK_DETECTED_MELODY[] = {{880, 55, 0}};
const Note MANEUVER_MELODY[] = {{587, 100, 0}};
const Note SUCCESS_MELODY[] = {{659, 90, 35}, {988, 180, 0}};
const Note COURSE_COMPLETE_MELODY[] = {
  {523, 90, 30}, {659, 90, 30}, {784, 90, 30}, {1047, 260, 0}
};
const Note LANE_LOST_MELODY[] = {{330, 100, 0}};
const Note ERROR_MELODY[] = {
  {330, 120, 70}, {294, 120, 70}, {262, 300, 0}
};
const Note SHUTDOWN_MELODY[] = {{659, 130, 50}, {392, 250, 0}};
const Note POWER_OFF_MELODY[] = {{262, 260, 0}};
const Note CALIBRATION_MELODY[] = {{784, 70, 65}, {784, 70, 0}};
const Note SAVED_MELODY[] = {{1319, 75, 0}};
const Note INVALID_MEASUREMENT_MELODY[] = {{220, 170, 0}};
const Note PERIODIC_TICK_MELODY[] = {{880, 35, 0}};

struct DemoStep { Notification notification; uint16_t durationMs; };
const DemoStep DEMO_TOUR[] = {
  {STARTING, 2600}, {PREPARING, 2200}, {READY, 2200},
  {WAITING_FOR_GREEN, 2400}, {RUN_STARTED, 1800},
  {TASK_DETECTED, 2000}, {MANDATORY_WAIT, 2600}, {MANEUVER, 2200},
  {TASK_SUCCESS, 2200}, {COURSE_COMPLETE, 3000}, {LANE_LOST, 2200},
  {CAMERA_OR_CONFIG_ERROR, 3000}, {CALIBRATION_ACTIVE, 2200},
  {VALUE_SAVED, 1800}, {INVALID_MEASUREMENT, 2000},
  {WRITING_FILE, 2200}, {APPLYING_UPDATE, 2200},
  {SHUTTING_DOWN, 2400}, {SAFE_TO_POWER_OFF, 2400}
};

void setColor(uint8_t red, uint8_t green, uint8_t blue) {
  if (COMMON_ANODE) {
    analogWrite(RED_PIN, 255 - red);
    analogWrite(GREEN_PIN, 255 - green);
    analogWrite(BLUE_PIN, 255 - blue);
  } else {
    analogWrite(RED_PIN, red);
    analogWrite(GREEN_PIN, green);
    analogWrite(BLUE_PIN, blue);
  }
}

void turnLedOff() { setColor(0, 0, 0); }

void stopMelody() {
  noTone(BUZZER_PIN);
  currentMelody = nullptr;
  currentMelodyLength = currentNoteIndex = 0;
  noteIsSounding = false;
}

void startMelody(const Note* melody, size_t length) {
  stopMelody();
  currentMelody = melody;
  currentMelodyLength = length;
  notePhaseStartedAt = millis();
}

bool melodyIsActive() { return currentMelody != nullptr; }

void updateMelody() {
  if (!melodyIsActive()) return;
  if (currentNoteIndex >= currentMelodyLength) { stopMelody(); return; }
  const uint32_t now = millis();
  const Note& note = currentMelody[currentNoteIndex];
  if (!noteIsSounding) {
    if (note.frequency > 0) tone(BUZZER_PIN, note.frequency);
    notePhaseStartedAt = now;
    noteIsSounding = true;
    return;
  }
  const uint32_t elapsed = now - notePhaseStartedAt;
  if (elapsed >= note.durationMs) noTone(BUZZER_PIN);
  if (elapsed >= static_cast<uint32_t>(note.durationMs) + note.pauseMs) {
    currentNoteIndex++;
    noteIsSounding = false;
    if (currentNoteIndex >= currentMelodyLength) stopMelody();
  }
}

uint8_t breathingBrightness(uint32_t now, uint16_t periodMs,
                            uint8_t minimum, uint8_t maximum) {
  const uint32_t halfPeriod = periodMs / 2;
  uint32_t phase = now % periodMs;
  if (phase > halfPeriod) phase = periodMs - phase;
  return minimum + static_cast<uint32_t>(maximum - minimum) * phase / halfPeriod;
}

bool isOnDuring(uint32_t elapsed, uint16_t cycleMs,
                uint16_t onStartMs, uint16_t onEndMs) {
  const uint16_t phase = elapsed % cycleMs;
  return phase >= onStartMs && phase < onEndMs;
}

void printNotificationDescription(Notification n) {
  Serial.println();
  Serial.print(F("Aktif bildirim: "));
  switch (n) {
    case OFF: Serial.println(F("KAPALI - LED ve buzzer kapali.")); break;
    case STARTING: Serial.println(F("ACILIS - Camgobegi nabiz ve yukselen melodi.")); break;
    case PREPARING: Serial.println(F("HAZIRLANIYOR - Sessiz mavi nefes.")); break;
    case READY: Serial.println(F("HAZIR - Sabit yesil ve iki yukselen nota.")); break;
    case WAITING_FOR_GREEN: Serial.println(F("YESIL BEKLENIYOR - Sari nabiz ve cift bip.")); break;
    case RUN_STARTED: Serial.println(F("YARIS BASLADI - Beyaz flas ve kisa tiz ses.")); break;
    case TASK_DETECTED: Serial.println(F("GOREV ALGILANDI - Turuncu cift flas.")); break;
    case MANDATORY_WAIT: Serial.println(F("ZORUNLU BEKLEME - Yavas sari yanip sonme ve seyrek tik.")); break;
    case MANEUVER: Serial.println(F("MANEVRA - Mor nefes ve baslangic sesi.")); break;
    case TASK_SUCCESS: Serial.println(F("GOREV BASARILI - Yesil cift flas ve yukselen ses.")); break;
    case COURSE_COMPLETE: Serial.println(F("PARKUR TAMAMLANDI - Yesil uclu flas ve kisa fanfar.")); break;
    case LANE_LOST: Serial.println(F("SERIT GECICI KAYIP - Hizli turuncu flas ve alcak bip.")); break;
    case CAMERA_OR_CONFIG_ERROR: Serial.println(F("KAMERA/AYAR HATASI - Kirmizi uclu flas ve uc alcak nota.")); break;
    case SHUTTING_DOWN: Serial.println(F("KAPANIYOR - Sonen mavi ve alcalan iki nota.")); break;
    case SAFE_TO_POWER_OFF: Serial.println(F("GUC KAPATILABILIR - Sabit mavi ve tek onay sesi.")); break;
    case CALIBRATION_ACTIVE: Serial.println(F("KALIBRASYON - Mavi nefes ve cift bip.")); break;
    case VALUE_SAVED: Serial.println(F("DEGER KAYDEDILDI - Tek yesil flas ve tiz tik.")); break;
    case INVALID_MEASUREMENT: Serial.println(F("GECERSIZ OLCUM - Tek kirmizi flas ve alcak ses.")); break;
    case WRITING_FILE: Serial.println(F("DOSYA YAZILIYOR - Sessiz beyaz/mavi gecis.")); break;
    case APPLYING_UPDATE: Serial.println(F("GUNCELLEME UYGULANIYOR - Sessiz mor nefes.")); break;
    case HARDWARE_TEST: Serial.println(F("DONANIM TESTI - R, G, B ve buzzer sirayla.")); break;
    case MANUAL_COLOR: Serial.println(F("ELLE RENK TESTI.")); break;
  }
}

void activateNotification(Notification n, bool cancelTour = true) {
  if (cancelTour) demoTourActive = false;
  stopMelody();
  turnLedOff();
  currentNotification = n;
  notificationStartedAt = millis();
  lastPeriodicSoundAt = notificationStartedAt;
  lastHardwareTestStep = -1;
  switch (n) {
    case STARTING: startMelody(STARTING_MELODY, arrayLength(STARTING_MELODY)); break;
    case READY: startMelody(READY_MELODY, arrayLength(READY_MELODY)); break;
    case WAITING_FOR_GREEN: startMelody(WAITING_MELODY, arrayLength(WAITING_MELODY)); break;
    case RUN_STARTED: startMelody(RUN_STARTED_MELODY, arrayLength(RUN_STARTED_MELODY)); break;
    case TASK_DETECTED: startMelody(TASK_DETECTED_MELODY, arrayLength(TASK_DETECTED_MELODY)); break;
    case MANEUVER: startMelody(MANEUVER_MELODY, arrayLength(MANEUVER_MELODY)); break;
    case TASK_SUCCESS: startMelody(SUCCESS_MELODY, arrayLength(SUCCESS_MELODY)); break;
    case COURSE_COMPLETE: startMelody(COURSE_COMPLETE_MELODY, arrayLength(COURSE_COMPLETE_MELODY)); break;
    case LANE_LOST: startMelody(LANE_LOST_MELODY, arrayLength(LANE_LOST_MELODY)); break;
    case CAMERA_OR_CONFIG_ERROR: startMelody(ERROR_MELODY, arrayLength(ERROR_MELODY)); break;
    case SHUTTING_DOWN: startMelody(SHUTDOWN_MELODY, arrayLength(SHUTDOWN_MELODY)); break;
    case SAFE_TO_POWER_OFF: startMelody(POWER_OFF_MELODY, arrayLength(POWER_OFF_MELODY)); break;
    case CALIBRATION_ACTIVE: startMelody(CALIBRATION_MELODY, arrayLength(CALIBRATION_MELODY)); break;
    case VALUE_SAVED: startMelody(SAVED_MELODY, arrayLength(SAVED_MELODY)); break;
    case INVALID_MEASUREMENT: startMelody(INVALID_MEASUREMENT_MELODY, arrayLength(INVALID_MEASUREMENT_MELODY)); break;
    default: break;
  }
  printNotificationDescription(n);
}

void updateHardwareTest(uint32_t elapsed) {
  const int8_t step = (elapsed / 900) % 5;
  if (step == lastHardwareTestStep) return;
  lastHardwareTestStep = step;
  stopMelody();
  switch (step) {
    case 0: Serial.println(F("[Test] Kirmizi kanal")); setColor(255, 0, 0); break;
    case 1: Serial.println(F("[Test] Yesil kanal")); setColor(0, 255, 0); break;
    case 2: Serial.println(F("[Test] Mavi kanal")); setColor(0, 0, 255); break;
    case 3: Serial.println(F("[Test] Beyaz: uc kanal birlikte")); setColor(255, 255, 255); break;
    case 4:
      Serial.println(F("[Test] Pasif buzzer: 440 Hz"));
      turnLedOff();
      tone(BUZZER_PIN, 440, 350);
      break;
  }
}

void updateNotificationEffects() {
  const uint32_t now = millis();
  const uint32_t elapsed = now - notificationStartedAt;
  uint8_t level;
  switch (currentNotification) {
    case OFF: turnLedOff(); break;
    case STARTING:
      level = breathingBrightness(elapsed, 1400, 20, 255); setColor(0, level, level); break;
    case PREPARING:
      level = breathingBrightness(elapsed, 1800, 10, 210); setColor(0, 0, level); break;
    case READY: setColor(0, 255, 0); break;
    case WAITING_FOR_GREEN:
      level = breathingBrightness(elapsed, 1200, 35, 255); setColor(level, level * 3 / 4, 0); break;
    case RUN_STARTED:
      if (elapsed < 350) setColor(255, 255, 255); else setColor(0, 255, 0); break;
    case TASK_DETECTED:
      if (isOnDuring(elapsed, 1300, 0, 160) || isOnDuring(elapsed, 1300, 300, 460)) setColor(255, 80, 0);
      else turnLedOff();
      break;
    case MANDATORY_WAIT:
      if ((elapsed % 1400) < 650) setColor(255, 170, 0); else turnLedOff();
      if (now - lastPeriodicSoundAt >= 2800 && !melodyIsActive()) {
        lastPeriodicSoundAt = now;
        startMelody(PERIODIC_TICK_MELODY, arrayLength(PERIODIC_TICK_MELODY));
      }
      break;
    case MANEUVER:
      level = breathingBrightness(elapsed, 1100, 20, 230); setColor(level, 0, level); break;
    case TASK_SUCCESS:
      if (isOnDuring(elapsed, 1500, 0, 180) || isOnDuring(elapsed, 1500, 340, 520)) setColor(0, 255, 0);
      else turnLedOff();
      break;
    case COURSE_COMPLETE:
      if (isOnDuring(elapsed, 1900, 0, 180) || isOnDuring(elapsed, 1900, 320, 500) || isOnDuring(elapsed, 1900, 640, 820)) setColor(0, 255, 0);
      else turnLedOff();
      break;
    case LANE_LOST:
      if ((elapsed % 320) < 150) setColor(255, 70, 0); else turnLedOff(); break;
    case CAMERA_OR_CONFIG_ERROR:
      if (isOnDuring(elapsed, 1800, 0, 220) || isOnDuring(elapsed, 1800, 380, 600) || isOnDuring(elapsed, 1800, 760, 980)) setColor(255, 0, 0);
      else turnLedOff();
      break;
    case SHUTTING_DOWN:
      level = 255 - static_cast<uint8_t>((elapsed % 1600) * 255 / 1600); setColor(0, 0, level); break;
    case SAFE_TO_POWER_OFF: setColor(0, 0, 255); break;
    case CALIBRATION_ACTIVE:
      level = breathingBrightness(elapsed, 1500, 15, 255); setColor(0, 0, level); break;
    case VALUE_SAVED:
      if ((elapsed % 1200) < 260) setColor(0, 255, 0); else turnLedOff(); break;
    case INVALID_MEASUREMENT:
      if ((elapsed % 1400) < 320) setColor(255, 0, 0); else turnLedOff(); break;
    case WRITING_FILE:
      if ((elapsed % 900) < 450) setColor(255, 255, 255); else setColor(0, 0, 180); break;
    case APPLYING_UPDATE:
      level = breathingBrightness(elapsed, 1300, 20, 220); setColor(level, 0, level); break;
    case HARDWARE_TEST: updateHardwareTest(elapsed); break;
    case MANUAL_COLOR: break;  // Yeni komuta kadar ayni renk kalir.
  }
}

void startDemoTour() {
  demoTourActive = true;
  demoTourIndex = 0;
  demoStepStartedAt = millis();
  Serial.println(F("\n=== OTOMATIK TANITIM BASLADI ==="));
  activateNotification(DEMO_TOUR[0].notification, false);
}

void updateDemoTour() {
  if (!demoTourActive) return;
  const uint32_t now = millis();
  if (now - demoStepStartedAt < DEMO_TOUR[demoTourIndex].durationMs) return;
  demoTourIndex++;
  if (demoTourIndex >= arrayLength(DEMO_TOUR)) {
    demoTourActive = false;
    Serial.println(F("=== OTOMATIK TANITIM BITTI ==="));
    activateNotification(OFF);
    return;
  }
  demoStepStartedAt = now;
  activateNotification(DEMO_TOUR[demoTourIndex].notification, false);
}

void setManualColor(uint8_t red, uint8_t green, uint8_t blue,
                    const __FlashStringHelper* name) {
  demoTourActive = false;
  stopMelody();
  currentNotification = MANUAL_COLOR;
  notificationStartedAt = millis();
  setColor(red, green, blue);
  Serial.print(F("Elle renk testi: "));
  Serial.println(name);
}

void printMenu() {
  Serial.println(F("\n========== BILDIRIM DEMOSU =========="));
  Serial.println(F("0 Kapali | 1 Acilis | 2 Hazirlaniyor | 3 Hazir"));
  Serial.println(F("4 Yesil bekle | 5 Yaris basladi | 6 Gorev algilandi"));
  Serial.println(F("7 Zorunlu bekle | 8 Manevra | 9 Gorev basarili"));
  Serial.println(F("F Parkur bitti | L Serit kayip | E Kamera/ayar hatasi"));
  Serial.println(F("K Kapaniyor | U Guc kapatilabilir | C Kalibrasyon"));
  Serial.println(F("S Deger kaydi | I Gecersiz olcum | W Dosya yazma"));
  Serial.println(F("G Guncelleme | X Donanim testi | D Otomatik tanitim"));
  Serial.println(F("r/g/b/y/c/m/w Dogrudan renk | ? Menu"));
  Serial.println(F("Buyuk ve kucuk harfler farkli komutlardir."));
}

void handleCommand(char command) {
  switch (command) {
    case '0': activateNotification(OFF); break;
    case '1': activateNotification(STARTING); break;
    case '2': activateNotification(PREPARING); break;
    case '3': activateNotification(READY); break;
    case '4': activateNotification(WAITING_FOR_GREEN); break;
    case '5': activateNotification(RUN_STARTED); break;
    case '6': activateNotification(TASK_DETECTED); break;
    case '7': activateNotification(MANDATORY_WAIT); break;
    case '8': activateNotification(MANEUVER); break;
    case '9': activateNotification(TASK_SUCCESS); break;
    case 'F': activateNotification(COURSE_COMPLETE); break;
    case 'L': activateNotification(LANE_LOST); break;
    case 'E': activateNotification(CAMERA_OR_CONFIG_ERROR); break;
    case 'K': activateNotification(SHUTTING_DOWN); break;
    case 'U': activateNotification(SAFE_TO_POWER_OFF); break;
    case 'C': activateNotification(CALIBRATION_ACTIVE); break;
    case 'S': activateNotification(VALUE_SAVED); break;
    case 'I': activateNotification(INVALID_MEASUREMENT); break;
    case 'W': activateNotification(WRITING_FILE); break;
    case 'G': activateNotification(APPLYING_UPDATE); break;
    case 'X': activateNotification(HARDWARE_TEST); break;
    case 'D': startDemoTour(); break;
    case 'r': setManualColor(255, 0, 0, F("kirmizi")); break;
    case 'g': setManualColor(0, 255, 0, F("yesil")); break;
    case 'b': setManualColor(0, 0, 255, F("mavi")); break;
    case 'y': setManualColor(255, 180, 0, F("sari")); break;
    case 'c': setManualColor(0, 255, 255, F("camgobegi")); break;
    case 'm': setManualColor(255, 0, 255, F("mor")); break;
    case 'w': setManualColor(255, 255, 255, F("beyaz")); break;
    case '?': printMenu(); break;
    default:
      Serial.print(F("Gecersiz komut: "));
      Serial.println(command);
      Serial.println(F("Komut listesi icin '?' gonderin."));
      break;
  }
}

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  Serial.begin(115200);
  stopMelody();
  turnLedOff();
  Serial.println(F("MEB Robot bildirim deneme araci hazir."));
  Serial.println(F("Bu kod motorlari kontrol etmez."));
  printMenu();
  activateNotification(OFF);
}

void loop() {
  updateMelody();
  updateNotificationEffects();
  updateDemoTour();
  while (Serial.available() > 0) {
    const char command = Serial.read();
    if (command == '\n' || command == '\r' || command == ' ') continue;
    handleCommand(command);
  }
}
