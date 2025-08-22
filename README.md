# Emotion analysis Interface TOPST-D3
This project is a smart emotion-analysis interface for mental health management.  
이 프로젝트는 정신 건강 관리를 위한 스마트 감정 인식 인터페이스입니다.  

TOPST D3 보드를 기반으로 OpenCV, V4L2, SCP/SSH 등의 다양한 통신 및 제어 기술을 활용하여 카메라, LCD, LED, 부저 등의 하드웨어를 통합적으로 제어합니다. 

이를 통해 사용자 얼굴을 실시간으로 인식 및 캡처하여 감정을 분석하고 , 분석 결과를 LCD와 음성으로 제공하며, 기록으로 남깁니다. 

사용자가 자신의 감정을 일상적으로 모니터링하고, 자가 진단 기회를 얻으며, 스트레스를 조기 발견하는 것을 목표로 합니다. 


D3 보드에서 얼굴을 5초 연속 인식하면 LED가 순차 점등되고, 부저가 울린 뒤 사진을 캡처하여 Host PC로 전송합니다. Host는 이미지를 감정 분석 API로 처리하고, 결과를 음성으로 재생하며, D3 LCD에 상위 감정 2줄 요약을 표시합니다.

* 구성 요약
  * D3 보드

    src/combine.cpp: 얼굴 인식 + GPIO(LED/부저) + 캡처 → scp → ssh

    src/lcd_display_easy.c: /home/root/emotion_result.txt 2줄을 I2C LCD에 표시

  * Host PC

    src/auto_emotion_send_save.py: 이미지 업로드 → 감정 분석 → 결과 저장/로그 → D3 전송 → LCD 실행 → 음성/조언

    src/read_speak.py: 감정 멘트 생성 + TTS 재생

    src/advice.py: 요약/로그 기반 조언 생성 + TTS 재생

  * 샘플/로그

    sample/result.txt: 결과 JSON 예시

    Host 작업 폴더: /home/a/Downloads/microprocessor/picture/2/ (이미지/결과/로그 파일)

* 환경 요구사항
  * D3 보드

     * OpenCV(영상/얼굴 인식)

     * I2C 활성화, /dev/i2c-1 접근 가능

  * Host PC

     * Python 3.8+

     * 시스템 패키지: mpg123(음성 재생)

     * requests

     * paramiko

     * scp

     * gTTS

     * playsound

     * transformers

     * torch (필요 시)

* 네트워크 설정
  * Host IP: 192.168.0.63 (예시)

  * D3 IP: 192.168.0.155 (예시)

    둘 다 같은 대역(예: 192.168.0.x)

    D3 → Host SSH 접속 가능(키 또는 비밀번호). 자동화를 위해 SSH 키 권장.

    공개키 등록 예: Host의 ~/.ssh/id_rsa.pub 내용을 Host의 ~/.ssh/authorized_keys에 추가

* 경로/파일
  * D3

    캡처 파일: /home/root/capture_0.jpg

    LCD 입력 파일: /home/root/emotion_result.txt

    LCD 바이너리: /home/root/lcd_display_easy

  * Host

    작업 폴더(BASE_DIR): /home/a/Downloads/microprocessor/picture/2/

    이미지 파일: capture_0.jpg

    결과 파일: result.txt (JSON)

    LCD용 요약 파일: emotion_result.txt (2줄)

    로그 파일: emotion_log.txt


* 실행 흐름
  * D3에서 실행
   ./combine

   동작:

   얼굴 5초 연속 인식 → LED 순차 점등 → 부저 0.5초 → /home/root/capture_0.jpg 저장

   scp로 Host:/home/a/Downloads/microprocessor/picture/2/ 에 전송

   ssh로 Host에서 auto_emotion_send_save.py 실행

  * Host에서 자동 실행
   auto_emotion_send_save.py가 수행:

   Imentiv API에 이미지 업로드 → 완료까지 폴링 → result.txt(JSON) 저장

   상위 4감정 요약 → emotion_result.txt(2줄) 작성

   emotion_log.txt에 누적 기록

   D3로 emotion_result.txt 전송 → lcd_display_easy 재시작하여 LCD 표시

   read_speak.py 호출(멘트 생성 + TTS)

   advice.py 실행(조언 생성 + TTS)

  * D3 LCD
   lcd_display_easy가 emotion_result.txt의 2줄을 화면에 표시

* 자주 발생하는 이슈
  * D3에서 카메라 인덱스 다름

  src/combine.cpp의 CAMERA_INDEX를 0/1/2 중 실제 연결에 맞게 변경

  * Host IP 변경

  src/combine.cpp의 host_ip 수정(현재 예시: 192.168.0.63)

  * SSH 접속 실패

  D3에서 ssh a@HOST_IP로 접속 테스트

  StrictHostKeyChecking=no 옵션 유지 또는 known_hosts 등록

  * HTTPS API 실패

  네트워크/프록시/방화벽 확인

  curl -v https://api.imentiv.ai/v1/images로 진단

  * 음성 미재생

  Host에서 mpg123 설치 확인

  read_speak.py/playsound가 무음이면 advice.py의 mpg123 경로 사용 참고

  * LCD 무표시

  I2C_ADDR(0x27/0x3F) 확인

  /dev/i2c-1 접근권한과 배선 확인

  emotion_result.txt가 정확히 2줄인지 확인(각 줄 16자 이내 권장)

* 파일 설명
  * src/combine.cpp

  얼굴 5초 연속 인식 시 LED 점등/부저, 캡처 저장, Host로 전송, Host 스크립트 호출

  * src/lcd_display_easy.c

  emotion_result.txt를 읽어 2줄 표시

  * src/auto_emotion_send_save.py

  이미지 업로드 → 분석 → result.txt 저장 → 요약/로그 → D3 전송/LCD 실행 → 멘트/조언

  * src/read_speak.py

  result.txt를 파싱(포맷에 따라 다름)해 멘트 생성 + TTS 재생

  * src/advice.py

  result.txt/로그 기반 요약과 모델을 사용해 조언 생성 + TTS 재생

  * sample/result.txt

  JSON 포맷 예시

* 빠른 시작(요약)
  
  * Host

  (옵션) export IMENTIV_API_KEY="발급키"

  * D3

  g++ -o combine src/combine.cpp $(pkg-config --cflags --libs opencv4)

  gcc -o lcd_display_easy src/lcd_display_easy.c -li2c

  ./combine
