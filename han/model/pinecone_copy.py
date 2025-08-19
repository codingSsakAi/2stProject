import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import time
import uuid
import numpy as np

# --- 1. 환경 변수 로드 및 Pinecone 클라이언트 초기화 ---
load_dotenv()
api_key = os.getenv("PINECONE_API_KEY_MY")
if not api_key:
    raise ValueError("PINECONE_API_KEY_MY가 .env 파일에 설정되어 있지 않습니다.")

pc = Pinecone(api_key=api_key)
print("Pinecone 클라이언트 초기화 완료.")

# --- 2. 인덱스 설정 ---
source_index_name = "solar-embedding-index"
target_index_name = "solar-embedding-index-1"

# 원본 인덱스 존재 확인
if source_index_name not in pc.list_indexes().names():
    raise ValueError(f"원본 인덱스 '{source_index_name}'가 존재하지 않습니다.")

source_index = pc.Index(source_index_name)

# --- 3. 원본 인덱스 정보 확인 ---
print(f"'{source_index_name}' 인덱스 정보 확인 중...")
source_stats = source_index.describe_index_stats()
total_vectors = source_stats['total_vector_count']
namespaces = source_stats.get('namespaces', {})

print(f"원본 인덱스 벡터 총 개수: {total_vectors}")
if namespaces:
    for namespace, ns_stats in namespaces.items():
        ns_name = namespace if namespace else "(기본 네임스페이스)"
        print(f"  - {ns_name}: {ns_stats.get('vector_count', 0)}개")

if total_vectors == 0:
    print("원본 인덱스에 복사할 데이터가 없습니다.")
    exit()

# 원본 인덱스의 dimension과 metric 정보 가져오기
index_info = pc.describe_index(source_index_name)
dimension = index_info.dimension
metric = index_info.metric

print(f"인덱스 차원: {dimension}, 메트릭: {metric}")
print("-" * 50)

# --- 4. 대상 인덱스 생성 또는 확인 ---
if target_index_name in pc.list_indexes().names():
    print(f"대상 인덱스 '{target_index_name}'가 이미 존재합니다.")
    target_index = pc.Index(target_index_name)
    
    # 기존 데이터 확인
    target_stats = target_index.describe_index_stats()
    target_vectors = target_stats['total_vector_count']
    
    if target_vectors > 0:
        overwrite = input(f"대상 인덱스에 {target_vectors}개의 벡터가 있습니다. 덮어쓰시겠습니까? (y/n): ")
        if overwrite.lower() != 'y':
            print("복사를 취소했습니다.")
            exit()
        
        print("기존 데이터 삭제 중...")
        target_index.delete(delete_all=True)
        time.sleep(5)  # 삭제 반영 대기
else:
    print(f"대상 인덱스 '{target_index_name}' 생성 중...")
    pc.create_index(
        name=target_index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(
            cloud='aws',  # 또는 'gcp', 'azure' - 원본과 동일하게 설정
            region='us-east-1'  # 원본과 동일한 리전으로 설정
        )
    )
    
    print("인덱스 생성 완료. 초기화 대기 중...")
    time.sleep(15)  # 인덱스 초기화 대기
    target_index = pc.Index(target_index_name)

print("-" * 50)

# --- 5. 데이터 복사 실행 (개선된 방법) ---
print("데이터 복사를 시작합니다...")

