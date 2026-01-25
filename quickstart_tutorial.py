"""
MindsDB Quickstart Tutorial
https://docs.mindsdb.com/quickstart-tutorial

이 스크립트는 MindsDB 퀵스타트 튜토리얼의 3단계를 따라합니다:
1. Connect - 데이터 소스 연결
2. Unify - Knowledge Base로 데이터 통합
3. Respond - AI 에이전트로 질문 응답
"""

import mindsdb_sdk
import time
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API 키 (.env에서 로드)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def connect_to_mindsdb():
    """MindsDB 서버에 연결"""
    print("=" * 60)
    print("MindsDB 서버에 연결 중...")
    print("=" * 60)
    
    server = mindsdb_sdk.connect('http://127.0.0.1:47334')
    print("✅ MindsDB 서버에 성공적으로 연결되었습니다!")
    return server


def step1_connect(server):
    """
    Step 1: Connect - 데이터 소스 연결
    MySQL 데모 데이터베이스와 웹 크롤러 연결
    """
    print("\n" + "=" * 60)
    print("📌 Step 1: Connect - 데이터 소스 연결")
    print("=" * 60)
    
    # 1-1. MySQL 데모 데이터베이스 연결
    print("\n🔗 MySQL 데모 데이터베이스 연결 중...")
    
    try:
        # 기존 연결이 있으면 삭제
        try:
            server.databases.drop('mysql_demo_db')
            print("  - 기존 mysql_demo_db 연결 삭제")
        except:
            pass
        
        query = """
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
        server.query(query)
        print("✅ MySQL 데모 데이터베이스가 연결되었습니다!")
        
        # 데이터 샘플 조회
        print("\n📊 home_rentals 테이블 샘플 데이터:")
        result = server.query("""
            SELECT *
            FROM mysql_demo_db.home_rentals
            LIMIT 5
        """)
        print(result.fetch())
        
    except Exception as e:
        print(f"⚠️ MySQL 연결 오류: {e}")
    
    # 1-2. 웹 크롤러 연결 (Unstructured Data)
    print("\n🔗 웹 크롤러 연결 중...")
    
    try:
        # 기존 연결이 있으면 삭제
        try:
            server.databases.drop('my_web')
            print("  - 기존 my_web 연결 삭제")
        except:
            pass
        
        query = """
        CREATE DATABASE my_web 
        WITH ENGINE = 'web'
        """
        server.query(query)
        print("✅ 웹 크롤러가 연결되었습니다!")
        
        # 웹 페이지 크롤링 테스트
        print("\n🌐 MindsDB 문서 페이지 크롤링 중...")
        result = server.query("""
            SELECT url, LEFT(text_content, 200) as preview
            FROM my_web.crawler
            WHERE url = 'https://docs.mindsdb.com/'
            LIMIT 1
        """)
        df = result.fetch()
        print(df)
        
        # View 생성
        print("\n📄 mindsdb_docs 뷰 생성 중...")
        try:
            server.query("DROP VIEW IF EXISTS mindsdb.mindsdb_docs")
        except:
            pass
            
        server.query("""
            CREATE VIEW mindsdb.mindsdb_docs (
                SELECT url, text_content
                FROM my_web.crawler
                WHERE url = 'https://docs.mindsdb.com/'
            )
        """)
        print("✅ mindsdb_docs 뷰가 생성되었습니다!")
        
    except Exception as e:
        print(f"⚠️ 웹 크롤러 연결 오류: {e}")
    
    print("\n✅ Step 1 완료: 데이터 소스 연결 완료!")


def step2_unify(server):
    """
    Step 2: Unify - Knowledge Base 생성 및 데이터 통합
    """
    print("\n" + "=" * 60)
    print("📌 Step 2: Unify - Knowledge Base 생성")
    print("=" * 60)
    
    # Knowledge Base 생성
    print("\n🧠 Knowledge Base 생성 중...")
    
    try:
        # 기존 KB가 있으면 삭제
        try:
            server.query("DROP KNOWLEDGE_BASE IF EXISTS my_kb")
            print("  - 기존 my_kb 삭제")
        except:
            pass
        
        kb_query = f"""
        CREATE KNOWLEDGE_BASE my_kb
        USING
            embedding_model = {{
                "provider": "openai",
                "model_name" : "text-embedding-3-large",
                "api_key": "{OPENAI_API_KEY}"
            }},
            reranking_model = {{
                "provider": "openai",
                "model_name": "gpt-4o",
                "api_key": "{OPENAI_API_KEY}"
            }},
            content_columns = ['content']
        """
        server.query(kb_query)
        print("✅ Knowledge Base 'my_kb'가 생성되었습니다!")
        
    except Exception as e:
        print(f"⚠️ Knowledge Base 생성 오류: {e}")
        return
    
    # home_rentals 데이터 삽입
    print("\n📥 home_rentals 데이터를 Knowledge Base에 삽입 중...")
    try:
        insert_query = """
        INSERT INTO my_kb
            SELECT
                'number_of_rooms: ' || number_of_rooms || ', ' ||
                'number_of_bathrooms: ' || number_of_bathrooms || ', ' ||
                'sqft: ' || sqft || ', ' ||
                'location: ' || location || ', ' ||
                'days_on_market: ' || days_on_market || ', ' ||
                'neighborhood: ' || neighborhood || ', ' ||
                'rental_price: ' || rental_price
                    AS content
            FROM mysql_demo_db.home_rentals
            LIMIT 100
        """
        server.query(insert_query)
        print("✅ home_rentals 데이터가 삽입되었습니다!")
    except Exception as e:
        print(f"⚠️ 데이터 삽입 오류: {e}")
    
    # 웹 문서 데이터 삽입
    print("\n📥 웹 문서 데이터를 Knowledge Base에 삽입 중...")
    try:
        insert_docs_query = """
        INSERT INTO my_kb
            SELECT text_content AS content
            FROM mindsdb.mindsdb_docs
        """
        server.query(insert_docs_query)
        print("✅ 웹 문서 데이터가 삽입되었습니다!")
    except Exception as e:
        print(f"⚠️ 문서 삽입 오류: {e}")
    
    # Knowledge Base 검색 테스트
    print("\n🔍 Knowledge Base 검색 테스트:")
    
    try:
        print("\n  질문 1: 'what is MindsDB'")
        result = server.query("""
            SELECT *
            FROM my_kb
            WHERE content = 'what is MindsDB'
            LIMIT 3
        """)
        print(result.fetch())
        
        print("\n  질문 2: 'rental price lower than 2000'")
        result = server.query("""
            SELECT *
            FROM my_kb
            WHERE content = 'rental price lower than 2000'
            LIMIT 3
        """)
        print(result.fetch())
        
    except Exception as e:
        print(f"⚠️ 검색 오류: {e}")
    
    print("\n✅ Step 2 완료: Knowledge Base 생성 및 데이터 통합 완료!")


def step3_respond(server):
    """
    Step 3: Respond - AI 에이전트 생성 및 질문 응답
    """
    print("\n" + "=" * 60)
    print("📌 Step 3: Respond - AI 에이전트 생성")
    print("=" * 60)
    
    # 에이전트 생성
    print("\n🤖 AI 에이전트 생성 중...")
    
    try:
        # 기존 에이전트가 있으면 삭제
        try:
            server.query("DROP AGENT IF EXISTS my_agent")
            print("  - 기존 my_agent 삭제")
        except:
            pass
        
        agent_query = f"""
        CREATE AGENT my_agent
        USING
            model = {{
                "provider": "openai",
                "model_name" : "gpt-4o",
                "api_key": "{OPENAI_API_KEY}"
            }},
            data = {{
                 "knowledge_bases": ["mindsdb.my_kb"],
                 "tables": ["mysql_demo_db.home_rentals"]
            }},
            prompt_template = 'mindsdb.my_kb stores data about mindsdb and home rentals,
                              mysql_demo_db.home_rentals stores data about home rentals'
        """
        server.query(agent_query)
        print("✅ AI 에이전트 'my_agent'가 생성되었습니다!")
        
    except Exception as e:
        print(f"⚠️ 에이전트 생성 오류: {e}")
        return
    
    # 에이전트에게 질문
    print("\n💬 AI 에이전트에게 질문:")
    
    questions = [
        "what is MindsDB?",
        "what are some rental properties with price under 2000?",
        "what neighborhoods have the best rental options?"
    ]
    
    for q in questions:
        print(f"\n  질문: '{q}'")
        try:
            result = server.query(f"""
                SELECT *
                FROM my_agent
                WHERE question = '{q}'
            """)
            df = result.fetch()
            print(f"  답변: {df.to_string()}")
        except Exception as e:
            print(f"  ⚠️ 응답 오류: {e}")
    
    print("\n✅ Step 3 완료: AI 에이전트 생성 및 질문 응답 완료!")


def main():
    """메인 실행 함수"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           MindsDB Quickstart Tutorial                        ║
    ║    https://docs.mindsdb.com/quickstart-tutorial              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # MindsDB 서버 연결
        server = connect_to_mindsdb()
        
        # Step 1: Connect
        step1_connect(server)
        
        # Step 2: Unify
        step2_unify(server)
        
        # Step 3: Respond
        step3_respond(server)
        
        print("\n" + "=" * 60)
        print("🎉 MindsDB Quickstart Tutorial 완료!")
        print("=" * 60)
        print("\n📝 다음 단계:")
        print("  - MindsDB GUI: http://127.0.0.1:47334")
        print("  - 더 많은 예제: https://docs.mindsdb.com/")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
