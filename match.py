"""소개팅 매칭 로직 (콘솔).

1) 거르기(규칙) → 2) 후보 추리기(로컬 임베딩) → 3) 순위 다시 매기기(규칙 점수) → 4) 이유 설명
실행: python match.py        (번호 입력: M07, W12, all)
      python match.py M01    (인자로 바로 실행)
"""
import csv
import hashlib
import json
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


def load_people():
    """두 CSV를 읽어 앞뒤 공백을 지우고 값을 검증합니다 (학생이 CSV를 고쳐도 엉뚱하게 거르지 않도록)."""
    people = []
    for name in ("men.csv", "women.csv"):
        with open(HERE / name, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                p = {k: (v or "").strip() for k, v in row.items() if k}
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
    return results


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
    arg = (sys.argv[1] if len(sys.argv) > 1 else input("번호(M01~M35, W01~W35) 또는 all: ")).strip().upper()
    if arg != "ALL" and arg not in by_id:
        print(f"'{arg}' 번호가 없습니다. 예: M07, W12, all")
        sys.exit(1)

    vecs, emb_err, fresh = load_embeddings(people)
    if emb_err:
        print(f"(임베딩 모델을 불러오지 못했습니다: {emb_err} → 거르기 통과자 전원을 규칙 점수로만 정렬합니다)")
    elif fresh:
        print(f"(임베딩 {fresh}명 새로 계산 → {EMB_FILE.name}에 저장)")

    results = self_check(people, vecs)
    print("(자체 점검 통과: 본인·같은 성별 제외 / 흡연 불가 / 통과자 0명 안내 / 순위 재현성)")

    if arg == "ALL":
        print_all(people, results)
    else:
        print_one(by_id[arg], results[arg], emb_err)


if __name__ == "__main__":
    main()
