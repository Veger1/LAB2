#include <Adafruit_ADS1X15.h>
Adafruit_ADS1115 ads;  // Create an instance of the ADS1115

const int MAX_MESSAGE_LENGTH = 11;  // Maximum possible message length
uint8_t messageBuffer[MAX_MESSAGE_LENGTH];
int bufferIndex = 0;
bool lookingForStart = true;
bool laserMeasure = false;
bool encoderMeasure = false;
bool state = true;

const int encoderPinA = 7;
const int encoderPinB = 8;  // pin A and B must be on different interrupt vector

volatile long encoderPosition = 0;
volatile int lastEncoded = 0;
String inputString = "";
volatile bool commandReceived = false;
byte laseron[] = { 0x80, 0x06, 0x05, 0x01, 0x74 };
byte continu[] = {0x80, 0x06, 0x03, 0x77}; 

int result;
// int command;
int delayTime = 100;

enum MessageType {
  UNKNOWN,
  TYPE_80,  // Starts with 0x80 0x06
  TYPE_FA   // Starts with 0xFA
};
MessageType currentMessageType = UNKNOWN;

void setup() {
  Serial.begin(19200);
  USART0.CTRLA |= (1 << USART_RXCIE_bp);
  Serial1.begin(9600);
  Serial1.write(continu, sizeof(continu));
  Serial1.end();

  ads.begin();
  ads.setGain(GAIN_TWOTHIRDS);

  pinMode(encoderPinA, INPUT);
  pinMode(encoderPinB, INPUT);
  digitalWrite(encoderPinA, HIGH);
  digitalWrite(encoderPinB, HIGH);
}

void loop() {
  if (laserMeasure) {
    //forwardSerialToSerial1();
    measureWithLaser();
  }
  if (encoderMeasure) {
    measureWithEncrEncoder();
  }
  if (Serial.available() > 0) {
    char command = Serial.read();
    stateControl(command);
  }
}

void stateControl(char command) {
  switch (command) {
    case 'G': // ON button
      if (state) {
        laserMeasure = true;
        Serial1.begin(9600);
      } else {
        encoderMeasure = true;
      }
      break;

    case 'S': // OFF button
      if (state) {
        laserMeasure = false;
        Serial1.end();
      } else {
        encoderMeasure = false;
      }
      break;

    case 'E': // Switch to incremental encoder
      if (!laserMeasure || state) {
        state = false;
        attachInterrupt(digitalPinToInterrupt(encoderPinA), updateEncoder, CHANGE);  
        attachInterrupt(digitalPinToInterrupt(encoderPinB), updateEncoder, CHANGE);
      }
      break;

    case 'L': // Switch to laser
      if (!encoderMeasure || !state) {
        state = true;
        detachInterrupt(digitalPinToInterrupt(encoderPinA));
        detachInterrupt(digitalPinToInterrupt(encoderPinB));
      }
      break;
    case 'R': // Reset the resolution
      if (state) {
        Serial1.write(continu, sizeof(continu));
      }
      
  }
}

void measureWithEncrEncoder() {
  result = ads.readADC_Differential_0_1();
  Serial.print(encoderPosition);
  Serial.print('\r');
  Serial.print(result);
  Serial.print('\n');
  delay(delayTime);
}

void measureWithLaser() {
  if (Serial1.available() > 0) {
    uint8_t incomingByte = Serial1.read();
    // Serial.print(incomingByte, HEX);

    if (lookingForStart) {
      // Detect the start of a message
      if (incomingByte == 0x80) {
        currentMessageType = TYPE_80;
        result = ads.readADC_Differential_0_1();  // Write result if beginning of measurement is detected
        bufferIndex = 0;
        messageBuffer[bufferIndex++] = incomingByte;
        lookingForStart = false;
      } else if (incomingByte == 0xFA) {
        currentMessageType = TYPE_FA;
        bufferIndex = 0;
        messageBuffer[bufferIndex++] = incomingByte;
        lookingForStart = false;
      }
    } else {
      // Continue buffering based on message type
      messageBuffer[bufferIndex++] = incomingByte;

      // Determine if the message is complete
      if (currentMessageType == TYPE_80 && bufferIndex == 2) {
        // Validate second byte for TYPE_80
        if (messageBuffer[1] != 0x06) {
          resetState();  // Not a valid TYPE_80 message, reset
          return;
        }
      }

      if ((currentMessageType == TYPE_80 && bufferIndex == 11) || (currentMessageType == TYPE_FA && bufferIndex >= 4)) {
        // Validate checksum
        if (validateChecksum(messageBuffer, bufferIndex)) {
          processMessage(messageBuffer, bufferIndex);
        } else {
          Serial.println("Invalid checksum, discarding message.");
        }
        resetState();  // Reset to process next message
      }
    }
  }
}
bool validateChecksum(uint8_t* message, int length) {
  uint16_t sum = 0;
  // Compute sum of all bytes except the checksum itself
  for (int i = 0; i < length - 1; i++) {
    sum += message[i];
  }
  // Calculate 2's complement checksum
  uint8_t calculatedChecksum = (0x100 - (sum & 0xFF)) & 0xFF;

  // Compare calculated checksum with received checksum
  return calculatedChecksum == message[length - 1];
}

// Process valid messages
void processMessage(uint8_t* message, int length) {
  // Serial.println("Valid message received:");
  for (int i = 0; i < length; i++) {
    //Serial.print("0x");
    if (message[i] < 0x10) {
      Serial.print('0');  // Add leading zero for single-digit hex
    }
    inputString += char(message[i]);
  }
  Serial.print(inputString);
  Serial.print('\r');
  if (length == 11) {
    Serial.print(result);
  }
  Serial.print('\n');
  inputString = "";
}

// Reset state machine
void resetState() {
  bufferIndex = 0;
  lookingForStart = true;
  currentMessageType = UNKNOWN;
}

void forwardSerialToSerial1() {
  if (Serial.available()) {
    delay(10);
    String command = "";
    // Read the command from the computer
    while (Serial.available()) {
      char c = Serial.read();
      if (c == '\n') {
        break;
      }
      command += c;
    }

    // Send the command to the sensor
    for (int i = 0; i < command.length(); i += 2) {
      String byteString = command.substring(i, i + 2);
      byte byteValue = (byte)strtol(byteString.c_str(), NULL, 16);
      Serial1.write(byteValue);
    }
  }
}

// Update encoder value
void updateEncoder() {
  int MSB = digitalRead(encoderPinA);
  int LSB = digitalRead(encoderPinB);

  int encoded = (MSB << 1) | LSB;          // Combine the two bits to form a 2-bit number
  int sum = (lastEncoded << 2) | encoded;  // Combine with previous state to track direction

  // Update encoder position based on direction
  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) encoderPosition++;
  if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) encoderPosition--;

  lastEncoded = encoded;
}
