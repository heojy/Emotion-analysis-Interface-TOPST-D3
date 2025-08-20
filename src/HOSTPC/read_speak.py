#!/usr/bin/env python3
# emotion_tts_comment.py

import sys
import tempfile
import os
import re
from gtts import gTTS
try:
    from playsound import playsound
except ImportError:
    playsound = None

import random

TEMPLATES = {
    'sad': [
        "오늘은 마음이 조금 무거우셨던 것 같아요.",
        "최근에 힘든 일이 있으셨나요? 마음을 돌보는 시간을 가져보세요.",
        "우울한 감정이 느껴집니다. 혼자가 아니라는 걸 기억하세요.",
        "감정의 파도가 잔잔하지 않았던 하루였네요.",
        "마음이 지친 날에는 잠시 쉬어가는 것도 필요해요.",
        "오늘은 평소보다 기운이 덜 나셨던 것 같아요.",
        "속상한 일이 있었다면, 누군가에게 털어놓아도 좋아요.",
        "스스로를 다독여주는 하루가 되길 바라요.",
        "작은 슬픔도 소중히 다뤄주세요.",
        "내일은 조금 더 가벼운 마음이 되길 응원합니다."
    ],
    'angry': [
        "오늘은 스트레스를 받는 일이 있었던 것 같아요.",
        "마음에 불편함이 남아있진 않으신가요?",
        "화가 나는 감정이 느껴집니다. 잠시 깊게 숨을 쉬어보세요.",
        "감정이 격해졌던 순간이 있었던 것 같아요.",
        "불쾌한 일이 있었다면, 자신을 보호하는 것도 중요해요.",
        "오늘은 평소보다 예민했던 하루였을 수 있어요.",
        "답답함이 느껴질 땐, 잠깐 자리를 벗어나보는 것도 좋아요.",
        "감정을 억누르지 말고, 건강하게 표현해보세요.",
        "스트레스가 쌓였을 땐, 나만의 해소법을 찾아보세요.",
        "내일은 더 평온한 하루가 되길 바랍니다."
    ],
    'surprise': [
        "예상치 못한 일이 있었던 하루였네요.",
        "오늘은 새로운 경험이나 소식이 있었던 것 같아요.",
        "변화가 많은 하루, 적응하느라 고생하셨죠?",
        "깜짝 놀랄 만한 일이 있었나요?",
        "일상이 평소와 달랐던 날이었을 수 있어요.",
        "새로운 자극이 감정에 영향을 준 것 같아요.",
        "오늘은 신선한 자극이 있었던 하루였네요.",
        "예상 밖의 상황이 당황스럽게 느껴졌을 수 있어요.",
        "갑작스러운 변화에도 잘 적응하셨네요.",
        "내일은 조금 더 안정적인 하루가 되길 바라요."
    ],
    'happy': [
        "오늘은 기분 좋은 일이 있었던 것 같아요!",
        "미소가 떠오르는 하루를 보내셨네요.",
        "긍정적인 에너지가 느껴집니다.",
        "즐거운 순간이 많았던 하루였겠어요.",
        "오늘의 행복이 오래 남길 바랍니다.",
        "좋은 일이 있으셨다면, 그 기쁨을 오래 간직하세요.",
        "소소한 행복이 쌓인 하루였던 것 같아요.",
        "기분 좋은 에너지가 전해집니다.",
        "감사한 마음으로 하루를 마무리하셨길 바래요.",
        "내일도 행복한 하루가 되길 응원합니다."
    ],
    'fear': [
        "오늘은 불안하거나 걱정되는 일이 있었던 것 같아요.",
        "마음 한켠에 두려움이 있었던 하루였네요.",
        "걱정이 많았던 하루, 스스로를 다독여주세요.",
        "불안한 감정이 느껴졌다면, 잠시 멈추고 호흡해보세요.",
        "마음이 조마조마했던 순간이 있었던 것 같아요.",
        "걱정이 많았던 하루, 충분히 이해해요.",
        "불확실함이 부담스러웠던 하루였을 수 있어요.",
        "마음이 편안해질 수 있도록 작은 휴식을 가져보세요.",
        "두려움이 들 때는, 주변의 도움을 받아도 좋아요.",
        "내일은 더 안정적인 하루가 되길 바랍니다."
    ],
    'contempt': [
        "오늘은 마음에 들지 않는 상황이 있었던 것 같아요.",
        "불쾌한 감정이 느껴졌다면, 스스로를 보호해보세요.",
        "상대방에 대한 실망감이 있었던 하루였나요?",
        "마음이 상하는 일이 있었다면, 자신을 위로해주세요.",
        "불편한 감정이 오래 남지 않길 바랍니다.",
        "실망스러운 일이 있었더라도, 자신을 탓하지 마세요.",
        "마음이 상할 땐, 잠시 거리를 두는 것도 좋아요.",
        "감정을 솔직하게 받아들이는 것도 중요해요.",
        "오늘의 불쾌함이 내일은 사라지길 바랍니다.",
        "자신을 소중히 여기는 하루가 되길 바랍니다."
    ],
    'disgust': [
        "오늘은 불쾌하거나 거북한 일이 있었던 것 같아요.",
        "마음에 들지 않는 상황이 있었던 하루였네요.",
        "불쾌한 감정이 남아있다면, 스스로를 돌봐주세요.",
        "거북한 일이 있었다면, 마음을 정리할 시간을 가져보세요.",
        "불편한 감정이 오래 남지 않길 바랍니다.",
        "오늘의 불쾌함이 내일은 사라지길 바랍니다.",
        "감정을 억지로 누르지 않아도 괜찮아요.",
        "자신을 소중히 여기는 하루가 되길 바랍니다.",
        "불쾌한 감정이 있을 땐, 잠시 쉬어가는 것도 좋아요.",
        "내일은 더 편안한 하루가 되길 바랍니다."
    ],
    'neutral': [
        "오늘은 감정의 큰 변화 없이 차분한 하루를 보내셨네요.",
        "평온한 하루를 보내신 것 같아요.",
        "특별한 감정 기복 없이 안정적인 하루였던 것 같습니다.",
        "오늘은 마음이 잔잔하게 유지된 하루였네요.",
        "무탈하게 하루를 마무리하신 것 같아요.",
        "감정의 변화가 크지 않은 하루였던 것 같아요.",
        "오늘은 평소와 비슷한 하루를 보내셨네요.",
        "특별히 힘들거나 기쁜 일 없이 하루를 보내셨던 것 같습니다.",
        "조용히 하루를 마무리하셨길 바랍니다.",
        "내일도 오늘처럼 평온한 하루가 되길 바랍니다."
    ]
}

