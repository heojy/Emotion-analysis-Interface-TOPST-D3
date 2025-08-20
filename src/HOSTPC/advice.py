#!/usr/bin/env python3
import os
import sys
import json
import re
from datetime import datetime
from transformers import pipeline
from gtts import gTTS
import subprocess

# ──────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
RESULT_PATH   = os.path.join(BASE_DIR, "result.txt")        # 단일 감정 분석 JSON
LOG_PATH      = os.path.join(BASE_DIR, "emotion_log.txt")   # 날짜별 로그
MODEL_NAME    = "google/flan-t5-small"

# ──────────────────────────────────────────────────────────
# TTS 재생 (gTTS + mpg123)
# ──────────────────────────────────────────────────────────
def speak(text: str):
    tmp_mp3 = os.path.join(BASE_DIR, "advice.mp3")
    tts = gTTS(text=text, lang="ko")
    tts.save(tmp_mp3)
    subprocess.run(["mpg123", "-q", tmp_mp3])
    os.remove(tmp_mp3)

# ──────────────────────────────────────────────────────────
# 감정 데이터 로드
# ──────────────────────────────────────────────────────────
def load_emotions(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def summarize_top4(emotions: dict) -> str:
    top4 = sorted(emotions.items(), key=lambda kv: kv[1], reverse=True)[:4]
    return " / ".join(f"{k[:3]}:{v:.2f}" for k, v in top4)

# ──────────────────────────────────────────────────────────
# sad가 상위 4개에 포함된 일자 집계
# ──────────────────────────────────────────────────────────
def count_sad_days(log_path):
    if not os.path.exists(log_path):
        return 0
    sad_dates = set()
    current_date = None
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 날짜 라인 (YYYY-MM-DD HH:MM:SS)
            m = re.match(r'^(\d{4}-\d{2}-\d{2}) ', line)
            if m:
                current_date = m.group(1)
            elif current_date and "sad:" in line.lower():
                sad_dates.add(current_date)
                current_date = None
    return len(sad_dates)

# ──────────────────────────────────────────────────────────
# 로컬 모델 초기화
# ──────────────────────────────────────────────────────────
_generator = None
def get_generator():
    global _generator
    if _generator is None:
        _generator = pipeline(
            "text2text-generation",
            model=MODEL_NAME,
            device="cpu",
            max_new_tokens=100,
            do_sample=False
        )
    return _generator

def generate_model_advice(summary: str) -> str:
    prompt = (
        f"감정 분석 결과 상위 4개 감정입니다: {summary}.\n"
        "이 결과를 바탕으로 간단한 마음 관리 및 기분 전환 방법을 한국어로 제안해 주세요."
    )
    gen = get_generator()
    out = gen(prompt)
    text = out[0]["generated_text"]
    return text.replace("<s>", "").replace("</s>", "").strip() or \
           "간단한 기분 전환 방법을 시도해 보세요."

# ──────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────
def main():
    # 1) result.txt 로드 및 요약
    emotions = load_emotions(RESULT_PATH)
    summary  = summarize_top4(emotions)
    print("🔍 상위 4개 감정 요약:", summary)

    # 2) sad 포함 일수 확인
    days_sad = count_sad_days(LOG_PATH)
    print(f"📅 sad가 상위 4개에 든 일수: {days_sad}일")

    # 3) 조건에 따른 고정 조언
    if days_sad >= 7:
        advice = "요즘 우울한 감정이 계속 드네요 병원을 가보시는건 어떤가요"
    elif days_sad >= 3:
        advice = "가벼운 산책을 통해 활기를 가져보세요"
    elif days_sad >= 2:
        advice = "요즘 우울한 감정이 드는거 같아요 기분을 환기 시켜 보세요"
    else:
        # 4) 조건 미충족 시 모델 기반 조언
        print("💡 모델 기반 조언 생성 중…")
        advice = generate_model_advice(summary)

    # 5) 결과 출력 및 음성 안내
    print("\n=== 조언 ===")
    print(advice)
    print("\n🔊 음성 재생 중…")
    speak(advice)

if __name__ == "__main__":
    main()

