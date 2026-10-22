# ⚠ **베이스를 `python:3.11-slim` 에서 Ubuntu 24.04 로 옮겼다** (2026-10-22).
#
# `python:*-slim` 은 Debian trixie 위에 있고, trixie 의 `zlib` 에
# CVE-2026-85091 이 걸려 있는데 **데비안이 고친 판을 안 냈다**(trixie·sid 모두
# vulnerable, 버그 #1146895). 이 이미지에 남아 있던 마지막 1건이 그것이었다.
#
#     python:3.11-slim                        0C 3H   (zlib 포함)
#     ubuntu:24.04 + python3 + python3-venv   **0C 0H**
#
# ⚠ **파이썬이 3.11 → 3.12 가 된다**(noble 의 기본). 기동 시험으로 확인했다.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# ⚠ **venv 를 만든 뒤 `*-whl` 꾸러미를 걷어낸다**.
# `python3-venv` 가 끌고 오는 `python3-pip-whl`·`python3-setuptools-whl` 이
# `/usr/share/python-wheels/` 에 옛 판 휠을 남기고, 검사기는 그 **안까지** 읽는다.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv ca-certificates \
    && python3 -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && apt-get purge -y python3-pip-whl python3-setuptools-whl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /usr/share/python-wheels
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
# ⚠ **다 깔았으면 `pip` 자신을 걷어낸다** (2026-10-22 실측).
# pip 는 `pip/_vendor/` 에 `urllib3`·`msgpack`·`setuptools` 사본을 들고 다니고
# 검사기가 그것까지 센다. 이 컨테이너는 uvicorn 만 띄우므로 런타임에 pip 가
# 필요 없다 — 없는 것을 안 싣는 것이 가장 확실하다.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip wheel \
    && rm -rf /root/.cache

# 애플리케이션 복사
COPY . .

EXPOSE 8404

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8404"]
