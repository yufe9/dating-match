"""소개팅 매칭 로직 (콘솔).

1) 거르기(규칙) → 2) 후보 추리기(로컬 임베딩) → 3) 순위 다시 매기기(규칙 점수) → 4) 이유 설명
v2 기믹: 5) 각자 다르게 보는 호감도 → 안정 매칭 → 쌍방 확인 → 6) 48시간 여행 → 7) 커플·지원금
실행: python match.py          (번호 입력: M07, W12, all, season, check)
      python match.py M01      (한 사람: 1~4단계 + 이번 시즌)
      python match.py season   (시즌 전체)
      python match.py check    (자체 점검 + 시각화 기준값 확인)
      python match.py ask      (질문 검색 화면 docs/ask.html 의 답 docs/ask.json 만들기)
"""
import csv
import hashlib
import json
import random
from collections import Counter
import sys
import unicodedata
from pathlib import Path

# ===================== 설정: 이 숫자만 바꾸면 결과가 바뀝니다 =====================
K = 10                                   # 2단계에서 3단계로 넘길 후보 수
MODEL_NAME = "intfloat/multilingual-e5-small"

# 3단계 규칙 점수표 (기본 합계 100점)
# 외모·연봉 배점을 작게 둔 이유: 배우자 조건 1순위는 성격이고, 오래가는 관계는 가치관·생활습관이 좌우하기 때문.
POINTS = {
    "결혼_같음": 10, "결혼_한칸": 5,                 # 가치관
    "자녀_같음": 10, "자녀_모름": 5,
    "습관_같음": 5, "습관_한칸": 2,                  # 생활습관: 음주·운동·주말스타일·반려동물 각각
    "관심사_개당": 5, "관심사_최대": 20,             # 관심사
    "연락_같음": 6, "연락_한칸": 3, "MBTI_글자": 1,  # 성격·소통
    "나이_0_2": 10, "나이_3_5": 6, "나이_6이상": 3,  # 나이 (구간 경계는 아래 AGE_BANDS)
    "같은구": 10, "같은시": 6, "다른시": 2,          # 거주지
    "외모_겹침": 5,                                  # 외모스타일
    "연봉_충족": 3, "학력_한단계": 2,                # 경제·학력
}
AGE_BANDS = (2, 5)  # 나이 차이 ≤2세 → 나이_0_2, ≤5세 → 나이_3_5, 그 이상 → 나이_6이상
HABITS = ["음주", "운동", "주말스타일", "반려동물"]
# 항목별 만점 (위 점수표에서 자동 계산)
MAX = {
    "가치관": POINTS["결혼_같음"] + POINTS["자녀_같음"],
    "생활습관": POINTS["습관_같음"] * len(HABITS),
    "관심사": POINTS["관심사_최대"],
    "성격·소통": POINTS["연락_같음"] + POINTS["MBTI_글자"] * 4,
    "나이": POINTS["나이_0_2"],
    "거주지": POINTS["같은구"],
    "외모스타일": POINTS["외모_겹침"],
    "경제·학력": POINTS["연봉_충족"] + POINTS["학력_한단계"],
}
# 순서가 있는 값들 — "한 칸 차이"는 이 순서로 셉니다 (반려동물 키움↔싫음은 두 칸이라 0점)
SCALES = {
    "결혼의향": ["1~2년내", "언젠가", "생각없음"],
    "음주": ["안마심", "가끔", "자주"],
    "운동": ["안함", "주1~2", "주3이상"],
    "주말스타일": ["집", "반반", "밖"],
    "반려동물": ["키움", "좋아함", "싫음"],
    "연락빈도": ["자주", "보통", "적게"],
    "연봉구간": ["3천미만", "3~5천", "5~7천", "7천이상"],
    "학력": ["고졸", "전문대", "4년제", "대학원"],
}
# 순서 없는 선택지 (CSV 검증용)
CHOICES = {
    "성별": ["남", "여"], "흡연": ["비흡연", "가끔", "흡연"], "자녀계획": ["원함", "모름", "원치않음"],
    "흡연상대": ["불가", "가능", ""], "종교일치": ["필수", "상관없음", ""],
    "자녀계획일치": ["필수", "상관없음", ""], "희망거주": ["같은시만", "상관없음", ""],
    "희망연봉_최소구간": SCALES["연봉구간"] + [""],
}
NUMBERS = ["나이", "키(cm)"]
OPTIONAL_NUMBERS = ["희망나이_최소", "희망나이_최대", "희망키_최소", "희망키_최대"]
# 1단계 거르기 조건 (본인·같은 성별은 따로 셉니다)
RULES = ["희망 나이", "흡연", "종교 일치", "자녀 계획 일치", "같은 시 거주", "희망 키"]

# ===================== v2 기믹 설정 (1~4단계에는 영향 없음) =====================
SEASON = "2026-가을"       # 첫인상·48시간 여행 시드. 바꾸면 모두 새로 섞입니다
WEIGHT_IMPORTANT = 2.5     # 본인 '중요항목'의 가중치 (나머지 1) → 궁합이 사람마다 달라짐
FIRST_IMPRESSION = 20      # 첫인상 ±값. A→B와 B→A를 따로 뽑아 '한쪽만 설레는' 경우를 만듭니다
MATCH_MIN = 60             # 안정 매칭 선호 목록에 넣을 최소 호감도 (미만이면 차라리 혼자)
PROPOSER = "여"            # 시즌 결과에 쓸 제안 쪽 (시즌마다 번갈아 쓰는 것을 권장)
MUTUAL_TOP = 2             # 쌍방 확인: 서로의 호감도 상위 몇 위 안에 있어야 하는지
MUTUAL_MIN = 85            # 쌍방 확인: 양쪽 호감도 최소값
TRIP_EVENTS = 4            # 48시간 동안 일어나는 이벤트 수 (12시간에 하나)
TRIP_SAME_EVENTS = False   # True면 모든 쌍이 같은 이벤트 순서 (운 대신 궁합만 비교)
TRIP_LUCK = 4              # 이벤트마다 사람별 운 ±값
TRIP_EFFECT = {"같음": 1, "한칸": -4, "두칸": -10}  # 여행은 현실 검증: 잘 맞아도 조금, 안 맞으면 크게
IMPORTANT_BOOST = 1.5      # 이벤트가 내 중요항목이면 효과 배율
COUPLE_MIN = 85            # 여행 뒤 양쪽 최종 호감도가 이 이상이면 커플
# 커플 지원금: 현금이 아닌 둘이 함께 쓰는 데이트 바우처. 순위·매칭 계산에는 절대 쓰지 않습니다
SUBSIDY_TIERS = [(95, 600_000), (90, 400_000), (COUPLE_MIN, 200_000)]  # (평균 최종 호감도 이상, 포인트)
SUBSIDY_SCHEDULE = [(1, 0.3), (3, 0.3), (6, 0.4)]                      # (유지 개월, 지급 비율)

# 48시간 여행 이벤트 풀: (이름, 시험하는 것, 관련 점수 항목)
EVENTS = [
    ("비가 와서 하루 종일 숙소", "주말스타일", "생활습관"),
    ("밤바다 앞 술자리 제안", "음주", "생활습관"),
    ("새벽 해돋이 산책", "운동", "생활습관"),
    ("각자 보내는 반나절", "연락빈도", "성격·소통"),
    ("유기견 보호소 봉사", "반려동물", "생활습관"),
    ("모닥불 앞 미래 이야기", "가치관", "가치관"),
    ("함께 해 보는 취미 체험", "관심사", "관심사"),
    ("지도 없이 길 잃기", "MBTI J/P", "성격·소통"),
    ("맛집 웨이팅 2시간", "운", None),
    ("숙소 앞 깜짝 선물", "운", None),
]

# ===================== 질문 검색 설정 (docs/ask.html, 1~7단계에는 영향 없음) =====================
# 답은 전부 아래 ask_answers()가 1~7단계 결과로 만듭니다. 질문을 바꾸면 python match.py ask 를 다시 실행합니다.
ASK_QUESTIONS = [  # (아이디, 질문, 검색에 걸리는 낱말)
    ("logic", "로직 확인하기", "로직 과정 단계 알고리즘 원리 어떻게 골라 매칭 순서"),
    ("why1", "왜 1위가 잘 맞아?", "1위 이유 잘 맞 궁합 점수 추천"),
    ("diff2", "2위와 뭐가 달라?", "2위 차이 비교 다른 달라"),
    ("low", "점수가 가장 낮은 항목은 왜 낮아?", "낮은 감점 부족 약점 만점"),
    ("filter", "누가 왜 걸러졌어?", "거르기 제외 조건 걸러 탈락 필터"),
    ("shift", "임베딩 순위와 최종 순위는 왜 달라?", "임베딩 순위 변동 유사도 문장 벡터"),
    ("wild", "의외의 궁합은 누구야?", "의외 숨은 후보 빠진 사람"),
    ("table", "점수표는 어떻게 계산돼?", "점수표 배점 계산 기준 100점"),
    ("weight", "외모·연봉 점수는 왜 작아?", "외모 연봉 경제 학력 배점 비중"),
    ("date", "둘이 첫 데이트로 뭘 하면 좋을까?", "데이트 추천 만남 장소 코스 뭐하"),
    ("season", "이번 시즌엔 어떻게 됐어?", "시즌 여행 커플 짝 안정 매칭 결과 호감도"),
]
# 데이트 제안: 둘 다 좋아하는 관심사 → 함께 해 볼 일 (CSV의 관심사 32종 전부, check 가 빠진 것을 찾습니다)
DATE_IDEAS = {
    "여행": "가까운 도시로 당일치기 여행", "독서": "서점에서 서로 책 한 권씩 골라 주기",
    "요리": "시장에서 장을 보고 함께 요리하기", "영화": "영화를 보고 감상 나누기",
    "맛집": "서로 아끼는 맛집 한 곳씩 소개하기", "와인": "와인 바에서 가볍게 한 잔",
    "카페": "조용한 카페에서 긴 대화", "사진": "카메라 들고 동네 사진 산책",
    "음악": "작은 공연장이나 LP 바", "캠핑": "당일 캠핑장 나들이", "러닝": "강변 가벼운 러닝",
    "게임": "게임 카페에서 한 판", "등산": "가까운 산 둘레길 걷기", "베이킹": "베이킹 원데이 클래스",
    "골프": "스크린 골프 한 게임", "반려동물": "반려동물 동반 공원 산책", "공연": "공연 관람",
    "드라이브": "근교 드라이브", "봉사": "하루 봉사 활동", "글쓰기": "북카페에서 짧은 글 바꿔 읽기",
    "전시회": "전시회 관람", "클라이밍": "실내 클라이밍", "요가": "요가 원데이 클래스",
    "헬스": "함께 운동하기", "테니스": "테니스 한 게임", "그림": "드로잉 원데이 클래스",
    "낚시": "바다 낚시", "수영": "실내 수영장", "보드게임": "보드게임 카페",
    "자전거": "강변 자전거", "패션": "쇼핑 산책", "악기": "악기 체험 공방",
}

