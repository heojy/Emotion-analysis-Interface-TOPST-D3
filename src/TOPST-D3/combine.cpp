// combine1.cpp (cleaned and runnable)
// D3 보드에서: 얼굴 5초 연속 인식 -> LED 순차 점등 -> 부저 0.5초 울림
// -> 이미지 캡처 저장(/home/root/capture_0.jpg)
// -> scp로 Host 전송 -> ssh로 Host에서 auto_emotion_send_save.py 실행

#include <opencv2/opencv.hpp>
#include <opencv2/objdetect.hpp>
#include <iostream>
#include <vector>
#include <chrono>
#include <sstream>
#include <string>

// POSIX / sysfs GPIO
#include <unistd.h>     // usleep, access
#include <fcntl.h>      // open
#include <string.h>     // strlen, strerror
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <errno.h>

using namespace cv;
using namespace std;

// ============== GPIO Helpers (sysfs) ==============
static void ExportGPIO(const char* pin_num) {
    int fd = open("/sys/class/gpio/export", O_WRONLY);
    if (fd == -1) {
        // cerr << "ExportGPIO open error: " << strerror(errno) << endl;
        return;
    }
    write(fd, pin_num, strlen(pin_num));
    close(fd);
}

static void UnexportGPIO(const char* pin_num) {
    int fd = open("/sys/class/gpio/unexport", O_WRONLY);
    if (fd == -1) {
        // cerr << "UnexportGPIO open error: " << strerror(errno) << endl;
        return;
    }
    write(fd, pin_num, strlen(pin_num));
    close(fd);
}

static void SetGPIODirection(const char* pin_num, const char* direction) {
    char path[128];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%s/direction", pin_num);
    int fd = open(path, O_WRONLY);
    if (fd == -1) {
        // cerr << "SetGPIODirection open error: " << path << " " << strerror(errno) << endl;
        return;
    }
    write(fd, direction, strlen(direction));
    close(fd);
}

static void WriteGPIOValue(const char* pin_num, int value) {
    char path;
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%s/value", pin_num);
    int fd = open(path, O_WRONLY);
    if (fd == -1) {
        // cerr << "WriteGPIOValue open error: " << path << " " << strerror(errno) << endl;
        return;
    }
    if (value == 1) write(fd, "1", 1);
    else            write(fd, "0", 1);
    close(fd);
}