WEIGHTS = {
    'neutral': 1.0,
    'happy': 1.2,
    'sad': 1.5,
    'angry': 1.5,
    'fear': 1.5,
    'surprise': 1.5,
    'contempt': 1.3,
    'disgust': 1.3
}

def parse_emotion_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        line = f.read().strip()
    scores = {}
    for part in line.split(','):
        part = part.strip()
        if not part:
            continue
        # 감정명과 숫자 분리
        try:
            k, v = part.split()
            scores[k] = float(v)
        except ValueError:
            continue
    return scores


def get_main_emotions(emotion_scores):
    weighted = {k: v * WEIGHTS.get(k, 1.0) for k, v in emotion_scores.items()}
    sorted_emotions = sorted(weighted.items(), key=lambda x: x[1], reverse=True)
    return sorted_emotions

def generate_comment(emotion_scores):
    sorted_emotions = get_main_emotions(emotion_scores)
    # 방어 코드 추가
    if not sorted_emotions:
        return "감정 분석 결과를 불러올 수 없습니다."
    if len(sorted_emotions) == 1:
        return random.choice(TEMPLATES.get(sorted_emotions[0][0], TEMPLATES['neutral']))
    first, second = sorted_emotions[0], sorted_emotions[1]
    # happy가 0.15 이상이면 happy 우선
    if emotion_scores.get('happy', 0) >= 0.15:
        return random.choice(TEMPLATES['happy'])
    # 부정감정(슬픔, 분노, 혐오, 공포 등)이 0.1 이상이면 neutral보다 우선
    for emo in ['sad', 'angry', 'fear', 'surprise', 'contempt', 'disgust']:
        if emotion_scores.get(emo, 0) >= 0.1:
            # 복합 감정: 두 감정이 0.1 이상이고, 점수 차이가 0.05 이내면 복합 코멘트
            if (emotion_scores.get(second[0], 0) >= 0.1 and abs(first[1] - second[1]) < 0.075 and first[0] != 'neutral'):
                return f"{random.choice(TEMPLATES[first[0]])} 그리고 {random.choice(TEMPLATES[second[0]])}"
            return random.choice(TEMPLATES[emo])
    # neutral이 압도적으로 높을 때
    return random.choice(TEMPLATES['neutral'])

def text_to_speech_and_play(text, lang='ko'):
    if not playsound:
        print("playsound 모듈이 설치되지 않아 음성 재생을 할 수 없습니다. pip install playsound 를 실행하세요.")
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
        tts = gTTS(text=text, lang=lang)
        tts.write_to_fp(tmp)
        tmp_path = tmp.name
    try:
        playsound(tmp_path)
    except Exception as e:
        print(f"음성 재생 중 오류 발생: {e}")
    finally:
        os.remove(tmp_path)

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else 'result.txt'
    emotion_scores = parse_emotion_file(file_path)
    comment = generate_comment(emotion_scores)
    print(comment)
    text_to_speech_and_play(comment)