# 시각화(M06 × W22) 기준값 — 이 숫자가 바뀌면 과제 시각화를 새로 만들어야 합니다
VISUAL_PAIR = ("M06", "W22")
VISUAL_ROW_HASH = {"M06": "553343db3de657b0", "W22": "a1c4aee3cb8003e4"}  # 원래 33칸 값의 해시
VISUAL_EXPECT = {
    "M06": {"통과": 10, "1위": "W03", "1위점수": 91},
    "W22": {"통과": 14, "1위": "M22", "1위점수": 100},
    "점수": {"가치관": 15, "생활습관": 11, "관심사": 5, "성격·소통": 4,
             "나이": 3, "거주지": 6, "외모스타일": 0, "경제·학력": 5},
    "걸린조건": ["희망 나이"], "유사도": 0.908,
}

HERE = Path(__file__).parent
EMB_FILE = HERE / "embeddings.json"
NO_MATCH = "조건에 맞는 사람이 없습니다"


# ------------------------------------------------------------------ 데이터
def _check_row(p):
    """CSV 한 줄의 값이 정해진 선택지·숫자인지 검사. 문제가 있으면 ValueError."""
    def bad(col):
        return ValueError(f"{p.get('번호') or '?'} {col}: '{p.get(col, '')}'")
    for col, ok in list(SCALES.items()) + list(CHOICES.items()):
        if p.get(col, "") not in ok:
            raise bad(col)
    for col in NUMBERS + OPTIONAL_NUMBERS:
        v = p.get(col, "")
        if not (v.isdigit() or (col in OPTIONAL_NUMBERS and v == "")):
            raise bad(col)
    if len(p.get("MBTI", "")) != 4:
        raise bad("MBTI")
    imp = _list(p.get("중요항목", ""))
    if len(imp) > 2 or any(c not in MAX for c in imp):
        raise bad("중요항목")


