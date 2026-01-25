"""
House Sales Forecasting Tutorial
https://docs.mindsdb.com/use-cases/predictive_analytics/house-sales-forecasting

분기별 주택 판매 예측을 위한 시계열 모델 생성 및 테스트
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:47334/api/sql/query"


def run_query(query, description="", timeout=300):
    """Execute SQL query via MindsDB HTTP API"""
    if description:
        print(f"\n🔹 {description}")
    
    # 쿼리 미리보기 (100자까지)
    preview = query.strip().replace('\n', ' ')[:100]
    print(f"   Query: {preview}..." if len(query.strip()) > 100 else f"   Query: {preview}")
    
    try:
        response = requests.post(
            BASE_URL,
            headers={"Content-Type": "application/json"},
            json={"query": query},
            timeout=timeout
        )
        result = response.json()
        
        if result.get("type") == "error":
            print(f"   ❌ Error: {result.get('error_message', 'Unknown error')[:200]}")
            return None
        elif result.get("type") == "table":
            rows = len(result.get('data', []))
            print(f"   ✅ Success! Rows: {rows}")
            return result
        else:
            print(f"   ✅ OK")
            return result
    except requests.exceptions.Timeout:
        print(f"   ⏳ Timeout - operation may still be running")
        return None
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None


def format_table(result, max_rows=10):
    """Format table result for display"""
    if not result or result.get("type") != "table":
        return
    
    columns = result.get("column_names", [])
    data = result.get("data", [])
    
    if not data:
        print("   (No data)")
        return
    
    # Calculate column widths
    widths = [max(len(str(c)), max(len(str(row[i])) for row in data[:max_rows])) for i, c in enumerate(columns)]
    widths = [min(w, 20) for w in widths]  # Cap at 20 chars
    
    # Print header
    header = " | ".join(str(c)[:w].ljust(w) for c, w in zip(columns, widths))
    print(f"\n   {header}")
    print("   " + "-" * len(header))
    
    # Print rows
    for row in data[:max_rows]:
        row_str = " | ".join(str(v)[:w].ljust(w) for v, w in zip(row, widths))
        print(f"   {row_str}")
    
    if len(data) > max_rows:
        print(f"   ... and {len(data) - max_rows} more rows")


def check_model_status(model_name, max_wait=600):
    """Check model status and wait for completion"""
    print(f"\n   ⏳ Waiting for model '{model_name}' to complete training...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        result = run_query(f"DESCRIBE {model_name}", "")
        
        if result and result.get("type") == "table" and result.get("data"):
            status = result["data"][0][1] if len(result["data"][0]) > 1 else "unknown"
            print(f"   Status: {status}")
            
            if status == "complete":
                return True
            elif status == "error":
                print(f"   ❌ Model training failed!")
                return False
        
        time.sleep(10)
    
    print(f"   ⏳ Timeout waiting for model completion")
    return False


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║       House Sales Forecasting with MindsDB                   ║
    ║  https://docs.mindsdb.com/use-cases/predictive_analytics/    ║
    ║               house-sales-forecasting                        ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # ================================================================
    # Step 1: Connect PostgreSQL Data Source
    # ================================================================
    print("\n" + "=" * 60)
    print("📌 Step 1: Connect a Data Source")
    print("=" * 60)
    
    # 기존 연결 삭제
    run_query("DROP DATABASE IF EXISTS example_db", "기존 PostgreSQL 연결 삭제")
    
    # PostgreSQL 연결 (로컬 PostgreSQL - robo-postgres)
    connect_query = """
    CREATE DATABASE example_db
    WITH ENGINE = 'postgres',
    PARAMETERS = {
        "user": "postgres",
        "password": "postgres123",
        "host": "host.docker.internal",
        "port": "5432",
        "database": "demo_data"
    }
    """
    run_query(connect_query.strip(), "PostgreSQL 데이터베이스 연결 (로컬)")
    
    # 데이터 미리보기
    result = run_query(
        "SELECT * FROM example_db.house_sales LIMIT 10",
        "house_sales 데이터 미리보기"
    )
    format_table(result)
    
    # 특정 그룹 데이터 확인
    result = run_query(
        """SELECT saledate, ma, type, bedrooms
           FROM example_db.house_sales
           WHERE type='house' AND bedrooms=3
           ORDER BY saledate""",
        "3 Bedroom House 시계열 데이터 확인"
    )
    format_table(result)
    
    print("\n✅ Step 1 완료: 데이터 소스 연결 완료!")
    
    # ================================================================
    # Step 2: Deploy and Train ML Model
    # ================================================================
    print("\n" + "=" * 60)
    print("📌 Step 2: Deploy and Train an ML Model")
    print("=" * 60)
    
    # 기존 모델 삭제
    run_query("DROP MODEL IF EXISTS mindsdb.house_sales_model", "기존 모델 삭제")
    
    # 시계열 예측 모델 생성
    # WINDOW 8 = 과거 2년 (8분기) 참조
    # HORIZON 4 = 미래 1년 (4분기) 예측
    model_query = """
    CREATE MODEL mindsdb.house_sales_model
    FROM example_db
    (SELECT * FROM house_sales)
    PREDICT ma
    ORDER BY saledate
    GROUP BY bedrooms, type
    WINDOW 8
    HORIZON 4
    """
    run_query(model_query.strip(), "시계열 예측 모델 생성 (WINDOW=8, HORIZON=4)")
    
    # 모델 상태 확인
    print("\n   ⏳ 모델 훈련 중... (몇 분 소요될 수 있습니다)")
    
    for i in range(30):  # 최대 5분 대기
        time.sleep(10)
        result = run_query("DESCRIBE house_sales_model", "")
        
        if result and result.get("type") == "table" and result.get("data"):
            # 데이터 구조에 따라 상태 추출
            data = result["data"][0]
            status = None
            
            # 상태 필드 찾기
            columns = result.get("column_names", [])
            if "STATUS" in columns:
                status_idx = columns.index("STATUS")
                status = data[status_idx]
            elif len(data) > 1:
                status = data[1]  # 두 번째 컬럼이 보통 상태
            
            print(f"   🔄 Model Status: {status}")
            
            if status and status.lower() == "complete":
                print("\n   ✅ 모델 훈련 완료!")
                break
            elif status and status.lower() == "error":
                print("\n   ❌ 모델 훈련 실패!")
                break
    else:
        print("\n   ⏳ 모델 훈련이 아직 진행 중입니다. 나중에 다시 확인하세요.")
    
    print("\n✅ Step 2 완료: ML 모델 생성!")
    
    # ================================================================
    # Step 3: Make Predictions
    # ================================================================
    print("\n" + "=" * 60)
    print("📌 Step 3: Make Predictions")
    print("=" * 60)
    
    # LATEST 키워드를 사용한 예측 - 2 bedroom house
    predict_query = """
    SELECT m.saledate as date, m.ma as forecast
    FROM mindsdb.house_sales_model as m
    JOIN example_db.house_sales as t
    WHERE t.saledate > LATEST
    AND t.type = 'house'
    AND t.bedrooms = 2
    LIMIT 4
    """
    result = run_query(predict_query.strip(), "2 Bedroom House 예측 (다음 4분기)")
    format_table(result)
    
    # 3 bedroom house 예측
    predict_query_3br = """
    SELECT m.saledate as date, m.ma as forecast
    FROM mindsdb.house_sales_model as m
    JOIN example_db.house_sales as t
    WHERE t.saledate > LATEST
    AND t.type = 'house'
    AND t.bedrooms = 3
    LIMIT 4
    """
    result = run_query(predict_query_3br.strip(), "3 Bedroom House 예측 (다음 4분기)")
    format_table(result)
    
    # Unit 1 bedroom 예측
    predict_query_unit = """
    SELECT m.saledate as date, m.ma as forecast
    FROM mindsdb.house_sales_model as m
    JOIN example_db.house_sales as t
    WHERE t.saledate > LATEST
    AND t.type = 'unit'
    AND t.bedrooms = 1
    LIMIT 4
    """
    result = run_query(predict_query_unit.strip(), "1 Bedroom Unit 예측 (다음 4분기)")
    format_table(result)
    
    print("\n✅ Step 3 완료: 예측 수행!")
    
    # ================================================================
    # Step 4: Automate with Jobs
    # ================================================================
    print("\n" + "=" * 60)
    print("📌 Step 4: Automate Continuous Improvement")
    print("=" * 60)
    
    # 기존 Job 삭제
    run_query("DROP JOB IF EXISTS retrain_model_and_save_predictions", "기존 Job 삭제")
    
    # 자동 재훈련 Job 생성
    job_query = """
    CREATE JOB retrain_model_and_save_predictions (
       RETRAIN mindsdb.house_sales_model
       FROM example_db
          (SELECT * FROM house_sales)
    )
    EVERY 2 days
    IF (SELECT * FROM example_db.house_sales
        WHERE created_at > LAST)
    """
    run_query(job_query.strip(), "자동 재훈련 Job 생성 (2일마다)")
    
    # Job 목록 확인
    result = run_query("SHOW JOBS", "등록된 Job 목록")
    format_table(result)
    
    print("\n✅ Step 4 완료: 자동화 설정!")
    
    # ================================================================
    # 완료
    # ================================================================
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║ 🎉 House Sales Forecasting Tutorial 완료!                    ║
    ╠══════════════════════════════════════════════════════════════╣
    ║ 📊 생성된 리소스:                                            ║
    ║   - Database: example_db (PostgreSQL)                        ║
    ║   - Model: house_sales_model (시계열 예측)                   ║
    ║   - Job: retrain_model_and_save_predictions (2일마다)        ║
    ╠══════════════════════════════════════════════════════════════╣
    ║ 📌 다음 단계:                                                ║
    ║   - MindsDB GUI: http://127.0.0.1:47334                      ║
    ║   - 다른 bedrooms/type으로 예측 시도                         ║
    ║   - 새 데이터 추가 후 Job 실행 확인                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
