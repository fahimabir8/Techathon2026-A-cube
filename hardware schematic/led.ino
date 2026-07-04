// LED pins
const int LED_PINS[5] = {21, 5, 17, 2, 15};

// Button pins (change these to match your wiring)
const int BUTTON_PINS[5] = {34, 35, 25, 14, 13};

bool ledState[5] = {false, false, false, false, false};
int lastButtonState[5] = {LOW, LOW, LOW, LOW, LOW};

void setup() {
  for (int i = 0; i < 5; i++) {
    pinMode(LED_PINS[i], OUTPUT);
    pinMode(BUTTON_PINS[i], INPUT);   // Use INPUT_PULLUP if using internal pull-up
  }
}

void loop() {
  for (int i = 0; i < 5; i++) {

    int buttonState = digitalRead(BUTTON_PINS[i]);

    // Detect button press
    if (buttonState == HIGH && lastButtonState[i] == LOW) {
      ledState[i] = !ledState[i];
      digitalWrite(LED_PINS[i], ledState[i]);
    }

    lastButtonState[i] = buttonState;
  }

  delay(50);   // Simple debounce
}