def load_people():
    """두 CSV를 읽어 앞뒤 공백을 지우고 값을 검증합니다 (학생이 CSV를 고쳐도 엉뚱하게 거르지 않도록)."""
    people = []
    for name in ("men.csv", "women.csv"):
        with open(HERE / name, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                p = {k: (v or "").strip() for k, v in row.items() if k}
                p.setdefault("중요항목", "")  # v1 형식 CSV(칸 없음)도 그대로 읽히게
                _check_row(p)
                people.append(p)
    ids = [p["번호"] for p in people]
    if len(set(ids)) != len(ids):
        raise ValueError("번호가 중복됩니다")
    return people


def _num(v):
    v = (v or "").strip()
    return int(v) if v else None


def _list(v):
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def _step(field, x, y):
    s = SCALES[field]
    return abs(s.index(x) - s.index(y))


# ------------------------------------------------------------------ 1) 거르기
def _out_of_range(lo, hi, x):
    return (lo is not None and x < lo) or (hi is not None and x > hi)


def _fails(rule, a, b):
    """a가 바라는 조건으로 b를 볼 때 걸리면 True."""
    if rule == "희망 나이":
        return _out_of_range(_num(a["희망나이_최소"]), _num(a["희망나이_최대"]), int(b["나이"]))
    if rule == "흡연":
        return a["흡연상대"] == "불가" and b["흡연"] in ("가끔", "흡연")
    if rule == "종교 일치":
        return a["종교일치"] == "필수" and a["종교"] != b["종교"]
    if rule == "자녀 계획 일치":
        return a["자녀계획일치"] == "필수" and {a["자녀계획"], b["자녀계획"]} == {"원함", "원치않음"}
    if rule == "같은 시 거주":
        return a["희망거주"] == "같은시만" and a["거주_시"] != b["거주_시"]
    if rule == "희망 키":
        return _out_of_range(_num(a["희망키_최소"]), _num(a["희망키_최대"]), int(b["키(cm)"]))
    raise ValueError(rule)


def filter_candidates(me, people):
    """양방향 거르기. 조건마다 따로 세므로, 여러 조건에 걸린 사람은 각 조건에 한 번씩 들어갑니다.

    제외[조건] = {"인원": 그 조건에 걸린 사람 수, "내 조건": 내 기준으로 걸린 수, "상대 조건": 상대 기준으로 걸린 수}
    """
    counts = {r: {"인원": 0, "내 조건": 0, "상대 조건": 0} for r in RULES}
    passed, same, dropped = [], 0, 0
    for p in people:
        if p["번호"] == me["번호"] or p["성별"] == me["성별"]:
            same += 1
            continue
        hit = False
        for r in RULES:
            mine, theirs = _fails(r, me, p), _fails(r, p, me)
            counts[r]["내 조건"] += mine
            counts[r]["상대 조건"] += theirs
            if mine or theirs:
                counts[r]["인원"] += 1
                hit = True
        if hit:
            dropped += 1
        else:
            passed.append(p)
    return {"전체": len(people), "본인·같은성별": same, "대상": len(people) - same,
            "제외": counts, "제외인원": dropped, "통과": passed}


def worst_rule(f):
    """가장 많이 거른 조건 (동률이면 RULES 순서상 앞의 것)."""
    return max(RULES, key=lambda r: f["제외"][r]["인원"])


def no_match_message(f):
    r = worst_rule(f)
    c = f["제외"][r]
    return (f"{NO_MATCH}. 가장 많이 거른 조건은 '{r}'입니다 "
            f"({c['인원']}명: 내 조건 {c['내 조건']} · 상대 조건 {c['상대 조건']}).")


# ------------------------------------------------------------------ 2) 임베딩
def embed_text(p):
    # e5 규칙: 두 사람의 문장이 대칭(사람↔사람)이므로 양쪽 모두 "query: "를 붙입니다.
    return (f"query: {p['자기소개']} 관심사: {', '.join(_list(p['관심사']))}. "
            f"주말: {p['주말스타일']}. 결혼 의향: {p['결혼의향']}. 자녀 계획: {p['자녀계획']}.")


def load_embeddings(people, path=EMB_FILE):
    """번호→벡터 사전, 오류 이유, 새로 계산한 인원 수를 돌려줍니다.

    embeddings.json에 저장해 재사용하고, 내용 해시가 바뀐 사람만 다시 계산합니다.
    모델을 불러오지 못하면 (None, 이유, 0)을 돌려줍니다.
    """
    try:
        cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        cache = {}  # 깨진 캐시는 버리고 다시 계산
    if not isinstance(cache, dict):
        cache = {}
    cache = {k: v for k, v in cache.items() if isinstance(v, dict) and "hash" in v and "vec" in v}
    hashes = {p["번호"]: hashlib.sha256((MODEL_NAME + embed_text(p)).encode()).hexdigest()
              for p in people}
    todo = [p for p in people if cache.get(p["번호"], {}).get("hash") != hashes[p["번호"]]]
    if todo:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(MODEL_NAME)
            vecs = model.encode([embed_text(p) for p in todo], normalize_embeddings=True)
        except Exception as e:  # 설치 안 됨·인터넷 없음 등 — 이유만 알리고 3단계로 넘어갑니다
            return None, f"{type(e).__name__}: {str(e).splitlines()[0][:120] if str(e) else ''}", 0
        for p, v in zip(todo, vecs):
            cache[p["번호"]] = {"hash": hashes[p["번호"]], "vec": [round(float(x), 6) for x in v]}
        try:  # 임시 파일에 쓰고 바꿔치기 — 중간에 끊겨도 기존 캐시가 깨지지 않습니다
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except OSError:
            pass  # 저장을 못 해도 이번 실행은 계산한 벡터로 계속합니다 (다음 실행 때 다시 계산)
    return {pid: cache[pid]["vec"] for pid in hashes}, None, len(todo)


def shortlist(me, passed, vecs, k=K):
    """코사인 유사도 상위 k명. 벡터가 없으면 통과자 전원(유사도 None)."""
    if vecs is None:
        return [(p, None) for p in sorted(passed, key=lambda p: p["번호"])]
    mv = vecs[me["번호"]]
    # 정규화된 벡터라 내적이 곧 코사인 유사도
    sims = [(p, sum(a * b for a, b in zip(mv, vecs[p["번호"]]))) for p in passed]
    sims.sort(key=lambda t: (-t[1], t[0]["번호"]))
    return sims[:k]


# ------------------------------------------------------------------ 3) 규칙 점수
def _by_step(d, same, one):
    return same if d == 0 else one if d == 1 else 0


def _looks(a, b):
    """a의 선호 외모와 b의 외모스타일이 겹치면 만점 (선호가 빈칸이면 상관없음 = 충족)."""
    pref = set(_list(a["선호외모스타일"]))
    return POINTS["외모_겹침"] if not pref or pref & set(_list(b["외모스타일"])) else 0


def _econ(a, b):
    want = a["희망연봉_최소구간"].strip()
    ok = not want or SCALES["연봉구간"].index(b["연봉구간"]) >= SCALES["연봉구간"].index(want)
    return (POINTS["연봉_충족"] if ok else 0) + \
           (POINTS["학력_한단계"] if _step("학력", a["학력"], b["학력"]) <= 1 else 0)


def shared_interests(a, b):
    theirs = set(_list(b["관심사"]))
    return [x for x in _list(a["관심사"]) if x in theirs]


def rule_score(a, b):
    """항목별 점수 사전 (키 순서 = MAX 순서)."""
    if a["자녀계획"] == b["자녀계획"]:
        kids = POINTS["자녀_같음"]
    elif "모름" in (a["자녀계획"], b["자녀계획"]):
        kids = POINTS["자녀_모름"]
    else:
        kids = 0
    age_gap = abs(int(a["나이"]) - int(b["나이"]))
    if a["거주_시"] == b["거주_시"]:
        home = POINTS["같은구"] if a["거주_구"] == b["거주_구"] else POINTS["같은시"]
    else:
        home = POINTS["다른시"]
    return {
        "가치관": _by_step(_step("결혼의향", a["결혼의향"], b["결혼의향"]),
                         POINTS["결혼_같음"], POINTS["결혼_한칸"]) + kids,
        "생활습관": sum(_by_step(_step(h, a[h], b[h]), POINTS["습관_같음"], POINTS["습관_한칸"])
                    for h in HABITS),
        "관심사": min(len(shared_interests(a, b)) * POINTS["관심사_개당"], POINTS["관심사_최대"]),
        "성격·소통": _by_step(_step("연락빈도", a["연락빈도"], b["연락빈도"]),
                          POINTS["연락_같음"], POINTS["연락_한칸"])
                   + sum(x == y for x, y in zip(a["MBTI"], b["MBTI"])) * POINTS["MBTI_글자"],
        # 나이 차이는 대칭이라 양방향 평균이 한쪽 값과 같습니다
        "나이": POINTS["나이_0_2"] if age_gap <= AGE_BANDS[0] else POINTS["나이_3_5"]
              if age_gap <= AGE_BANDS[1] else POINTS["나이_6이상"],
        "거주지": home,
        # 선호에 기대는 항목은 나→상대, 상대→나 양방향 평균
        "외모스타일": (_looks(a, b) + _looks(b, a)) / 2,
        "경제·학력": (_econ(a, b) + _econ(b, a)) / 2,
    }


def rank(me, cands):
    rows = []
    for i, (p, sim) in enumerate(cands, 1):
        sc = rule_score(me, p)
        rows.append({"상대": p, "유사도": sim, "임베딩순위": i if sim is not None else None,
                     "점수": sc, "총점": sum(sc.values())})
    # 동점이면 가치관 → 생활습관 → 번호 순 (같은 입력이면 항상 같은 순위)
    rows.sort(key=lambda r: (-r["총점"], -r["점수"]["가치관"], -r["점수"]["생활습관"], r["상대"]["번호"]))
    for i, r in enumerate(rows, 1):
        r["최종순위"] = i
    return rows


# ------------------------------------------------------------------ 4) 이유 설명
def _phrase(cat, a, b, s):
    """항목별 (이어지는 말, 끝맺는 말)."""
    if cat == "가치관":
        m, k = a["결혼의향"] == b["결혼의향"], a["자녀계획"] == b["자녀계획"]
        t = ("결혼 시기와 자녀 계획이 같" if m and k else "결혼 시기가 같" if m
             else "자녀 계획이 같" if k else "결혼·자녀 계획이 비슷하" if s else "결혼·자녀 계획은 다르")
        return t + "고", t + "습니다"
    if cat == "생활습관":
        same = [h for h in HABITS if a[h] == b[h]]
        t = f"생활습관({'·'.join(same)})이 같" if same else "생활습관이 비슷하"
        return t + "고", t + "습니다"
    if cat == "관심사":
        sh = shared_interests(a, b)
        if not sh:
            return "관심사는 겹치지 않고", "관심사는 겹치지 않습니다"
        return f"관심사 {len(sh)}개({'·'.join(sh)})가 겹치고", f"관심사 {len(sh)}개({'·'.join(sh)})가 겹칩니다"
    if cat == "성격·소통":
        d = _step("연락빈도", a["연락빈도"], b["연락빈도"])
        n = sum(x == y for x, y in zip(a["MBTI"], b["MBTI"]))
        c = "연락 빈도가 같고" if d == 0 else "연락 빈도가 비슷하고" if d == 1 else "연락 빈도는 다르지만"
        return f"{c} MBTI가 {n}글자 같고", f"{c} MBTI가 {n}글자 같습니다"
    if cat == "나이":
        g = abs(int(a["나이"]) - int(b["나이"]))
        return ("동갑이고", "동갑입니다") if g == 0 else (f"나이 차이가 {g}살이고", f"나이 차이가 {g}살입니다")
    if cat == "거주지":
        if a["거주_시"] != b["거주_시"]:
            return "사는 곳은 다르고", "사는 곳은 다릅니다"
        if a["거주_구"] == b["거주_구"]:
            return f"같은 동네({a['거주_구']})에 살고", f"같은 동네({a['거주_구']})에 삽니다"
        return f"같은 {a['거주_시']} 생활권이고", f"같은 {a['거주_시']} 생활권입니다"
    if cat == "외모스타일":
        t = ("서로 선호하는 외모 스타일과 맞" if s == MAX[cat]
             else "한쪽이 선호하는 외모 스타일과 맞" if s else "외모 취향은 다르")
        return t + "고", t + "습니다"
    t = "희망 연봉·학력 조건이 맞" if s == MAX[cat] else "경제·학력 조건은 일부 맞"
    return t + "고", t + "습니다"


def explain(me, row):
    """점수가 높은 3개 항목(동률이면 만점 대비 비율이 높은 항목)을 근거로 한 문장."""
    sc = row["점수"]
    top = sorted(MAX, key=lambda c: (-sc[c], -sc[c] / MAX[c], list(MAX).index(c)))[:3]
    parts = []
    for i, c in enumerate(top):
        mid, end = _phrase(c, me, row["상대"], sc[c])
        parts.append(f"{end if i == len(top) - 1 else mid}({sc[c]:g}/{MAX[c]})")
    return ", ".join(parts) + "."


# ------------------------------------------------------------------ 묶음
def recommend(me, people, vecs):
    f = filter_candidates(me, people)
    if not f["통과"]:
        return {"거르기": f, "후보": [], "순위": [], "이유": None}
    cands = shortlist(me, f["통과"], vecs)
    rows = rank(me, cands)
    return {"거르기": f, "후보": cands, "순위": rows, "이유": explain(me, rows[0])}


def wildcard(me, r, vecs):
    """의외의 궁합: 임베딩 상위 K명에 못 들어 3단계에서 빠진 사람 중 규칙 점수 1위 (없으면 None)."""
    if vecs is None or not r["후보"]:
        return None  # 임베딩 없이 돌면 통과자 전원이 이미 3단계에 들어갑니다
    passed = r["거르기"]["통과"]
    emb_rank = {p["번호"]: i for i, (p, _) in enumerate(shortlist(me, passed, vecs, k=len(passed)), 1)}
    inside = {p["번호"] for p, _ in r["후보"]}
    rest = sorted((p for p in passed if p["번호"] not in inside),
                  key=lambda p: (-sum(rule_score(me, p).values()), p["번호"]))
    if not rest:
        return None
    best = rest[0]
    total = sum(rule_score(me, best).values())
    beats = sum(total > row["총점"] for row in r["순위"])  # 후보 K명 중 이 사람보다 점수가 낮은 인원
    return {"상대": best, "총점": total, "임베딩순위": emb_rank[best["번호"]], "앞선인원": beats}


# ------------------------------------------------------------------ 5) 각자 다르게 보기 → 안정 매칭 → 쌍방 확인
def weights(p):
    imp = set(_list(p.get("중요항목", "")))
    return {c: WEIGHT_IMPORTANT if c in imp else 1 for c in MAX}


def affinity(a, b):
    """a가 b를 보는 호감도(100점). 같은 항목 점수에 a의 가중치를 곱하므로 a→b와 b→a가 달라질 수 있습니다."""
    sc, w = rule_score(a, b), weights(a)
    return round(100 * sum(sc[c] * w[c] for c in MAX) / sum(MAX[c] * w[c] for c in MAX), 1)


def first_impression(a_id, b_id):
    """a가 b에게 받은 첫인상(±FIRST_IMPRESSION). 방향마다 따로 뽑으므로 서로 다릅니다."""
    key = f"{SEASON}|첫인상|{a_id}>{b_id}"
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest(), 16))
    return round(rng.uniform(-FIRST_IMPRESSION, FIRST_IMPRESSION), 1)


def season_score(a, b):
    """시즌 호감도 = 궁합(중요항목 가중) + 첫인상, 0~100으로 자름. (궁합, 첫인상, 호감도)"""
    fit, imp = affinity(a, b), first_impression(a["번호"], b["번호"])
    return fit, imp, round(min(100, max(0, fit + imp)), 1)


def season_prefs(people, results):
    """번호 → [(상대 번호, 시즌 호감도), ...] 거르기 통과자 전원을 호감도 높은 순으로."""
    prefs = {}
    for p in people:
        scored = []
        for q in results[p["번호"]]["거르기"]["통과"]:
            fit, imp, s = season_score(p, q)
            scored.append((-s, -(fit + imp), q["번호"], s))  # 100으로 잘린 동점은 자르기 전 값으로 가름
        prefs[p["번호"]] = [(qid, s) for _, _, qid, s in sorted(scored)]
    return prefs


def arrows(prefs):
    """호감도 1위를 화살표로 보고 쌍방·짝사랑·인기 집중·삼각관계를 셉니다."""
    top1 = {pid: lst[0][0] for pid, lst in prefs.items() if lst}
    mutual = sorted({tuple(sorted((a, b))) for a, b in top1.items() if top1.get(b) == a})
    one_way = sorted((a, b) for a, b in top1.items() if top1.get(b) != a)
    votes = Counter(top1.values())
    popular = sorted(votes.items(), key=lambda t: (-t[1], t[0]))
    triangles = []
    for x, n in popular:
        fans = sorted(a for a, b in top1.items() if b == x)
        if n == 2 and top1.get(x) in fans:  # 3명 이상이 몰린 경우는 '인기 집중'에 나옵니다
            triangles.append({"중심": x, "선택": top1[x], "경쟁": [a for a in fans if a != top1[x]]})
    return {"1위": top1, "쌍방": mutual, "짝사랑": one_way, "인기": popular, "삼각관계": triangles}


def _accept(prefs):
    """안정 매칭에 쓸 선호 목록(MATCH_MIN 이상)과 각자의 순위표."""
    accept = {pid: [q for q, s in lst if s >= MATCH_MIN] for pid, lst in prefs.items()}
    return accept, {pid: {q: i for i, q in enumerate(lst)} for pid, lst in accept.items()}


