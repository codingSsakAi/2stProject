import os
from pinecone import Pinecone
from dotenv import load_dotenv
import time

# --- 1. 환경 변수 로드 및 Pinecone 클라이언트 초기화 ---
load_dotenv()
api_key = os.getenv("PINECONE_API_KEY_MY")
if not api_key:
    raise ValueError("PINECONE_API_KEY_MY가 .env 파일에 설정되어 있지 않습니다.")

pc = Pinecone(api_key=api_key)
print("Pinecone 클라이언트 초기화 완료.")

# --- 2. 인덱스 설정 ---
original_index_name = "solar-embedding-index"

# 인덱스 존재 확인
if original_index_name not in pc.list_indexes().names():
    raise ValueError(f"'{original_index_name}' 인덱스가 존재하지 않습니다.")

original_index = pc.Index(original_index_name)

# --- 3. 현재 데이터 상태 확인 ---
print(f"'{original_index_name}' 인덱스 현재 상태 확인 중...")
stats = original_index.describe_index_stats()
total_vectors = stats['total_vector_count']
namespaces = stats.get('namespaces', {})

print(f"현재 벡터 총 개수: {total_vectors}")
if namespaces:
    for namespace, ns_stats in namespaces.items():
        ns_name = namespace if namespace else "(기본 네임스페이스)"
        print(f"  - {ns_name}: {ns_stats.get('vector_count', 0)}개")

if total_vectors == 0:
    print("인덱스에 삭제할 데이터가 없습니다.")
    exit()

print("-" * 50)

# --- 4. 삭제 확인 ---
print("⚠️  주의: 이 작업은 되돌릴 수 없습니다!")
final_confirm = input(f"'{original_index_name}' 인덱스의 모든 데이터를 삭제하시겠습니까? (정확히 'yes' 입력): ")

if final_confirm != "yes":
    print("삭제를 취소했습니다.")
    exit()

print("-" * 50)

# --- 5. 데이터 삭제 실행 ---
print("데이터 삭제를 시작합니다...")

try:
    # 네임스페이스가 있는 경우 각각 삭제
    if namespaces:
        for namespace in namespaces.keys():
            try:
                if namespace:  # 네임스페이스가 있는 경우
                    print(f"네임스페이스 '{namespace}' 삭제 중...")
                    original_index.delete(delete_all=True, namespace=namespace)
                else:  # 기본 네임스페이스
                    print("기본 네임스페이스 삭제 중...")
                    original_index.delete(delete_all=True)
                
                print(f"네임스페이스 삭제 완료!")
                time.sleep(2)  # 삭제 처리 시간 대기
                
            except Exception as e:
                print(f"네임스페이스 삭제 중 오류: {e}")
    else:
        # 네임스페이스 정보가 없는 경우 전체 삭제
        print("모든 데이터 삭제 중...")
        original_index.delete(delete_all=True)
        print("삭제 완료!")

except Exception as e:
    print(f"삭제 중 오류 발생: {e}")
    exit()

print("-" * 50)

# --- 6. 삭제 결과 확인 ---
print("삭제 결과 확인 중...")
time.sleep(5)  # 삭제 반영 시간 대기

try:
    final_stats = original_index.describe_index_stats()
    final_vector_count = final_stats['total_vector_count']
    
    print(f"삭제 전 벡터 수: {total_vectors}")
    print(f"삭제 후 벡터 수: {final_vector_count}")
    
    if final_vector_count == 0:
        print("✅ 모든 데이터가 성공적으로 삭제되었습니다!")
        print(f"'{original_index_name}' 인덱스가 비워져서 새로운 데이터를 받을 준비가 되었습니다.")
    else:
        print(f"⚠️  {final_vector_count}개의 벡터가 아직 남아있습니다.")
        print("잠시 후 다시 확인해보거나, 수동으로 삭제를 재시도해주세요.")

except Exception as e:
    print(f"결과 확인 중 오류: {e}")

print("-" * 50)
print("작업 완료!")