// STARTECH-ADAM vehicle warning firmware
//
// Real serial protocol used by arac/adam.py. This firmware controls only the
// vehicle's RGB warning LED and passive buzzer; it has no motor connection.
// Target: Arduino Uno/Nano. Buzzer D2; common-anode RGB LED D3, D5 and D6.
// The exact installed wiring remains PHYSICALLY UNVERIFIED until checked at SCHOOL.

#include <Arduino.h>

const uint8_t BUZZER_PIN = 2;
const uint8_t RED_PIN = 3;
const uint8_t GREEN_PIN = 5;
const uint8_t BLUE_PIN = 6;
const bool COMMON_ANODE = true;

enum RunState : uint8_t {
  ADAM_OFF,
  ADAM_RUN_RECEIVED,
  ADAM_RUN_INITIATED,
  ADAM_RUN_HALT_NOCON
};

RunState currentState = ADAM_OFF;
bool buzzerMuted = false;
uint32_t stateStartedAt = 0;
uint32_t lastChirpAt = 0;
char commandBuffer[32];
uint8_t commandLength = 0;

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

void stopWarningSound() {
  noTone(BUZZER_PIN);
}

void chirp(uint16_t frequency, uint16_t durationMs) {
  if (!buzzerMuted) tone(BUZZER_PIN, frequency, durationMs);
}

void enterState(RunState nextState) {
  stopWarningSound();
  currentState = nextState;
  stateStartedAt = millis();
  lastChirpAt = stateStartedAt;
  switch (currentState) {
    case ADAM_OFF:
      setColor(0, 0, 0);
      break;
    case ADAM_RUN_RECEIVED:
      setColor(255, 150, 0);
      chirp(880, 120);
      break;
    case ADAM_RUN_INITIATED:
      setColor(0, 255, 0);
      chirp(1175, 180);
      break;
    case ADAM_RUN_HALT_NOCON:
      setColor(255, 0, 0);
      chirp(294, 300);
      break;
  }
}

void updateWarning() {
  const uint32_t now = millis();
  const uint32_t elapsed = now - stateStartedAt;
  switch (currentState) {
    case ADAM_OFF:
      setColor(0, 0, 0);
      break;
    case ADAM_RUN_RECEIVED: {
      const bool on = (elapsed % 1000) < 650;
      setColor(on ? 255 : 25, on ? 150 : 15, 0);
      if (now - lastChirpAt >= 2000) {
        lastChirpAt = now;
        chirp(880, 90);
      }
      break;
    }
    case ADAM_RUN_INITIATED:
      setColor(0, 255, 0);
      break;
    case ADAM_RUN_HALT_NOCON: {
      const uint16_t phase = elapsed % 1200;
      const bool on = phase < 180 || (phase >= 340 && phase < 520);
      setColor(on ? 255 : 0, 0, 0);
      if (now - lastChirpAt >= 2400) {
        lastChirpAt = now;
        chirp(294, 220);
      }
      break;
    }
  }
}

void acknowledge(const __FlashStringHelper* text) {
  Serial.println(text);
}

void handleCommand(const char* command) {
  if (strcmp(command, "PING") == 0) {
    acknowledge(F("ADAM_READY"));
  } else if (strcmp(command, "MUTE") == 0) {
    buzzerMuted = true;
    stopWarningSound();
    acknowledge(F("ADAM_MUTED"));
  } else if (strcmp(command, "UNMUTE") == 0) {
    buzzerMuted = false;
    acknowledge(F("ADAM_UNMUTED"));
  } else if (strcmp(command, "RUN_RECEIVED") == 0) {
    enterState(ADAM_RUN_RECEIVED);
    acknowledge(F("ADAM_RUN_RECEIVED"));
  } else if (strcmp(command, "RUN_INITIATED") == 0) {
    enterState(ADAM_RUN_INITIATED);
    acknowledge(F("ADAM_RUN_INITIATED"));
  } else if (strcmp(command, "RUN_HALT_NOCON") == 0) {
    enterState(ADAM_RUN_HALT_NOCON);
    acknowledge(F("ADAM_RUN_HALT_NOCON"));
  } else if (strcmp(command, "OFF") == 0) {
    enterState(ADAM_OFF);
    acknowledge(F("ADAM_OFF"));
  } else if (command[0] != '\0') {
    acknowledge(F("ADAM_UNKNOWN_COMMAND"));
  }
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());
    if (incoming == '\r') continue;
    if (incoming == '\n') {
      commandBuffer[commandLength] = '\0';
      handleCommand(commandBuffer);
      commandLength = 0;
      continue;
    }
    if (commandLength < sizeof(commandBuffer) - 1) {
      commandBuffer[commandLength++] = incoming;
    } else {
      commandLength = 0;
      acknowledge(F("ADAM_COMMAND_TOO_LONG"));
    }
  }
}

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  enterState(ADAM_OFF);
  Serial.begin(115200);
  acknowledge(F("ADAM_READY"));
}

void loop() {
  readSerialCommands();
  updateWarning();
}
