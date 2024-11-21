// Define pins for the encoder
const int encoderPinA = 7; // Must be an interrupt pin on Arduino UNO
const int encoderPinB = 8; // Optional for direction detection

volatile long encoderPosition = 0; // Holds the current position
volatile int lastEncoded = 0; // Stores the last encoder state

void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Set up encoder pins as inputs
  pinMode(encoderPinA, INPUT);
  pinMode(encoderPinB, INPUT);
  
  // Enable pullup resistors if needed
  digitalWrite(encoderPinA, HIGH);
  digitalWrite(encoderPinB, HIGH);

  // Attach interrupts for encoder
  attachInterrupt(digitalPinToInterrupt(encoderPinA), updateEncoder, CHANGE);
  attachInterrupt(digitalPinToInterrupt(encoderPinB), updateEncoder, CHANGE);
}

void loop() {
  // Print the encoder position
  //Serial.print("Position: ");
  Serial.println(encoderPosition);
  delay(10); // Adjust as needed for your application
}

// Interrupt function to update the encoder position
void updateEncoder() {
  // Read the current state of the encoder
  int MSB = digitalRead(encoderPinA); // Most significant bit
  int LSB = digitalRead(encoderPinB); // Least significant bit

  int encoded = (MSB << 1) | LSB; // Combine the two bits to form a 2-bit number
  int sum = (lastEncoded << 2) | encoded; // Combine with previous state to track direction
  
  // Update encoder position based on direction
  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) encoderPosition++;
  if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) encoderPosition--;
  
  lastEncoded = encoded; // Store current state for next iteration
}