def stable_match(prefs, proposer, gender):
    """게일-섀플리. proposer 성별이 먼저 고백합니다. 번호 → 짝 번호 (양쪽 모두 들어 있음)."""
    accept, rank_of = _accept(prefs)
    free = sorted(pid for pid in accept if gender[pid] == proposer)
    nxt = {pid: 0 for pid in free}
    holds = {}  # 받는 사람 → 지금 붙잡고 있는 제안자
    while free:
        p = free.pop(0)
        if nxt[p] >= len(accept[p]):
            continue  # 제안할 사람이 더 없으면 이번 시즌은 혼자
        r = accept[p][nxt[p]]
        nxt[p] += 1
        cur = holds.get(r)
        if p not in rank_of[r]:
            free.insert(0, p)  # 상대 목록에 내가 없음 → 바로 다음 사람에게
        elif cur is None:
            holds[r] = p
        elif rank_of[r][p] < rank_of[r][cur]:
            holds[r] = p
            free.insert(0, cur)
        else:
            free.insert(0, p)
    pairs = {}
    for r, p in holds.items():
        pairs[p], pairs[r] = r, p
    return pairs


def blocking_pairs(prefs, pairs):
    """'서로 지금 짝보다 상대를 더 원하는' 쌍 목록. 비어 있어야 안정 매칭입니다."""
    accept, rank_of = _accept(prefs)
    out = []
    for a, lst in accept.items():
        for b in lst:
            if pairs.get(a) == b or a not in rank_of[b]:
                continue
            a_wants = a not in pairs or rank_of[a][b] < rank_of[a][pairs[a]]
            b_wants = b not in pairs or rank_of[b][a] < rank_of[b][pairs[b]]
            if a_wants and b_wants:
                out.append((a, b))
    return out


def mutual_check(a, b, prefs, pairs):
    """쌍방 확인 세 조건 → {조건 이름: 통과 여부}. 셋 다 통과해야 48시간 여행.

    shortcut: 통과자가 MUTUAL_TOP명 이하인 사람에게는 '상위 N위' 조건이 늘 참입니다.
    선택지가 적은 사람을 불리하게 만들지 않으려고 둔 것이며, 더 엄격하게 하려면 통과자 수 조건을 추가하세요.
    """
    top_a = [q for q, _ in prefs[a][:MUTUAL_TOP]]
    top_b = [q for q, _ in prefs[b][:MUTUAL_TOP]]
    sa, sb = dict(prefs[a]).get(b, 0), dict(prefs[b]).get(a, 0)
    return {"안정 매칭 짝": pairs.get(a) == b,
            f"서로 상위 {MUTUAL_TOP}위": b in top_a and a in top_b,
            f"양쪽 호감도 {MUTUAL_MIN}+": min(sa, sb) >= MUTUAL_MIN}


# ------------------------------------------------------------------ 6) 48시간 여행 → 7) 커플·지원금
def trip_rng(a_id, b_id):
    """쌍 전용 난수. 번호를 정렬해 넣으므로 누가 조회해도 같은 여행입니다 (파이썬 hash()는 실행마다 바뀌어 쓰지 않음)."""
    key = SEASON if TRIP_SAME_EVENTS else f"{SEASON}|{'|'.join(sorted([a_id, b_id]))}"
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest(), 16))


def _event_kind(test, a, b):
    """이벤트가 시험하는 성향을 비교해 '같음'·'한칸'·'두칸'·'운' 중 하나."""
    if test == "운":
        return "운"
    if test in SCALES:
        d = _step(test, a[test], b[test])
    elif test == "가치관":
        s = rule_score(a, b)["가치관"]
        d = 0 if s == MAX["가치관"] else 1 if s >= MAX["가치관"] / 2 else 2
    elif test == "관심사":
        n = len(shared_interests(a, b))
        d = 0 if n >= 2 else 1 if n == 1 else 2
    else:  # MBTI J/P — 길 잃었을 때 계획파와 즉흥파
        d = 0 if a["MBTI"][3] == b["MBTI"][3] else 2
    return ("같음", "한칸", "두칸")[d]


def run_trip(a, b, start):
    """48시간 여행. start = {번호: 시작 호감도}. 같은 쌍·같은 시즌이면 항상 같은 결과."""
    m, w = (a, b) if a["성별"] == "남" else (b, a)  # 순서를 고정해 조회 방향과 무관하게
    rng = trip_rng(m["번호"], w["번호"])
    now = {m["번호"]: start[m["번호"]], w["번호"]: start[w["번호"]]}
    log = []
    for name, test, cat in rng.sample(EVENTS, TRIP_EVENTS):
        kind = _event_kind(test, m, w)
        base = 0 if kind == "운" else TRIP_EFFECT[kind]
        delta = {}
        for p in (m, w):
            boost = IMPORTANT_BOOST if cat and cat in _list(p.get("중요항목", "")) else 1
            raw = base * boost + rng.randint(-TRIP_LUCK, TRIP_LUCK)
            new = round(min(100, max(0, now[p["번호"]] + raw)), 1)
            delta[p["번호"]] = round(new - now[p["번호"]], 1)  # 0~100으로 자른 뒤 실제로 바뀐 만큼
            now[p["번호"]] = new
        log.append({"이벤트": name, "시험": test, "결과": kind, "변화": delta, "호감도": dict(now)})
    return {"로그": log, "최종": now, "커플": min(now.values()) >= COUPLE_MIN}


def subsidy(final):
    """커플 지원금(데이트 바우처). 마지막 회차가 나머지를 받아 분할 합계가 총액과 정확히 같습니다."""
    avg = sum(final.values()) / len(final)
    total = next((pts for th, pts in SUBSIDY_TIERS if avg >= th), 0)
    plan, paid = [], 0
    for i, (month, ratio) in enumerate(SUBSIDY_SCHEDULE):
        amt = total - paid if i == len(SUBSIDY_SCHEDULE) - 1 else round(total * ratio)
        plan.append((month, amt))
        paid += amt
    return {"평균": round(avg, 1), "총액": total, "분할": plan}


def run_season(people, results):
    """시즌 전체: 화살표 → 안정 매칭(양방향) → 쌍방 확인 → 여행 → 커플·지원금."""
    by_id = {p["번호"]: p for p in people}
    gender = {p["번호"]: p["성별"] for p in people}
    prefs = season_prefs(people, results)
    both = {g: stable_match(prefs, g, gender) for g in ("남", "여")}
    pairs = both[PROPOSER]
    changed = sorted(pid for pid in prefs if both["남"].get(pid) != both["여"].get(pid))
    entries = {}
    for m in sorted(pid for pid in pairs if gender[pid] == "남"):
        w = pairs[m]
        start = {m: dict(prefs[m])[w], w: dict(prefs[w])[m]}
        e = {"남": m, "여": w, "호감도": start, "확인": mutual_check(m, w, prefs, pairs)}
        if all(e["확인"].values()):
            e["여행"] = run_trip(by_id[m], by_id[w], start)
            if e["여행"]["커플"]:
                e["지원금"] = subsidy(e["여행"]["최종"])  # 커플이 정해진 뒤에만 계산 — 선택에 영향 없음
        entries[m] = entries[w] = e
    return {"선호": prefs, "화살표": arrows(prefs), "매칭": both, "달라진": changed, "쌍": entries}


# ------------------------------------------------------------------ 질문 검색 답 (docs/ask.html)
def _j(word, pair):
    """받침에 맞는 조사를 붙입니다. pair = '이가'·'은는'·'과와'·'을를'."""
    ch = word[-1]
    batchim = "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 > 0
    return word + (pair[0] if batchim else pair[1])


def _how(c, a, b, s):
    """항목 점수가 어떻게 나왔는지 한 문장. 이름을 붙여 누구의 값인지 분명히 합니다."""
    an, bn = a["이름"], b["이름"]
    if c == "가치관":
        d = _step("결혼의향", a["결혼의향"], b["결혼의향"])
        mp = _by_step(d, POINTS["결혼_같음"], POINTS["결혼_한칸"])
        return (f"결혼 시기 {mp}점({an} {a['결혼의향']}, {bn} {b['결혼의향']}) + "
                f"자녀 계획 {s - mp:g}점({an} {a['자녀계획']}, {bn} {b['자녀계획']})")
    if c == "생활습관":
        parts = []
        for h in HABITS:
            pts = _by_step(_step(h, a[h], b[h]), POINTS["습관_같음"], POINTS["습관_한칸"])
            parts.append(f"{h} {pts}점(둘 다 {a[h]})" if a[h] == b[h] else f"{h} {pts}점({an} {a[h]}, {bn} {b[h]})")
        return " + ".join(parts)
    if c == "관심사":
        sh = shared_interests(a, b)
        only_a = [x for x in _list(a["관심사"]) if x not in sh]
        only_b = [x for x in _list(b["관심사"]) if x not in sh]
        t = (f"둘 다 좋아하는 관심사 {len(sh)}개({'·'.join(sh)}) × {POINTS['관심사_개당']}점" if sh
             else "겹치는 관심사가 없어 0점")
        return t + (f". {an}만 {'·'.join(only_a)}" if only_a else "") + (f", {bn}만 {'·'.join(only_b)}" if only_b else "")
    if c == "성격·소통":
        cp = _by_step(_step("연락빈도", a["연락빈도"], b["연락빈도"]), POINTS["연락_같음"], POINTS["연락_한칸"])
        n = sum(x == y for x, y in zip(a["MBTI"], b["MBTI"]))
        return (f"연락 빈도 {cp}점({an} {a['연락빈도']}, {bn} {b['연락빈도']}) + "
                f"MBTI 같은 자리 {n}글자 × {POINTS['MBTI_글자']}점({an} {a['MBTI']}, {bn} {b['MBTI']})")
    if c == "나이":
        gap = abs(int(a["나이"]) - int(b["나이"]))
        return (f"{an} {a['나이']}세, {bn} {b['나이']}세로 {gap}살 차이 "
                f"({AGE_BANDS[0]}살 이내 {POINTS['나이_0_2']}점, {AGE_BANDS[1]}살 이내 {POINTS['나이_3_5']}점, "
                f"그 이상 {POINTS['나이_6이상']}점)")
    if c == "거주지":
        if a["거주_시"] != b["거주_시"]:
            t = f"사는 시가 다름({an} {a['거주_시']}, {bn} {b['거주_시']})"
        elif a["거주_구"] == b["거주_구"]:
            t = f"둘 다 {a['거주_시']} {a['거주_구']}"
        else:
            t = f"같은 {a['거주_시']}이지만 {an} {a['거주_구']}, {bn} {b['거주_구']}"
        return t + f" (같은 구 {POINTS['같은구']}점, 같은 시 {POINTS['같은시']}점, 다른 시 {POINTS['다른시']}점)"
    return _phrase(c, a, b, s)[1] + " (나→상대, 상대→나 평균)"


