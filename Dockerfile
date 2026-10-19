FROM python:3.11-slim

WORKDIR /app

# 취약점 보정 ⑩ (2026-10-19) — 포장 도구의 **딸린 사본**을 올린다.
#
# 굽고 재니 고위험 2건이 `jaraco-context` 5.3.0 과 `wheel` 0.45.1 에 있었다
# (done14 §288). 둘 다 우리가 적은 의존성이 아니다 — **setuptools 가 품고
# 들어오는 사본**이다. 그래서 requirements.txt 로는 못 고치고 포장 도구
# 자체를 올려야 한다(`authority` 에 같은 줄이 10-19 에 들어갔다 · §286).
# 자리는 **requirements 설치보다 먼저** 다 — `authority` 와 같은 순서다(§286).
# 위 레이어에서 **덮어쓰면** 걷힌다(§264 실측: 파이썬 꾸러미는 **교체**가 통한다 —
# Go 바이너리 **삭제**가 안 통하는 것과 다르다). 그래서 앞뒤 어느 쪽에 둬도
# 벤더 사본은 새 판으로 바뀐다. 앞에 두는 것은 **requirements 가 setuptools 를
# 고정하지 않기** 때문이고, 고정하게 되면 이 줄을 뒤로 옮겨야 한다.
# ⚠ `wheel` 은 두 군데에 있다 — setuptools 가 품은 사본(0.45.1 · 결함 있음)과
#   따로 깔린 것(0.46.3 · 결함 없음). **센 것은 품은 사본**이다.
RUN pip install --no-cache-dir --upgrade 'setuptools>=84.0.0'

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY . .

EXPOSE 8404

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8404"]
