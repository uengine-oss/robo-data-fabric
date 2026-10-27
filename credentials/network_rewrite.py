"""원천 DB 접속값의 `localhost` 를 바꿔 준다 — 요청에만 쓰고 저장하지 않는다.

⚠ 사람이 적는 `localhost` 는 **자기 PC** 다. 그런데 원천에 실제로 붙는 쪽은
**중앙 DB 컨테이너**이고(FDW 외부 서버가 거기서 열린다), 거기서 `localhost` 는 그
컨테이너 자신이다. 바꾸지 않으면 "되는 주소를 적었는데 안 붙는다" 가 된다.

⚠ 이 함수가 돌려준 값은 **등록 요청에만** 들어간다. registry 에 저장되는 값은
`credentials/allowlist.py` 가 따로 좁힌다 — 비밀번호는 거기 없다.
"""
from typing import Any


def source_parameters(parameters: dict[str, Any], replacement_host: str) -> dict[str, Any]:
    result = dict(parameters)
    if result.get("host") in {"localhost", "127.0.0.1"} and replacement_host:
        result["host"] = replacement_host
    return result