def _p(text):
    return {"t": "p", "text": text}


def _ratio_items(sc, best=True, n=2):
    """만점 대비 비율이 높은(낮은) 항목 n개."""
    key = (lambda c: (-sc[c] / MAX[c], list(MAX).index(c))) if best else (lambda c: (sc[c] / MAX[c], list(MAX).index(c)))
    return sorted(MAX, key=key)[:n]


def ask_answers(me, r, wc, season, by_id):
    """질문 아이디 → 답(블록 목록). 전부 1~7단계 결과로 만들며 순위·점수는 바꾸지 않습니다.

    블록: {"t": "p", "text"} 문단 · {"t": "steps", "items": [{"h", "text"}]} 단계
          {"t": "bars", "items": [{"label", "v", "max", "note"}]} 점수 막대 · {"t": "table", "head", "rows"} 표
          {"t": "list", "items": [문장]} 목록
    """
    f, rows, cands, mn = r["거르기"], r["순위"], r["후보"], me["이름"]
    n = len(f["통과"])
    A = {
        "filter": [_p(f"반대 성별 {f['대상']}명 중 {f['제외인원']}명이 거르기 조건에 걸려 {n}명이 남았습니다. "
                      "나→상대(내 조건)와 상대→나(상대 조건)를 모두 검사합니다."),
                   {"t": "table", "head": ["조건", "걸린 인원", "내 조건으로", "상대 조건으로"],
                    "rows": [[rule, f"{c['인원']}명", f"{c['내 조건']}명", f"{c['상대 조건']}명"]
                             for rule, c in ((rule, f["제외"][rule]) for rule in RULES)]},
                   _p("한 사람이 여러 조건에 걸리면 조건마다 따로 세므로, 조건별 인원의 합은 실제로 걸러진 인원보다 클 수 있습니다.")],
        "table": [_p(f"100점 만점 규칙 점수입니다. 임베딩으로 추린 후보 {K}명을 이 점수로 다시 줄 세웁니다."),
                  {"t": "table", "head": ["항목", "배점", "계산"], "rows": [
                      ["가치관", f"{MAX['가치관']}", f"결혼의향 같으면 {POINTS['결혼_같음']}, 한 칸 차이 {POINTS['결혼_한칸']} / 자녀계획 같으면 {POINTS['자녀_같음']}, 한쪽이 모름이면 {POINTS['자녀_모름']}"],
                      ["생활습관", f"{MAX['생활습관']}", f"{'·'.join(HABITS)} 각각 같으면 {POINTS['습관_같음']}, 한 칸 차이 {POINTS['습관_한칸']}"],
                      ["관심사", f"{MAX['관심사']}", f"겹치는 관심사 1개당 {POINTS['관심사_개당']}, 최대 {POINTS['관심사_최대']}"],
                      ["성격·소통", f"{MAX['성격·소통']}", f"연락빈도 같으면 {POINTS['연락_같음']}, 한 칸 차이 {POINTS['연락_한칸']} / MBTI 같은 자리 글자당 {POINTS['MBTI_글자']}"],
                      ["나이", f"{MAX['나이']}", f"차이 {AGE_BANDS[0]}살 이내 {POINTS['나이_0_2']}, {AGE_BANDS[1]}살 이내 {POINTS['나이_3_5']}, 그 이상 {POINTS['나이_6이상']}"],
                      ["거주지", f"{MAX['거주지']}", f"같은 구 {POINTS['같은구']}, 같은 시 {POINTS['같은시']}, 다른 시 {POINTS['다른시']}"],
                      ["외모스타일", f"{MAX['외모스타일']}", f"선호 키워드와 상대 외모스타일이 겹치면 {POINTS['외모_겹침']} (선호가 빈칸이면 충족)"],
                      ["경제·학력", f"{MAX['경제·학력']}", f"희망 연봉 구간 이상 {POINTS['연봉_충족']} + 학력 차이 한 단계 이내 {POINTS['학력_한단계']}"]]},
                  _p("외모스타일·경제·학력은 나→상대, 상대→나 양방향 평균이라 2.5점 같은 값이 나옵니다. "
                     "총점이 같으면 가치관 → 생활습관 → 번호 순으로 정합니다.")],
        "weight": [_p(f"외모스타일 {MAX['외모스타일']}점, 경제·학력 {MAX['경제·학력']}점으로 100점 중 "
                      f"{MAX['외모스타일'] + MAX['경제·학력']}점입니다. 가치관·생활습관·관심사는 각 {MAX['가치관']}점입니다."),
                   _p("배우자 조건 1순위는 성격이고, 오래가는 관계는 가치관·생활습관이 좌우한다고 보고 배점을 정했습니다. "
                      "외모와 연봉은 '선호에 맞는지'만 보고 크기를 따지지 않습니다.")],
    }
    if not rows:  # 거르기 통과자가 0명: 1단계만 있고 나머지 질문은 답할 내용이 없음
        none = [_p(no_match_message(f)), _p("1단계에서 모두 걸러져 2~4단계와 시즌은 진행되지 않았습니다.")]
        A["logic"] = [{"t": "steps", "items": [{"h": "1 거르기", "text": no_match_message(f)}]}]
        for qid, _, _ in ASK_QUESTIONS:
            A.setdefault(qid, none)
        return A

    top, p1 = rows[0], rows[0]["상대"]
    sims = cands and cands[0][1] is not None
    A["logic"] = [{"t": "steps", "items": [
        {"h": "1 거르기", "text": f"전체 {f['전체']}명 중 본인·같은 성별을 빼면 {f['대상']}명. 희망 나이·흡연·종교·자녀 계획·"
                               f"거주지·키 조건을 나→상대, 상대→나 양방향으로 검사해 {f['제외인원']}명을 거르고 {n}명이 남았습니다."},
        {"h": "2 후보 추리기", "text": (f"남은 {n}명의 자기소개·관심사·주말·결혼·자녀 문장을 임베딩 모델({MODEL_NAME})로 "
                                   f"숫자 벡터로 바꾸고, {mn}님과 문장이 비슷한 순으로 {len(cands)}명을 골랐습니다. "
                                   f"가장 비슷한 사람은 {cands[0][0]['이름']}(유사도 {cands[0][1]:.3f})입니다.")
                                  if sims else f"임베딩 모델 없이 {n}명 전원을 3단계로 넘겼습니다."},
        {"h": "3 순위", "text": f"{len(rows)}명을 100점 규칙 점수로 다시 줄 세웠습니다. "
                              + ", ".join(f"{x['최종순위']}위 {x['상대']['이름']} {x['총점']:g}점" for x in rows[:3]) + "."},
        {"h": "4 이유", "text": f"1위 {p1['이름']}: {r['이유']}"}]}]

    A["why1"] = [_p(f"{_j(p1['이름'], '은는')} {mn}님의 1위, 규칙 점수 {top['총점']:g}/100점입니다."
                    + (f" 문장 유사도로는 {top['임베딩순위']}위였습니다." if top["임베딩순위"] else "")),
                 {"t": "bars", "items": [{"label": c, "v": top["점수"][c], "max": MAX[c],
                                          "note": _how(c, me, p1, top["점수"][c])} for c in MAX]},
                 _p("한 줄로: " + r["이유"])]

    if len(rows) < 2:
        A["diff2"] = [_p("후보가 1명뿐이라 비교할 2위가 없습니다.")]
    else:
        a, b = rows[0], rows[1]
        pa, pb = a["상대"]["이름"], b["상대"]["이름"]
        diff = [c for c in MAX if a["점수"][c] != b["점수"][c]]
        head = (f"1위 {pa} {a['총점']:g}점과 2위 {pb} {b['총점']:g}점은 {a['총점'] - b['총점']:g}점 차이입니다. "
                + (f"점수가 다른 항목은 {'·'.join(diff)}이고 나머지는 같습니다." if diff
                   else "모든 항목 점수가 같아 가치관 → 생활습관 → 번호 순으로 정했습니다."))
        A["diff2"] = [_p(head)]
        if diff:
            A["diff2"].append({"t": "table", "head": ["항목", f"1위 {pa}", f"2위 {pb}"],
                               "rows": [[c, f"{a['점수'][c]:g}/{MAX[c]}", f"{b['점수'][c]:g}/{MAX[c]}"] for c in diff]})
            for c in diff:
                A["diff2"].append({"t": "list", "h": c, "items": [
                    f"{pa}: " + _how(c, me, a["상대"], a["점수"][c]), f"{pb}: " + _how(c, me, b["상대"], b["점수"][c])]})

    sc = top["점수"]
    low = [c for c in _ratio_items(sc, best=False, n=len(MAX)) if sc[c] < MAX[c]]
    if not low:
        A["low"] = [_p(f"1위 {p1['이름']}님은 모든 항목이 만점입니다.")]
    else:
        c = low[0]
        A["low"] = [_p(f"1위 {p1['이름']}님에게서 만점 대비 가장 낮은 항목은 {c} {sc[c]:g}/{MAX[c]}점"
                       f"({round(100 * sc[c] / MAX[c])}%)입니다."), _p(f"{c} 계산: " + _how(c, me, p1, sc[c]) + ".")]
        if len(low) > 1:
            A["low"].append(_p("그 밖에 만점이 아닌 항목: " + ", ".join(f"{x} {sc[x]:g}/{MAX[x]}" for x in low[1:]) + "."))

    if not sims:
        A["shift"] = [_p("임베딩 모델 없이 돌아 문장 유사도 순위가 없습니다. 통과자 전원을 규칙 점수로만 줄 세웠습니다.")]
    else:
        moved = [(x["임베딩순위"] - x["최종순위"], x) for x in rows]
        up, down = max(moved, key=lambda t: (t[0], -t[1]["최종순위"])), min(moved, key=lambda t: (t[0], t[1]["최종순위"]))
        A["shift"] = [_p("임베딩은 자기소개 문장이 얼마나 비슷한지만 보고, 최종 순위는 결혼·자녀 계획·생활습관 같은 조건을 "
                         "점수로 매깁니다. 그래서 문장은 비슷해도 조건이 다르면 내려가고, 반대도 생깁니다."),
                      {"t": "table", "head": ["이름", "임베딩", "최종", "변동"],
                       "rows": [[x["상대"]["이름"], f"{x['임베딩순위']}위", f"{x['최종순위']}위",
                                 "=" if d == 0 else (f"▲{d}" if d > 0 else f"▼{-d}")] for d, x in moved]}]
        if up[0] > 0:
            x = up[1]
            A["shift"].append(_p(f"가장 크게 오른 사람은 {x['상대']['이름']}(임베딩 {x['임베딩순위']}위 → 최종 {x['최종순위']}위)입니다. "
                                 + ", ".join(f"{c} {x['점수'][c]:g}/{MAX[c]}" for c in _ratio_items(x["점수"]))
                                 + "에서 점수가 높았습니다."))
        if down[0] < 0:
            x = down[1]
            A["shift"].append(_p(f"가장 크게 내려간 사람은 {x['상대']['이름']}(임베딩 {x['임베딩순위']}위 → 최종 {x['최종순위']}위)입니다. "
                                 + ", ".join(f"{c} {x['점수'][c]:g}/{MAX[c]}" for c in _ratio_items(x["점수"], best=False))
                                 + "에서 점수가 낮았습니다."))

    if wc is None:
        A["wild"] = [_p("통과자 전원이 이미 3단계 후보에 들어가 따로 뽑을 사람이 없습니다.")]
    else:
        w, wsc = wc["상대"], rule_score(me, wc["상대"])
        A["wild"] = [_p(f"{w['이름']}({w['번호']}, {w['나이']}세, {w['거주_시']} {w['거주_구']})님은 문장 유사도 "
                        f"{wc['임베딩순위']}위라 후보 {K}명에 못 들었지만, 규칙 점수는 {wc['총점']:g}점으로 후보 {K}명 중 "
                        f"{wc['앞선인원']}명보다 높습니다."),
                     _p("잘 맞는 항목: " + ", ".join(f"{c} {wsc[c]:g}/{MAX[c]}" for c in _ratio_items(wsc, n=3)) + ".")]

    sh = shared_interests(me, p1)
    pn = p1["이름"]
    tips = []
    if me["주말스타일"] == p1["주말스타일"]:
        tips.append({"집": "둘 다 주말엔 집이 편한 편이라 붐비는 곳보다 조용한 곳이 맞겠습니다.",
                     "밖": "둘 다 주말엔 밖이 좋은 편이라 바깥 활동이 잘 맞겠습니다.",
                     "반반": "둘 다 주말을 반반 보내는 편이라 낮엔 밖, 저녁엔 조용한 곳으로 나누면 좋겠습니다."}[me["주말스타일"]])
    else:
        tips.append(f"주말 스타일이 달라({mn} {me['주말스타일']}, {pn} {p1['주말스타일']}) 첫 만남은 짧은 일정이 무난하겠습니다.")
    drinkers = [x["음주"] for x in (me, p1)]
    if drinkers.count("안마심") == 2:
        tips.append("둘 다 술을 마시지 않으니 식사와 카페 위주가 좋겠습니다.")
    elif "안마심" in drinkers:
        tips.append("한 분은 술을 마시지 않으니 술자리보다 식사·카페가 무난하겠습니다.")
    A["date"] = [_p(f"{mn}님과 1위 {pn}님이 둘 다 좋아하는 것: {'·'.join(sh)}." if sh else
                    f"{mn}님과 1위 {pn}님은 겹치는 관심사가 없습니다."),
                 {"t": "list", "items": [f"{x}: {DATE_IDEAS.get(x, x + ' 함께 해 보기')}" for x in sh] if sh else
                  [f"{mn}님의 {_j(_list(me['관심사'])[0], '과와')} {pn}님의 {_j(_list(p1['관심사'])[0], '을를')} "
                   "한 번씩 번갈아 해 보기"]},
                 _p(" ".join(tips)),
                 _p("두 사람의 공통 관심사와 주말·음주 습관 규칙으로 고른 제안입니다.")]

    pid = me["번호"]
    prefs, e = season["선호"].get(pid, []), season["쌍"].get(pid)
    imp = me.get("중요항목") or "없음(균형형)"
    S = [_p(f"이번 시즌({SEASON}) 호감도 = 궁합(항목 점수 × 내 중요항목 {WEIGHT_IMPORTANT}배) + 첫인상(±{FIRST_IMPRESSION}). "
            f"{mn}님의 중요항목: {imp}.")]
    if prefs:
        S.append({"t": "table", "head": ["상대", "내가 보는 호감도", "상대가 나를 보는 호감도"],
                  "rows": [[by_id[q]["이름"], f"{s:.1f}", f"{dict(season['선호'][q]).get(pid, 0):.1f}"]
                           for q, s in prefs[:3]]})
    if e is None:
        S.append(_p(f"호감도 {MATCH_MIN}점 이상인 상대와 짝이 맺어지지 않아 이번 시즌은 혼자입니다."))
    else:
        mate = e["여"] if e["남"] == pid else e["남"]
        S.append(_p(f"안정 매칭 짝은 {by_id[mate]['이름']}님입니다. 쌍방 확인: "
                    + ", ".join(f"{k} {'통과' if ok else '탈락'}" for k, ok in e["확인"].items()) + "."))
        if "여행" not in e:
            S.append(_p("쌍방 확인을 모두 통과하지 못해 48시간 여행은 가지 않았습니다."))
        else:
            label = {"같음": "잘 맞음", "한칸": "그럭저럭", "두칸": "부딪힘", "운": "운"}
            t = e["여행"]
            S.append({"t": "table", "head": ["48시간 여행", "결과", f"{mn} 호감도", f"{by_id[mate]['이름']} 호감도"],
                      "rows": [[ev["이벤트"], label[ev["결과"]], f"{ev['호감도'][pid]:.1f} ({ev['변화'][pid]:+.1f})",
                                f"{ev['호감도'][mate]:.1f} ({ev['변화'][mate]:+.1f})"] for ev in t["로그"]]})
            if t["커플"]:
                s = e["지원금"]
                S.append(_p(f"최종 호감도 {t['최종'][pid]:.1f} / {t['최종'][mate]:.1f}로 양쪽 모두 {COUPLE_MIN}점 이상이라 "
                            f"커플이 됐습니다. 데이트 바우처 {s['총액']:,}P를 "
                            + " · ".join(f"{mo}개월 {amt:,}P" for mo, amt in s["분할"]) + "로 나눠 받습니다."))
            else:
                S.append(_p(f"최종 호감도 {t['최종'][pid]:.1f} / {t['최종'][mate]:.1f}. 한쪽 이상이 {COUPLE_MIN}점에 못 미쳐 "
                            "커플이 되지 않았습니다."))
    A["season"] = S
    return A