// ============== Main ==============
int main() {
    // 0) 환경 설정 (필요시 값만 바꿔서 사용)
    const int CAMERA_INDEX = 1; // 실제 연결된 카메라 인덱스(0/1/2...)
    const int required_seconds = 5; // 연속 검출 시간(초)

    // GPIO 핀 번호 (실제 보드 배선에 맞춰 사용)
    const char* led_pins[5] = {"84", "85", "86", "112", "113"};
    const char* buzzer_pin  = "89";

    // Host PC 정보 (시연/현행 값에 맞게)
    const string host_user = "a";
    const string host_ip   = "192.168.0.63"; // 필요시 변경
    const string host_dst  = "/home/a/Downloads/microprocessor/picture/2/";
    const string py_path   = "/home/a/Downloads/microprocessor/picture/2/auto_emotion_send_save.py";

    // 캡처 저장 경로(D3 로컬)
    const string filename = "/home/root/capture_0.jpg";

    // 1) GPIO 초기화
    for (int i = 0; i < 5; i++) {
        ExportGPIO(led_pins[i]);
        SetGPIODirection(led_pins[i], "out");
        WriteGPIOValue(led_pins[i], 0); // 초기 OFF
    }
    ExportGPIO(buzzer_pin);
    SetGPIODirection(buzzer_pin, "out");
    WriteGPIOValue(buzzer_pin, 0); // 초기 OFF

    // 2) 카메라 열기
    VideoCapture capture(CAMERA_INDEX, cv::CAP_V4L2);
    if (!capture.isOpened()) {
        cerr << "Error opening video capture" << endl;
        // GPIO 해제 후 종료
        for (int i = 0; i < 5; i++) UnexportGPIO(led_pins[i]);
        UnexportGPIO(buzzer_pin);
        return -1;
    }

    capture.set(CAP_PROP_FRAME_WIDTH,  640);
    capture.set(CAP_PROP_FRAME_HEIGHT, 480);

    // 3) 얼굴 검출기 로드
    CascadeClassifier face_cascade;
    const String face_cascade_name = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml";
    if (!face_cascade.load(face_cascade_name)) {
        cerr << "Error loading face cascade" << endl;
        capture.release();
        for (int i = 0; i < 5; i++) UnexportGPIO(led_pins[i]);
        UnexportGPIO(buzzer_pin);
        return -1;
    }

    Mat frame, gray;
    bool face_detecting = false;
    chrono::steady_clock::time_point face_start;

    bool done = false; // 한 번만 동작 후 종료

    while (!done) {
        if (!capture.read(frame) || frame.empty()) {
            cerr << "No captured frame -- Break!" << endl;
            break;
        }

        Mat clean_frame = frame.clone();
        cvtColor(frame, gray, COLOR_BGR2GRAY);

        vector<Rect> faces;
        face_cascade.detectMultiScale(gray, faces, 1.1, 5, 0, Size(30, 30));

        if (!faces.empty()) {
            if (!face_detecting) {
                face_detecting = true;
                face_start = chrono::steady_clock::now();
                // 얼굴 처음 인식되면 LED 모두 OFF
                for (int i = 0; i < 5; i++) WriteGPIOValue(led_pins[i], 0);
            } else {
                int elapsed = (int)chrono::duration_cast<chrono::seconds>(chrono::steady_clock::now() - face_start).count();

                // LED 점등: 1초마다 1개씩 추가 점등
                for (int i = 0; i < 5; i++) {
                    WriteGPIOValue(led_pins[i], (i < elapsed) ? 1 : 0);
                }

                // 5초 이상 지속되면 캡처/부저/전송/원격실행
                if (elapsed >= required_seconds) {
                    // 부저 ON 0.5s
                    WriteGPIOValue(buzzer_pin, 1);
                    usleep(500000);
                    WriteGPIOValue(buzzer_pin, 0);

                    // LED 모두 OFF
                    for (int i = 0; i < 5; i++) WriteGPIOValue(led_pins[i], 0);

                    // 캡처 저장 (D3 로컬)
                    if (imwrite(filename, clean_frame)) {
                        cout << "Saved image: " << filename << endl;

                        // Host로 파일 전송 (scp)
                        ostringstream scp_cmd;
                        scp_cmd << "scp -o StrictHostKeyChecking=no " << filename << " "
                                << host_user << "@" << host_ip << ":" << host_dst;
                        int ret_scp = system(scp_cmd.str().c_str());
                        if (ret_scp == 0) {
                            cout << "Image sent to local PC successfully." << endl;

                            // Host에서 파이썬 실행 (ssh)
                            ostringstream ssh_cmd;
                            ssh_cmd << "ssh -o StrictHostKeyChecking=no -o BatchMode=yes "
                                    << host_user << "@" << host_ip << " "
                                    << "\"python3 " << py_path << "\"";
                            int ret_ssh = system(ssh_cmd.str().c_str());
                            if (ret_ssh == 0) {
                                cout << "auto_emotion_send_save.py 실행 요청 성공." << endl;
                            } else {
                                cerr << "auto_emotion_send_save.py 실행 요청 실패 (코드=" << ret_ssh << ")." << endl;
                            }
                        } else {
                            cerr << "Failed to send image to local PC." << endl;
                        }
                    } else {
                        cerr << "Failed to save image: " << filename << endl;
                    }

                    done = true; // 한 번 동작 후 종료
                }
            }
        } else {
            // 얼굴 인식 안되면 상태 리셋 및 LED OFF
            if (face_detecting) {
                face_detecting = false;
                for (int i = 0; i < 5; i++) WriteGPIOValue(led_pins[i], 0);
            }
        }

        // 헤드리스: GUI 없음. 필요 시 sleep 등 추가 조정 가능.
        // usleep(10000);
    }

    // 자원 정리
    capture.release();
    for (int i = 0; i < 5; i++) {
        WriteGPIOValue(led_pins[i], 0);
        UnexportGPIO(led_pins[i]);
    }
    WriteGPIOValue(buzzer_pin, 0);
    UnexportGPIO(buzzer_pin);

    return 0;
}
