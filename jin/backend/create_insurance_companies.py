#!/usr/bin/env python
"""
보험사 데이터 생성 스크립트
"""

import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'insurance_project.settings')
django.setup()

from insurance.models import InsuranceCompany

def create_insurance_companies():
    """보험사 데이터 생성"""
    
    # 보험사 목록
    companies = [
        "삼성화재",
        "현대해상",
        "KB손해보험",
        "메리츠화재",
        "DB손해보험",
        "롯데손해보험",
        "하나손해보험",
        "흥국화재",
        "AXA손해보험",
        "MG손해보험",
        "캐롯손해보험",
        "한화손해보험",
    ]
    
    created_count = 0
    existing_count = 0
    
    for company_name in companies:
        try:
            # 기존에 있는지 확인
            company, created = InsuranceCompany.objects.get_or_create(
                name=company_name,
                defaults={
                    'code': company_name.replace('손해보험', '').replace('화재', '').replace('해상', ''),
                    'description': f'{company_name} 자동차보험 상품',
                    'status': 'active',
                    'phone': '02-0000-0000',
                    'email': f'info@{company_name.lower().replace("손해보험", "").replace("화재", "").replace("해상", "")}.com',
                    'website': f'https://www.{company_name.lower().replace("손해보험", "").replace("화재", "").replace("해상", "")}.com',
                    'address': f'{company_name} 본사',
                    'city': '서울',
                    'state': '서울특별시',
                    'zip_code': '00000',
                    'is_active': True
                }
            )
            
            if created:
                print(f"✅ 생성됨: {company_name}")
                created_count += 1
            else:
                print(f"⏭️  이미 존재: {company_name}")
                existing_count += 1
                
        except Exception as e:
            print(f"❌ 오류 ({company_name}): {e}")
    
    print(f"\n📊 결과:")
    print(f"   새로 생성: {created_count}개")
    print(f"   기존 존재: {existing_count}개")
    print(f"   총 보험사: {created_count + existing_count}개")

if __name__ == "__main__":
    print("🏢 보험사 데이터 생성 시작...")
    create_insurance_companies()
    print("✅ 보험사 데이터 생성 완료!") 