def ask_export(people, results, season, vecs):
    """docs/ask.json: 질문 목록 + 사람 목록 + 사람별 답. 웹은 이 값을 그대로 보여 주기만 합니다."""
    by_id = {p["번호"]: p for p in people}
    answers = {}
    for p in people:
        r = results[p["번호"]]
        wc = wildcard(p, r, vecs) if r["순위"] else None
        answers[p["번호"]] = ask_answers(p, r, wc, season, by_id)
    return {"questions": [{"id": q, "q": text, "keys": keys} for q, text, keys in ASK_QUESTIONS],
            "people": [{"id": p["번호"], "name": p["이름"], "sex": p["성별"], "age": int(p["나이"]),
                        "home": f"{p['거주_시']} {p['거주_구']}"} for p in people],
            "answers": answers}


def ask_check(people, results, season, vecs):
    """질문 검색 답 점검 — 하나라도 어기면 AssertionError."""
    missing = sorted({x for p in people for x in _list(p["관심사"])} - set(DATE_IDEAS))
    assert not missing, f"DATE_IDEAS에 없는 관심사: {missing}"
    data = ask_export(people, results, season, vecs)
    ids = [q["id"] for q in data["questions"]]
    for p in people:
        ans, r = data["answers"][p["번호"]], results[p["번호"]]
        assert ids == [q for q, _, _ in ASK_QUESTIONS] and set(ans) == set(ids), p["번호"]
        if r["순위"]:  # 1위 답의 이름·총점이 3단계 결과와 같아야 함
            top = r["순위"][0]
            assert ans["why1"][0]["text"].startswith(_j(top["상대"]["이름"], "은는"))
            assert f"{top['총점']:g}/100점" in ans["why1"][0]["text"]
    return data


def visual_check(people, results, vecs):
    """과제 시각화(M06 × W22)에 쓴 숫자가 그대로인지. 어긋난 항목 목록 (빈 목록이면 정상)."""
    by_id = {p["번호"]: p for p in people}
    bad = []
    for pid, h in VISUAL_ROW_HASH.items():
        p = by_id.get(pid)
        if p is None:
            bad.append(f"{pid}가 없습니다")
            continue
        raw = "|".join(v for k, v in p.items() if k != "중요항목")
        if hashlib.sha256(raw.encode()).hexdigest()[:16] != h:
            bad.append(f"{pid}의 프로필 값이 바뀌었습니다")
        if p.get("중요항목"):
            bad.append(f"{pid}의 중요항목이 비어 있지 않습니다")
        exp, r = VISUAL_EXPECT[pid], results[pid]
        got = (len(r["거르기"]["통과"]), r["순위"][0]["상대"]["번호"] if r["순위"] else None,
               r["순위"][0]["총점"] if r["순위"] else None)
        if got != (exp["통과"], exp["1위"], exp["1위점수"]):
            bad.append(f"{pid}의 통과 인원·1위가 바뀌었습니다: {got}")
    if not bad:
        m, w = (by_id[x] for x in VISUAL_PAIR)
        if rule_score(m, w) != VISUAL_EXPECT["점수"]:
            bad.append("M06 × W22 규칙 점수가 바뀌었습니다")
        hit = [rule for rule in RULES if _fails(rule, m, w) and _fails(rule, w, m)]
        any_hit = [rule for rule in RULES if _fails(rule, m, w) or _fails(rule, w, m)]
        if hit != VISUAL_EXPECT["걸린조건"] or any_hit != VISUAL_EXPECT["걸린조건"]:
            bad.append(f"M06 × W22 거르기 결과가 바뀌었습니다: {any_hit}")
        if vecs is not None:
            sim = round(sum(a * b for a, b in zip(vecs[m["번호"]], vecs[w["번호"]])), 3)
            if sim != VISUAL_EXPECT["유사도"]:
                bad.append(f"M06 × W22 임베딩 유사도가 바뀌었습니다: {sim}")
    return bad


