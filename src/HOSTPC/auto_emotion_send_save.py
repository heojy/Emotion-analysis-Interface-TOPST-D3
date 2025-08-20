#!/usr/bin/env python3

import os
import sys
import time
import json
import requests
import paramiko
from scp import SCPClient
from datetime import datetime
import subprocess

# ───────────────────────────────────────────────────────────
#   경로 및 파일 설정 (절대경로로 통일)
# ───────────────────────────────────────────────────────────

BASE_DIR = "/home/a/Downloads/microprocessor/picture/2"
IMAGE_FILE = os.path.join(BASE_DIR, "capture_0.jpg")
OUTPUT_FILE = os.path.join(BASE_DIR, "result.txt")                # 감정 점수 JSON 저장
EMOTION_RESULT_FILE = os.path.join(BASE_DIR, "emotion_result.txt") # 감정 요약 텍스트 저장
LOCAL_LOG_FILE = os.path.join(BASE_DIR, "emotion_log.txt")         # 로그 파일

API_KEY = "-krKVu9UOCKFy92pfdHyI6gEs6B9ka0n4I9fP3csYh8-Zy3tRzjcsPLCn_7n_z6cf7Q"
BASE_URL = "https://api.imentiv.ai/v1/images"

MAX_RETRIES = 15
SLEEP_SEC = 2

# ───────────────────────────────────────────────────────────
#   감정 분석 API
# ───────────────────────────────────────────────────────────

def upload_image():
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    with open(IMAGE_FILE, "rb") as image_data:
        files = {
            "image": (os.path.basename(IMAGE_FILE), image_data, "image/jpeg"),
        }
        resp = requests.post(BASE_URL, headers=headers, files=files)
        resp.raise_for_status()
        return resp.json()["id"]

def poll_result(image_id: str):
    headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
    url = f"{BASE_URL}/{image_id}"
    for _ in range(MAX_RETRIES):
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "").lower()
        if status == "completed":
            return data
        if status in ("failed", "error"):
            raise RuntimeError(f"분석 실패: {data}")
        time.sleep(SLEEP_SEC)
    raise TimeoutError("분석 대기 시간 초과")

# ───────────────────────────────────────────────────────────
#   보드로 결과 전송 및 C 바이너리 실행
# ───────────────────────────────────────────────────────────

D3_IP = "192.168.0.155"
D3_USER = "root"
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")
REMOTE_RESULT_PATH = "/home/root/emotion_result.txt"
REMOTE_C_BINARY = "/home/root/lcd_display_easy"

def emotion_summary(result_file):
    """
    result.txt에서 상위 4개 감정을 3자리코드+정수%로 LCD용 요약 문자열로 반환
    """
    with open(result_file, 'r', encoding='utf-8') as f:
        line = f.read().strip()
    scores = {}
    for part in line.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            k, v = part.split()
            k = k.replace('"','').replace("'",'')  # 따옴표 제거
            scores[k] = float(v)
        except ValueError:
            continue
    # 상위 4개 추출
    sorted_emotions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top4 = sorted_emotions[:4]
    # 3자리 감정명 + 정수% 변환
    def clean3(name):
        # 혹시라도 감정명이 3글자 미만이면 빈칸 채우기
        n = name.replace('"','').replace("'",'')
        return n[:3].ljust(3)
    line1 = f"{clean3(top4[0][0])} {int(round(top4[0][1]*100))}%, {clean3(top4[1][0])} {int(round(top4[1][1]*100))}%"
    line2 = f"{clean3(top4[2][0])} {int(round(top4[2][1]*100))}%, {clean3(top4[3][0])} {int(round(top4[3][1]*100))}%"
    return f"{line1}\n{line2}\n"



def log_full_emotions(result_file, log_file):
    # 분석용: 8개 전체 감정, 소수점 3자리, 누적 저장
    with open(result_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return
    emotions = ['neutral','happy','sad','angry','surprise','fear','disgust','contempt']
    code_map = {
        'neutral':'neu', 'happy':'hap', 'sad':'sad', 'angry':'ang',
        'surprise':'sur', 'fear':'fea', 'disgust':'dis', 'contempt':'con'
    }
    line = []
    for emo in emotions:
        short = code_map[emo]
        val = data.get(emo, 0.0)
        line.append(f"{short}:{val:.3f}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{now} {' '.join(line)}\n"
    try:
        with open(log_file, "a", encoding="utf-8") as log_f:
            log_f.write(log_line)
        print("전체 감정 로그 기록:", log_line.strip())
    except Exception as e:
        print(f"전체 감정 로그 기록 오류: {e}")

def log_with_timestamp(summary):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{now} {summary.replace(chr(10), ' ').strip()}\n"
    try:
        with open(LOCAL_LOG_FILE, "a", encoding="utf-8") as log_f:
            log_f.write(log_line)
        print("로그 기록:", log_line.strip())
    except Exception as e:
        print(f"로그 기록 오류: {e}")

def send_to_d3(result_file):
    try:
        # LCD용 요약
        summary = emotion_summary(result_file)
        with open(EMOTION_RESULT_FILE, "w", encoding="utf-8") as f:
            f.write(summary)  # summary는 위에서 반환된 순수 텍스트
        
        log_with_timestamp(summary)  # 기존 로그(상위 4개)
        # 전체 감정 로그(모든 감정)
        log_full_emotions(result_file, LOCAL_LOG_FILE)
        # 보드 전송
        with open(EMOTION_RESULT_FILE, "w") as f:
            f.write(summary)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=D3_IP,
            username=D3_USER,
            key_filename=SSH_KEY_PATH,
            timeout=10
        )
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(EMOTION_RESULT_FILE, REMOTE_RESULT_PATH)
        ssh.exec_command("pkill -f lcd_display_easy")
        run_cmd = f"nohup {REMOTE_C_BINARY} > /dev/null 2>&1 &"
        ssh.exec_command(run_cmd)
        print("✅ 보드로 감정 결과 전송 및 C 바이너리 실행 요청 성공")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        try: ssh.close()
        except: pass
    
    # --- 여기서 음성 출력(read_speak.py) 호출 ---
    base_dir = os.path.dirname(result_file)
    read_speak_path = os.path.join(base_dir, "read_speak.py")
    try:
        subprocess.Popen(["python3", read_speak_path, result_file])
        print("read_speak.py 호출 성공 (host에서 음성 출력)")
    except Exception as e:
        print(f"read_speak.py 호출 실패: {e}")

def main():
    try:
        # 1) 이미지 업로드
        image_id = upload_image()
        full_result = poll_result(image_id)

        faces = full_result.get("faces", [])
        if not faces:
            raise KeyError("faces 데이터 없음")
        emotions = faces[0].get("emotions")
        if emotions is None:
            raise KeyError("emotions 필드 없음")

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(emotions, f, ensure_ascii=False, indent=2)
        print(f"✅ 감정 점수 '{OUTPUT_FILE}'에 저장 완료")

        # 2) 노트북에서 날짜·시간과 함께 로그 기록 후 보드로 전송
        send_to_d3(OUTPUT_FILE)

        # 3) advice.py 실행 (절대경로와 cwd 명확히 지정)
        advice_py_path = os.path.join(BASE_DIR, "advice.py")
        try:
            subprocess.run(["python3", advice_py_path], check=True, cwd=BASE_DIR)
        except Exception as e:
            print(f"advice.py 실행 오류: {e}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

