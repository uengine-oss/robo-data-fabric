"""
MindsDB Quickstart Tutorial - HTTP API Version
https://docs.mindsdb.com/quickstart-tutorial
"""

import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:47334/api/sql/query"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def run_query(query, description=""):
    """Execute SQL query via MindsDB HTTP API"""
    if description:
        print(f"\n🔹 {description}")
    print(f"   Query: {query[:100]}..." if len(query) > 100 else f"   Query: {query}")
    
    try:
        response = requests.post(
            BASE_URL,
            headers={"Content-Type": "application/json"},
            json={"query": query},
            timeout=120
        )
        result = response.json()
        
        if result.get("type") == "error":
            print(f"   ❌ Error: {result.get('error_message', 'Unknown error')}")
            return None
        elif result.get("type") == "table":
            print(f"   ✅ Success! Rows: {len(result.get('data', []))}")
            return result
        else:
            print(f"   ✅ OK")
            return result
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None


def format_table(result):
    """Format table result for display"""
    if not result or result.get("type") != "table":
        return
    
    columns = result.get("column_names", [])
    data = result.get("data", [])
    
    if not data:
        print("   (No data)")
        return
    
    # Print header
    print("\n   " + " | ".join(str(c)[:20] for c in columns))
    print("   " + "-" * (22 * len(columns)))
    
    # Print rows (max 5)
    for row in data[:5]:
        print("   " + " | ".join(str(v)[:20] for v in row))
    
    if len(data) > 5:
        print(f"   ... and {len(data) - 5} more rows")


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           MindsDB Quickstart Tutorial                        ║
    ║    https://docs.mindsdb.com/quickstart-tutorial              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # ================================================================
    # Step 1: Connect - 데이터 소스 연결
    # ================================================================
    print("\n" + "=" * 60)
    print("📌 Step 1: Connect - 데이터 소스 연결")
    print("=" * 60)
    
    # 1-1. MySQL 데모 데이터베이스 연결
    run_query("DROP DATABASE IF EXISTS mysql_demo_db", "기존 MySQL 연결 삭제")
    
    mysql_query = """
    CREATE DATABASE mysql_demo_db
    WITH ENGINE = 'mysql',
    PARAMETERS = {
        "user": "user",
        "password": "MindsDBUser123!",
        "host": "samples.mindsdb.com",
        "port": "3306",
        "database": "public"
    }
    """
    run_query(mysql_query.strip(), "MySQL 데모 데이터베이스 연결")
    
    # MySQL 데이터 조회
    result = run_query(
        "SELECT * FROM mysql_demo_db.home_rentals LIMIT 5",
        "home_rentals 샘플 데이터 조회"
    )
    format_table(result)
    
    # 1-2. 웹 크롤러 연결
    run_query("DROP DATABASE IF EXISTS my_web", "기존 웹 크롤러 삭제")
    run_query("CREATE DATABASE my_web WITH ENGINE = 'web'", "웹 크롤러 연결")
    
    print("\n✅ Step 1 완료: 데이터 소스 연결 완료!")
    
    # ================================================================
    # Step 2: Unify - Knowledge Base 생성
    # ================================================================
    print("\n" + "=" * 60)
    print("📌 Step 2: Unify - Knowledge Base 생성")
    print("=" * 60)
    
    # Knowledge Base 생성
    run_query("DROP KNOWLEDGE_BASE IF EXISTS my_kb", "기존 Knowledge Base 삭제")
    
    kb_query = f"""
    CREATE KNOWLEDGE_BASE my_kb
    USING
        embedding_model = {{
            "provider": "openai",
            "model_name": "text-embedding-3-large",
            "api_key": "{OPENAI_API_KEY}"
        }},
        reranking_model = {{
            "provider": "openai",
            "model_name": "gpt-4o",
            "api_key": "{OPENAI_API_KEY}"
        }},
        content_columns = ['content']
    """
    run_query(kb_query.strip(), "Knowledge Base 생성")
    
    # 데이터 삽입
    insert_query = """
    INSERT INTO my_kb
        SELECT
            'Rental Property - rooms: ' || CAST(number_of_rooms AS VARCHAR) || 
            ', bathrooms: ' || CAST(number_of_bathrooms AS VARCHAR) || 
            ', sqft: ' || CAST(sqft AS VARCHAR) || 
            ', location: ' || location || 
            ', neighborhood: ' || neighborhood || 
            ', price: $' || CAST(rental_price AS VARCHAR)
                AS content
        FROM mysql_demo_db.home_rentals
        LIMIT 50
    """
    run_query(insert_query.strip(), "home_rentals 데이터 50개 삽입")
    
    print("\n   ⏳ 인덱싱 대기 중 (5초)...")
    time.sleep(5)
    
    # Knowledge Base 검색 테스트
    result = run_query(
        "SELECT * FROM my_kb WHERE content = 'rental under 2000' LIMIT 3",
        "Knowledge Base 검색 테스트"
    )
    format_table(result)
    
    print("\n✅ Step 2 완료: Knowledge Base 생성 완료!")
    
    # ================================================================
    # Step 3: Respond - AI 에이전트 생성
    # ================================================================
    print("\n" + "=" * 60)
    print("📌 Step 3: Respond - AI 에이전트 생성")
    print("=" * 60)
    
    # 기존 에이전트 삭제 시도 (오류 무시)
    run_query("DROP AGENT IF EXISTS my_agent", "기존 에이전트 삭제 시도")
    
    # 에이전트 생성
    agent_query = f"""
    CREATE AGENT my_agent
    USING
        model = {{
            "provider": "openai",
            "model_name": "gpt-4o",
            "api_key": "{OPENAI_API_KEY}"
        }},
        data = {{
            "knowledge_bases": ["mindsdb.my_kb"],
            "tables": ["mysql_demo_db.home_rentals"]
        }},
        prompt_template = 'You are a helpful real estate assistant. The knowledge base contains rental property listings with details like rooms, bathrooms, sqft, location, neighborhood, and rental price.'
    """
    run_query(agent_query.strip(), "AI 에이전트 생성")
    
    # 에이전트에게 질문
    print("\n💬 AI 에이전트에게 질문하기:")
    
    questions = [
        "What rental properties are available under $2000?",
        "Find me a 2 bedroom apartment in downtown",
        "What is the average rental price in berkeley_hills?"
    ]
    
    for q in questions:
        print(f"\n   ❓ Question: {q}")
        result = run_query(
            f"SELECT * FROM my_agent WHERE question = '{q}'",
            ""
        )
        if result and result.get("type") == "table" and result.get("data"):
            answer = result["data"][0][0] if result["data"][0] else "No answer"
            print(f"   💡 Answer: {str(answer)[:500]}...")
    
    print("\n✅ Step 3 완료: AI 에이전트 생성 완료!")
    
    # ================================================================
    # 완료
    # ================================================================
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║ 🎉 MindsDB Quickstart Tutorial 완료!                         ║
    ╠══════════════════════════════════════════════════════════════╣
    ║ 📌 다음 단계:                                                ║
    ║   - MindsDB GUI: http://127.0.0.1:47334                      ║
    ║   - 더 많은 예제: https://docs.mindsdb.com/                  ║
    ╚══════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
