#include <Arduino.h>
#include <WiFi.h>
#include <NTPClient.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_camera.h"
#include "secrets.h"

const long utcOffsetInSeconds = 0;

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", utcOffsetInSeconds);


WiFiClient client;

// CAMERA_MODEL_AI_THINKER
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

const int timerInterval = 900000;    // time between each HTTP POST image
//const int timerInterval = 900000;
unsigned long previousMillis = 0;   // last time image was sent

int attempts = 0;
int wifiAttempts = 0;

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);

  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  //WiFi.setSleep(false);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    wifiAttempts++;
    if(wifiAttempts > 40){
      Serial.println("THE WIFI DID NOT LET ME CONNECT");
      delay(10000);
      ESP.restart();
    }
    delay(1000);
  }
  Serial.println();
  Serial.print("ESP32-CAM IP Address: ");
  Serial.println(WiFi.localIP());

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // init with high specs to pre-allocate larger buffers
  if(psramFound()){
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 10;  //0-63 lower number means higher quality
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_CIF;
    config.jpeg_quality = 12;  //0-63 lower number means higher quality
    config.fb_count = 1;
  }
 
  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    delay(10000);
    ESP.restart();
  }

  sensor_t * s = esp_camera_sensor_get();
  //s->set_wb_mode(s, 3);
  //s->set_exposure_ctrl(s, 0);
  //s->set_brightness(s, 2);

 
  // time init
  timeClient.begin();
 
  sendPhoto();
}

void loop() {
  unsigned long currentMillis = millis();
  timeClient.update();
 
  if((timeClient.getHours() == 22 && timeClient.getMinutes() == 5) && (currentMillis - previousMillis >= (1000 * 60 * 2))){
    if (WiFi.status() != WL_CONNECTED){
      wifiAttempts = 0;
     
      WiFi.disconnect();
      WiFi.reconnect();
      Serial.println("RECONNECTNG");
     
       while (WiFi.status() != WL_CONNECTED) {
          Serial.print(".");
          wifiAttempts++;
          if(wifiAttempts > 40){
            Serial.println("THE WIFI DID NOT LET ME CONNECT");
            delay(10000);
            ESP.restart();
          }
          delay(1000);
      }
    }
   
    sendPhoto();
    previousMillis = currentMillis;
  }
}


void sendPhoto() {
  String getAll;
  String getBody;


  digitalWrite(2, LOW);
  delay(5000);
 
 
  timeClient.update();

  Serial.println(timeClient.getFormattedTime());
  Serial.println(timeClient.getEpochTime());

  camera_fb_t * fb = NULL;
  Serial.println("Camera capture START");
  fb = esp_camera_fb_get();
  Serial.println("Camera capture STOP");
 
  if(!fb) {
    Serial.println("Camera capture failed");
    delay(1000);
    ESP.restart();
  }

 

  delay(1000);

  digitalWrite(2, HIGH);
 
  Serial.println("Connecting to server: " + serverName);

  if (client.connect(serverName.c_str(), serverPort)) {
    uint8_t * fbBuf = fb->buf;

    attempts = 0;
   
    Serial.println("Connection successful!");    
    String head = "--\r\nContent-Disposition: form-data; name=\"meter\"; filename=\"image_" + String(timeClient.getEpochTime()) + ".jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
    String tail = "\r\n----\r\n";

    uint32_t imageLen = fb->len;
    uint32_t extraLen = head.length() + tail.length();
    uint32_t totalLen = imageLen + extraLen;
 
    client.println("POST " + serverPath + " HTTP/1.1");
    client.println("Host: " + serverName);
    client.println("Content-Length: " + String(totalLen));
    client.println("Content-Type: multipart/form-data; boundary=--");
    client.println("Authorization: Basic " + superSecretKey);
    client.println();
    client.print(head);
 
   
    size_t fbLen = fb->len;
    for (size_t n=0; n<fbLen; n=n+1024) {
      if (n+1024 < fbLen) {
        client.write(fbBuf, 1024);
        fbBuf += 1024;
      }
      else if (fbLen%1024>0) {
        size_t remainder = fbLen%1024;
        client.write(fbBuf, remainder);
      }
    }  
    client.print(tail);
   
   
   
    int timoutTimer = 10000;
    long startTimer = millis();
    bool state = false;
   
    while ((startTimer + timoutTimer) > millis()) {
      Serial.print(".");
      delay(100);      
      while (client.available()) {
        char c = client.read();
        getAll += String(c);
        if (c == '\n') {
          if (getAll.length()==0) { state=true; }
          //getAll = "";
        }
        //else if (c != '\r') {  }
        if (state==true) { getBody += String(c); }
        startTimer = millis();
      }
      if (getBody.length()>0) { break; }
    }
    Serial.println();
    Serial.print(getAll);
    client.stop();
    Serial.println(getBody);
  }
  else {
    getBody = "Connection to " + serverName +  " failed.";
    Serial.println(getBody);
//    attempts++;
//    if (attempts > 2){
      delay(5000);
      Serial.println("RESTARTING");
//      attempts = 0;
      ESP.restart();
//    } 
  }
  esp_camera_fb_return(fb);
  return;
}