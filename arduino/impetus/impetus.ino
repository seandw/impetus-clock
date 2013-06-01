#include <i2cmaster.h>
#include <SoftwareSerial.h>

SoftwareSerial display(8, 9);

int ledPin = 13;
int mphonePin = 0;
int buzzPin = 12;
int cycle = 0, vol = 0;
double temp = 0;
boolean flash = false;

void setup(){
  Serial.begin(9600);
  
  display.begin(9600);
  display.write(0x76);
  display.write('t');
  display.write('e');
  display.write('s');
  display.write('t');
  display.write(0x77);
  display.write(0b00010000);
  
  i2c_init(); //Initialise the i2c bus
  PORTC = (1 << PORTC4) | (1 << PORTC5);//enable pullups

  //pinMode(ledPin, OUTPUT);
  pinMode(mphonePin, INPUT);
  pinMode(buzzPin, OUTPUT);
}

float readTemp(){
  int dev = 0x5A<<1;
  int data_low = 0;
  int data_high = 0;
  int pec = 0;
  
  i2c_start_wait(dev+I2C_WRITE);
  i2c_write(0x07);
  
  // read
  i2c_rep_start(dev+I2C_READ);
  data_low = i2c_readAck(); //Read 1 byte and then send ack
  data_high = i2c_readAck(); //Read 1 byte and then send ack
  pec = i2c_readNak();
  i2c_stop();
  
  //This converts high and low bytes together and processes temperature, MSB is a error bit and is ignored for temps
  double tempFactor = 0.02; // 0.02 degrees per LSB (measurement resolution of the MLX90614)
  double tempData = 0x0000; // zero out the data
  int frac; // data past the decimal point
  
  // This masks off the error bit of the high byte, then moves it left 8 bits and adds the low byte.
  tempData = (double)(((data_high & 0x007F) << 8) + data_low);
  tempData = (tempData * tempFactor)-0.01;
  
  float celcius = tempData - 273.15;
  float fahrenheit = (celcius*1.8) + 32;
  
  //if (Serial) {
    // Print fahrenheit value.
    // Serial.println(fahrenheit);
  //}
  
  //if (fahrenheit > 79.f)
  //  digitalWrite(ledPin, HIGH);
  //else
  //  digitalWrite(ledPin, LOW);

  return fahrenheit;
}

int readVol() {
  int readings[50], minR = 1023, maxR = 0;
  for (int i = 0; i < 50; i++) {
    readings[i] = analogRead(mphonePin);
    delay(1);
  }
  for (int i = 0; i < 50; i++) {
    if (readings[i] > maxR)
      maxR = readings[i];
    else if (readings[i] < minR)
      minR = readings[i];
  }
  return maxR-minR;
}

void alarm() {
  digitalWrite(buzzPin, HIGH);
  delay(1000);
  digitalWrite(buzzPin, LOW);
}

void loop() {
  double tt = readTemp();
  int tv = readVol();
  if (tt > temp)
    temp = tt;
  if (tv > vol)
    vol = tv;
  cycle++;
  if (cycle == 60) {
    cycle = 0;
    if (Serial) {
      Serial.print(temp);
      Serial.print(" ");
      Serial.println(vol);
    }
    temp = 0;
    vol = 0;
  }
  if (Serial.available() > 4) {
    int hour = Serial.parseInt();
    display.write(hour/10);
    display.write(hour%10);
    int minute = Serial.parseInt();
    display.write(minute/10);
    display.write(minute%10);
  }
  if (!flash) {
    flash = true;
    display.write(0x77);
    display.write(0b00010000);
  } else {
    flash = false;
    display.write(0x77);
    display.write((byte) 0);
  }
  // alarm();
  delay(1000); // wait a second before printing again
}