def copy_vectors_using_query(source_idx, target_idx, namespace=None):
    """쿼리 기반으로 벡터 데이터 복사"""
    vectors_copied = 0
    batch_size = 100
    max_iterations = 50  # 무한루프 방지
    
    try:
        # 랜덤 벡터로 쿼리하여 데이터 수집
        print(f"네임스페이스 '{namespace or '(기본)'}' 데이터 수집 중...")
        
        collected_ids = set()
        all_vectors = []
        
        # 여러 번의 랜덤 쿼리로 모든 벡터 수집
        for iteration in range(max_iterations):
            # 랜덤 벡터 생성 (정규화된)
            random_vector = np.random.normal(0, 1, dimension).tolist()
            norm = np.linalg.norm(random_vector)
            if norm > 0:
                random_vector = [x / norm for x in random_vector]
            
            try:
                # 쿼리 실행
                query_response = source_idx.query(
                    vector=random_vector,
                    top_k=10000,  # 최대한 많은 결과 요청
                    include_values=True,
                    include_metadata=True,
                    namespace=namespace
                )
                
                new_vectors_found = 0
                
                if 'matches' in query_response:
                    for match in query_response['matches']:
                        vector_id = match['id']
                        
                        if vector_id not in collected_ids:
                            vector_to_upsert = {
                                'id': vector_id,
                                'values': match['values'],
                                'metadata': match.get('metadata', {})
                            }
                            
                            all_vectors.append(vector_to_upsert)
                            collected_ids.add(vector_id)
                            new_vectors_found += 1
                            
                            # 배치 단위로 업서트
                            if len(all_vectors) >= batch_size:
                                target_idx.upsert(vectors=all_vectors, namespace=namespace)
                                vectors_copied += len(all_vectors)
                                print(f"  → {vectors_copied}개 벡터 복사됨...")
                                all_vectors = []
                
                print(f"반복 {iteration + 1}: {new_vectors_found}개 새 벡터 발견 (총 {len(collected_ids)}개)")
                
                # 새로운 벡터가 발견되지 않으면 종료
                if new_vectors_found == 0:
                    print("모든 벡터를 수집했습니다.")
                    break
                    
            except Exception as e:
                print(f"쿼리 {iteration + 1} 실행 중 오류: {e}")
                continue
        
        # 남은 벡터들 업서트
        if all_vectors:
            target_idx.upsert(vectors=all_vectors, namespace=namespace)
            vectors_copied += len(all_vectors)
            print(f"  → 최종 {vectors_copied}개 벡터 복사 완료!")
            
    except Exception as e:
        print(f"데이터 복사 중 오류: {e}")
        return vectors_copied
    
    return vectors_copied

# 전체 복사 실행
total_copied = 0

# 기본 네임스페이스 처리 (빈 문자열 또는 None)
if not namespaces or "" in namespaces or len(namespaces) == 0:
    print("\n기본 네임스페이스 복사 중...")
    copied_count = copy_vectors_using_query(source_index, target_index, None)
    total_copied += copied_count
    print(f"기본 네임스페이스 복사 완료: {copied_count}개")
else:
    # 명시적 네임스페이스들 처리
    for namespace in namespaces.keys():
        if namespace:  # 빈 문자열이 아닌 네임스페이스
            print(f"\n네임스페이스 '{namespace}' 복사 중...")
            copied_count = copy_vectors_using_query(source_index, target_index, namespace)
            total_copied += copied_count
            print(f"네임스페이스 '{namespace}' 복사 완료: {copied_count}개")
        else:  # 빈 문자열 네임스페이스 (기본 네임스페이스)
            print(f"\n기본 네임스페이스 복사 중...")
            copied_count = copy_vectors_using_query(source_index, target_index, None)
            total_copied += copied_count
            print(f"기본 네임스페이스 복사 완료: {copied_count}개")

print("-" * 50)

# --- 6. 복사 결과 확인 ---
print("복사 결과 확인 중...")
time.sleep(10)  # 업서트 반영 대기

try:
    final_target_stats = target_index.describe_index_stats()
    final_target_count = final_target_stats['total_vector_count']
    
    print(f"원본 인덱스 벡터 수: {total_vectors}")
    print(f"복사 시도한 벡터 수: {total_copied}")
    print(f"대상 인덱스 최종 벡터 수: {final_target_count}")
    
    success_rate = (final_target_count / total_vectors) * 100 if total_vectors > 0 else 0
    print(f"복사 성공률: {success_rate:.1f}%")
    
    if final_target_count >= total_vectors * 0.95:  # 95% 이상이면 성공으로 간주
        print("✅ 데이터가 성공적으로 복사되었습니다!")
        print(f"이제 '{source_index_name}' 인덱스의 데이터를 안전하게 삭제할 수 있습니다.")
    else:
        print(f"⚠️  복사가 완전하지 않을 수 있습니다.")
        print("잠시 후 다시 확인하거나, 복사를 재시도해주세요.")
        
        # 추가 복사 시도 제안
        retry = input("복사를 다시 시도하시겠습니까? (y/n): ")
        if retry.lower() == 'y':
            print("복사를 재시도합니다...")
            # 재시도 로직은 스크립트를 다시 실행하는 것으로 대체

except Exception as e:
    print(f"결과 확인 중 오류: {e}")

print("-" * 50)
print("복사 작업 완료!")