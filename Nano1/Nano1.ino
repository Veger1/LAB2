#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads; // Create an instance of the ADS1115

const int ledPin = 13; // Pin 13 is the onboard LED on many Arduino boards, remove


byte continu[] = {0x80, 0x06, 0x03, 0x77}; // Continuous measurement
byte laser_on[] = {0x80, 0x06, 0x05, 0x01, 0x74}; // Laser on
byte single[] = {0x80, 0x06, 0x02, 0x78}; // Single measurement
byte xfast[] = {0xFA, 0x04, 0x0A, 0x14, 0xE4}; // 20Hz
byte fast[] = {0xFA, 0x04, 0x0A, 0x0A, 0xEE}; // 10Hz
byte medium[] = {0xFA, 0x04, 0x0A, 0x05, 0xF3}; // 5Hz
byte slow[] = {0xFA, 0x04, 0x0A, 0x00, 0xF8}; // 1Hz

String inputString = ""; // String to store incoming bytes
const int MAX_BUFFER_SIZE = 32; // Maximum size of input buffer
byte inputBuffer[MAX_BUFFER_SIZE];
int bufferIndex = 0;

void setup()
{
  Serial.begin(19200);   // Serial communication with the computer
  Serial1.begin(9600);  // Serial1 for communication with the sensor
  ads.begin();
  ads.setGain(GAIN_TWOTHIRDS); 
  delay(100); // Allow time for initialization
  pinMode(ledPin, OUTPUT); // Initialize the LED pin as an output
  Serial1.write(continu, sizeof(continu));
  delay(100);
  Serial1.end(); // End communication if needed
}

void loop() 
{
  // Check if data is available from the sensor
  if (Serial1.available() > 0) {
    int result = ads.readADC_Differential_0_1();
    delay(20);
    while (Serial1.available()) {
      char incomingChar = Serial1.read();
      inputString += incomingChar; // Append incoming character to inputString
    }
    Serial.print(inputString);
    inputString = "";
    Serial.write('\r');
    Serial.print(result);
    Serial.write('\n');
  }

  // Check if data is available from the computer
  if (Serial.available() > 0) {
    char received = Serial.read();
    if (received == 'G') {
      Serial1.begin(9600); // Begin communication with the sensor
      digitalWrite(ledPin, HIGH);
    }
    else if (received == 'S') {
      Serial1.end(); // End communication with the sensor
      digitalWrite(ledPin, LOW);
    }
    else if (received == 'H') {
      Serial1.write(continu, sizeof(continu)); // Send continuous measurement command
    }
    else if (received == 'M') {
      Serial1.write(fast, sizeof(fast)); // Send fast measurement command
    }
    else if (received == 'L') {
      Serial1.write(medium, sizeof(medium)); // Send medium measurement command
    }
  }
}