def export_web(people):
    """웹 앱(docs/app.html)이 쓸 프로필과 점수표. 파이썬과 웹이 같은 숫자를 쓰게 하려는 것입니다."""
    return {"profiles": people, "POINTS": POINTS, "MAX": MAX, "SCALES": SCALES, "HABITS": HABITS,
            "AGE_BANDS": list(AGE_BANDS), "WEIGHT_IMPORTANT": WEIGHT_IMPORTANT, "K": K,
            # 48시간 여행 규칙 — 웹의 여행 재생도 같은 이벤트·효과·커플 기준을 씁니다
            "EVENTS": [list(e) for e in EVENTS], "TRIP_EVENTS": TRIP_EVENTS, "TRIP_EFFECT": TRIP_EFFECT,
            "TRIP_LUCK": TRIP_LUCK, "IMPORTANT_BOOST": IMPORTANT_BOOST, "COUPLE_MIN": COUPLE_MIN,
            "FIRST_IMPRESSION": FIRST_IMPRESSION}


def self_check(people, vecs):
    """자체 점검 — 하나라도 어기면 AssertionError."""
    by_id = {p["번호"]: p for p in people}
    results = {pid: recommend(p, people, vecs) for pid, p in by_id.items()}
    # 1) 나 자신과 같은 성별은 추천되지 않는다
    for pid, r in results.items():
        for row in r["순위"]:
            assert row["상대"]["번호"] != pid and row["상대"]["성별"] != by_id[pid]["성별"], pid
    # 아래 2)·3)은 데이터를 고쳐도 깨지지 않게 가상 프로필을 만들어 확인합니다
    pid, r = next((pid, r) for pid, r in results.items() if r["거르기"]["통과"])
    me, other = by_id[pid], r["거르기"]["통과"][0]
    # 2) 흡연 불가 조건이 작동한다 (통과하던 상대를 흡연자로 바꾸면 걸러져야 함)
    f = filter_candidates(dict(me, 흡연상대="불가"), [dict(other, 흡연="흡연")])
    assert not f["통과"] and f["제외"]["흡연"]["내 조건"] == 1
    # 3) 통과자 0명일 때 안내가 나온다
    f = filter_candidates(dict(me, 희망나이_최소="99", 희망나이_최대="99"), people)
    assert not f["통과"] and no_match_message(f).startswith(NO_MATCH)
    assert recommend(dict(me, 희망나이_최소="99"), people, vecs)["순위"] == []
    # 4) 같은 입력이면 순위가 항상 똑같다
    again = recommend(me, people, vecs)
    assert [x["상대"]["번호"] for x in again["순위"]] == [x["상대"]["번호"] for x in r["순위"]]

    # --- v2 기믹 점검 ---
    assert PROPOSER in ("남", "여"), f"PROPOSER는 '남' 또는 '여'여야 합니다: {PROPOSER!r}"
    season = run_season(people, results)
    # 5) 중요항목이 없으면 궁합 = 규칙 점수를 100점으로 환산한 값 (가중치는 시즌 호감도에만 영향)
    plain = round(100 * sum(rule_score(me, other).values()) / sum(MAX.values()), 1)
    assert affinity(dict(me, 중요항목=""), other) == plain
    # 5-1) 시즌 호감도는 0~100 안이고 높은 순으로 정렬돼 있다
    for lst in season["선호"].values():
        scores = [s for _, s in lst]
        assert all(0 <= s <= 100 for s in scores) and scores == sorted(scores, reverse=True)
    # 6) blocking_pairs가 실제로 찾아낸다 (서로 원하는데 둘 다 혼자인 쌍) — 아래 검사가 헛돌지 않게
    assert blocking_pairs({"A": [("B", 99)], "B": [("A", 99)]}, {}) == [("A", "B"), ("B", "A")]
    # 6-1) 두 방향 안정 매칭 모두 '서로 더 원하는 쌍'이 없고, 짝은 서로 MATCH_MIN 이상인 반대 성별
    for pairs in season["매칭"].values():
        assert not blocking_pairs(season["선호"], pairs)
        for a, b in pairs.items():
            assert pairs[b] == a and by_id[a]["성별"] != by_id[b]["성별"]
            assert dict(season["선호"][a])[b] >= MATCH_MIN
    # 7) 48시간 여행은 조회 방향과 무관하게 같은 결과, 지원금 분할 합계 = 총액
    for e in season["쌍"].values():
        if "여행" in e:
            m, w = by_id[e["남"]], by_id[e["여"]]
            assert run_trip(w, m, e["호감도"]) == e["여행"]
        if "지원금" in e:
            assert sum(a for _, a in e["지원금"]["분할"]) == e["지원금"]["총액"] > 0
    return results, season


# ------------------------------------------------------------------ 출력 (main에서만)
def _w(s):
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in str(s))


def _pad(s, n):
    s = str(s)
    return s + " " * max(0, n - _w(s))


def _who(p):
    return f"{p['번호']} {p['이름']} ({p['나이']}세, {p['거주_시']} {p['거주_구']})"


def print_one(me, r, emb_err):
    f = r["거르기"]
    print(f"\n■ {_who(me)} 님에게 추천")
    print(f"\n[1 거르기] 전체 {f['전체']}명 중 본인·같은 성별 {f['본인·같은성별']}명 제외 → 반대 성별 {f['대상']}명")
    print("   조건별로 걸린 인원 (한 사람이 여러 조건에 걸리면 각각 셉니다)")
    for rule in RULES:
        c = f["제외"][rule]
        print(f"   - {_pad(rule, 14)} {c['인원']:>2}명 (내 조건 {c['내 조건']} · 상대 조건 {c['상대 조건']})")
    print(f"   → 하나라도 걸린 {f['제외인원']}명 제외 → 남은 {len(f['통과'])}명")
    if not f["통과"]:
        print(f"\n{no_match_message(f)}\n2~4단계는 건너뜁니다.")
        return

    n = len(f["통과"])
    if emb_err:
        print(f"\n[2 임베딩] 모델이 없어 건너뜁니다 → 통과자 {n}명 전원을 3단계로 넘깁니다.")
    else:
        print(f"\n[2 임베딩] {n}명 → 상위 {len(r['후보'])}명 (자기소개·관심사·주말·결혼·자녀 문장의 코사인 유사도)")
        for i, (p, sim) in enumerate(r["후보"], 1):
            print(f"   {i:>2}. {_pad(p['번호'] + ' ' + p['이름'], 14)} {sim:.3f}")

    print("\n[3 순위]")
    cols = [("이름", 14), ("임베딩순위", 10), ("규칙점수", 8), ("최종순위", 8), ("변동", 4)]
    print("   " + " | ".join(_pad(c, w) for c, w in cols))
    print("   " + "-+-".join("-" * w for _, w in cols))
    for row in r["순위"]:
        e = row["임베딩순위"]
        d = "-" if e is None else "=" if e == row["최종순위"] else \
            (f"▲{e - row['최종순위']}" if e > row["최종순위"] else f"▼{row['최종순위'] - e}")
        vals = [row["상대"]["번호"] + " " + row["상대"]["이름"], "-" if e is None else e,
                f"{row['총점']:g}", row["최종순위"], d]
        print("   " + " | ".join(_pad(v, w) for v, (_, w) in zip(vals, cols)))

    top = r["순위"][0]
    print(f"\n[4 이유] 1위: {_who(top['상대'])} - {top['총점']:g}/{sum(MAX.values())}점")
    for cat, mx in MAX.items():
        s = top["점수"][cat]
        print(f"   {_pad(cat, 10)} {s:>4g}/{mx:<3} {'■' * round(s / mx * 5)}")
    print(f"   → {r['이유']}")


def _nm(pid, by_id):
    return f"{pid} {by_id[pid]['이름']}"


def _ox(ok):
    return "○" if ok else "×"


def print_wildcard(wc):
    print("\n[5 의외의 궁합] 임베딩 후보에는 못 들었지만 규칙 점수가 높은 사람")
    if wc is None:
        print("   통과자 전원이 이미 3단계 후보에 들어가 따로 뽑을 사람이 없습니다.")
        return
    p = wc["상대"]
    print(f"   {_who(p)}: 임베딩 {wc['임베딩순위']}위라 후보 {K}명에서 빠졌지만 규칙 점수 {wc['총점']:g}점"
          f" (후보 {K}명 중 {wc['앞선인원']}명보다 높음)")


def print_my_season(me, season, by_id):
    pid = me["번호"]
    prefs, e = season["선호"][pid], season["쌍"].get(pid)
    print(f"\n[6 이번 시즌 {SEASON}] 호감도 = 궁합(항목 점수 × 내 중요항목 {WEIGHT_IMPORTANT}배) + 첫인상(±{FIRST_IMPRESSION})"
          f" · 내 중요항목: {me.get('중요항목') or '없음(균형형)'}")
    if not prefs:
        print("   거르기 통과자가 없어 이번 시즌에 참가하지 못했습니다.")
        return
    print("   내가 보는 호감도 상위 3명 (오른쪽 = 상대가 나를 보는 호감도)")
    for i, (q, s) in enumerate(prefs[:3], 1):
        fit, imp, _ = season_score(me, by_id[q])
        back = dict(season["선호"][q]).get(pid, 0)
        print(f"   {i}. {_pad(_nm(q, by_id), 14)} {s:>5.1f} (궁합 {fit:5.1f} · 첫인상 {imp:+5.1f})   상대→나 {back:5.1f}")
    m_pair, w_pair = season["매칭"]["남"].get(pid), season["매칭"]["여"].get(pid)
    show = lambda x: _nm(x, by_id) if x else "짝 없음"
    print(f"   안정 매칭: 남 제안 → {show(m_pair)} / 여 제안 → {show(w_pair)}  (시즌 결과는 {PROPOSER} 제안)")
    if e is None:
        print(f"   → 호감도 {MATCH_MIN}점 이상인 상대와 짝이 맺어지지 않아 이번 시즌은 혼자입니다.")
        return
    mate = e["여"] if e["남"] == pid else e["남"]
    print("   쌍방 확인: " + "  ".join(f"{_ox(ok)} {k}" for k, ok in e["확인"].items()))
    if "여행" not in e:
        print(f"   → {_nm(mate, by_id)} 님과 짝이 됐지만 쌍방 확인을 통과하지 못해 여행은 가지 않습니다.")
        return
    print(f"\n   [48시간 여행] {_nm(pid, by_id)} × {_nm(mate, by_id)}  시작 호감도 "
          f"{e['호감도'][pid]:.1f} / {e['호감도'][mate]:.1f}")
    label = {"같음": "잘 맞음", "한칸": "그럭저럭", "두칸": "부딪힘", "운": "운"}
    for i, ev in enumerate(e["여행"]["로그"], 1):
        d, now = ev["변화"], ev["호감도"]
        print(f"   {i}. {_pad(ev['이벤트'], 24)} {_pad(label[ev['결과']], 8)}"
              f" 나 {d[pid]:+5.1f} · 상대 {d[mate]:+5.1f}  → {now[pid]:5.1f} / {now[mate]:5.1f}")
    fin = e["여행"]["최종"]
    print(f"\n[7 최종 선택] 최종 호감도 {fin[pid]:.1f} / {fin[mate]:.1f} (기준 {COUPLE_MIN})")
    if not e["여행"]["커플"]:
        print("   → 한쪽 이상이 기준에 못 미쳐 커플이 되지 않았습니다.")
        return
    s = e["지원금"]
    plan = " · ".join(f"{mo}개월 {amt:,}P" for mo, amt in s["분할"])
    print(f"   → 커플 성사! 데이트 바우처 {s['총액']:,}P (평균 {s['평균']}) 분할 지급: {plan}")


def print_season(people, season):
    by_id = {p["번호"]: p for p in people}
    nm = lambda x: _nm(x, by_id)
    ar = season["화살표"]
    print(f"\n[시즌 {SEASON}] 호감도 = 궁합(8개 항목 점수 × 본인 중요항목 {WEIGHT_IMPORTANT}배) + 첫인상(±{FIRST_IMPRESSION})")

    print("\n① 엇갈린 화살표 (각자 호감도 1위 기준)")
    print(f"   쌍방 {len(ar['쌍방'])}쌍: " + ", ".join(f"{a}↔{b}" for a, b in ar["쌍방"]))
    print(f"   짝사랑 {len(ar['짝사랑'])}건: " + ", ".join(f"{a}→{b}" for a, b in ar["짝사랑"]))
    print("   인기 집중: " + ", ".join(f"{nm(x)} {n}표" for x, n in ar["인기"][:3]))
    for t in ar["삼각관계"]:
        print(f"   삼각관계: {nm(t['중심'])} 님을 두고 {', '.join(t['경쟁'] + [t['선택']])} "
              f"→ {nm(t['중심'])} 님의 선택은 {t['선택']}")

    both, gender = season["매칭"], {p["번호"]: p["성별"] for p in people}
    count = {g: sum(1 for pid in both[g] if gender[pid] == "남") for g in both}
    print("\n② 안정 매칭 (서로 지금 짝보다 상대를 더 원하는 쌍이 없는 조합)")
    print(f"   남 제안 {count['남']}쌍 · 여 제안 {count['여']}쌍 · 제안 쪽에 따라 짝이 달라진 사람 "
          f"{len(season['달라진'])}명" + (f": {', '.join(season['달라진'])}" if season["달라진"] else ""))
    print(f"   시즌 결과는 '{PROPOSER}' 제안 기준입니다.")

    pairs = sorted({id(e): e for e in season["쌍"].values()}.values(), key=lambda e: e["남"])
    print(f"\n③ 쌍방 확인 → 48시간 여행 자격 (세 조건 모두: 안정 매칭 짝 · 서로 상위 {MUTUAL_TOP}위 · 양쪽 호감도 {MUTUAL_MIN}+)")
    for e in pairs:
        m, w = e["남"], e["여"]
        marks = " ".join(_ox(ok) for ok in e["확인"].values())
        print(f"   {_pad(nm(m), 12)} × {_pad(nm(w), 14)} 호감도 {e['호감도'][m]:5.1f} / {e['호감도'][w]:5.1f}"
              f"   {marks}   {'→ 여행' if '여행' in e else ''}")

    trips = [e for e in pairs if "여행" in e]
    print(f"\n④ 48시간 여행 결과 ({len(trips)}쌍, 커플 기준: 양쪽 최종 호감도 {COUPLE_MIN}+)")
    for e in trips:
        m, w, t = e["남"], e["여"], e["여행"]
        print(f"   {_pad(nm(m), 12)} × {_pad(nm(w), 14)} {e['호감도'][m]:5.1f}/{e['호감도'][w]:5.1f}"
              f" → {t['최종'][m]:5.1f}/{t['최종'][w]:5.1f}   {'커플 성사' if t['커플'] else '엇갈림'}")

    couples = [e for e in trips if "지원금" in e]
    total = sum(e["지원금"]["총액"] for e in couples)
    print(f"\n⑤ 커플 {len(couples)}쌍 · 데이트 바우처 총 {total:,}P (현금 아님, 1·3·6개월 유지 시 분할 지급)")
    for e in couples:
        s = e["지원금"]
        plan = " · ".join(f"{mo}개월 {amt:,}" for mo, amt in s["분할"])
        print(f"   {_pad(nm(e['남']), 12)} × {_pad(nm(e['여']), 14)} 평균 {s['평균']:5.1f} → {s['총액']:,}P ({plan})")


def print_all(people, results):
    print(f"\n[all] {len(people)}명 전원의 1위")
    for p in people:
        r = results[p["번호"]]
        head = _pad(f"{p['번호']} {p['이름']}", 14)
        if not r["순위"]:
            print(f"   {head} → {NO_MATCH} (가장 많이 거른 조건: {worst_rule(r['거르기'])})")
        else:
            t = r["순위"][0]
            print(f"   {head} → {_pad(t['상대']['번호'] + ' ' + t['상대']['이름'], 14)} "
                  f"{t['총점']:>5g}점  (통과 {len(r['거르기']['통과']):>2}명)")


def main():
    try:
        people = load_people()
    except (OSError, ValueError) as e:
        print(f"프로필 CSV를 읽지 못했습니다: {e}")
        sys.exit(1)
    by_id = {p["번호"]: p for p in people}
    arg = (sys.argv[1] if len(sys.argv) > 1
           else input("번호(M01~M35, W01~W35) 또는 all / season / check: ")).strip().upper()
    if arg == "EXPORT":  # 임베딩 모델 없이도 되도록 맨 앞에서 처리
        out = HERE / "docs" / "profiles.json"
        out.write_text(json.dumps(export_web(people), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{out.relative_to(HERE)}에 {len(people)}명과 점수표를 내보냈습니다.")
        return
    if arg not in ("ALL", "SEASON", "CHECK", "ASK") and arg not in by_id:
        print(f"'{arg}' 번호가 없습니다. 예: M07, W12, all, season, check")
        sys.exit(1)

    vecs, emb_err, fresh = load_embeddings(people)
    if emb_err:
        print(f"(임베딩 모델을 불러오지 못했습니다: {emb_err} → 거르기 통과자 전원을 규칙 점수로만 정렬합니다)")
    elif fresh:
        print(f"(임베딩 {fresh}명 새로 계산 → {EMB_FILE.name}에 저장)")

    results, season = self_check(people, vecs)
    print("(자체 점검 통과: 본인·같은 성별 제외 / 흡연 불가 / 통과자 0명 안내 / 순위 재현성)")

    if arg == "ALL":
        print_all(people, results)
    elif arg == "SEASON":
        print_season(people, season)
    elif arg == "CHECK":
        print("(v2 점검 통과: 중요항목 없으면 호감도 = 규칙 점수 / 두 방향 안정 매칭 / 여행 재현성 / 지원금 분할 합계)")
        bad = visual_check(people, results, vecs)
        if bad:
            print("시각화(M06 × W22) 기준값이 바뀌었습니다:\n   - " + "\n   - ".join(bad))
            sys.exit(1)
        note = "" if vecs is not None else " (임베딩 유사도는 모델이 없어 확인하지 못함)"
        print(f"시각화(M06 × W22) 기준값 일치: 프로필 원본 · 통과 인원 · 1위 · 49점 · 거르기 · 유사도{note}")
        ask_check(people, results, season, vecs)
        print(f"(질문 검색 점검 통과: {len(people)}명 × 질문 {len(ASK_QUESTIONS)}개 / 1위 이름·총점 = 3단계 결과 / 데이트 제안 관심사 전부)")
    elif arg == "ASK":
        out = HERE / "docs" / "ask.json"
        with open(out, "w", encoding="utf-8", newline="\n") as fh:  # LF 유지 (write_text 는 Windows 에서 CRLF)
            json.dump(ask_check(people, results, season, vecs), fh, ensure_ascii=False, indent=1)
        print(f"{out.relative_to(HERE)}에 {len(people)}명 × 질문 {len(ASK_QUESTIONS)}개의 답을 내보냈습니다."
              + (" (임베딩 없이 계산됨: 모델을 불러온 뒤 다시 실행하세요)" if vecs is None else ""))
    else:
        print_one(by_id[arg], results[arg], emb_err)
        if results[arg]["순위"]:
            print_wildcard(wildcard(by_id[arg], results[arg], vecs))
        print_my_season(by_id[arg], season, by_id)


if __name__ == "__main__":
    main()
