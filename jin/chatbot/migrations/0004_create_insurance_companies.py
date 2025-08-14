from django.db import migrations


def create_insurance_companies(apps, schema_editor):
    """12개 보험사 데이터 생성"""
    InsuranceCompany = apps.get_model("chatbot", "InsuranceCompany")

    companies = [
        {"name": "메리츠화재", "code": "0101"},
        {"name": "한화손해보험", "code": "0102"},
        {"name": "롯데손해보험", "code": "0103"},
        {"name": "MG손해보험", "code": "0104"},
        {"name": "흥국화재", "code": "0105"},
        {"name": "삼성화재", "code": "0108"},
        {"name": "현대해상", "code": "0109"},
        {"name": "KB손해보험", "code": "0110"},
        {"name": "DB손해보험", "code": "0111"},
        {"name": "AXA다이렉트", "code": "0112"},
        {"name": "하나손해보험", "code": "0152"},
        {"name": "캐롯손해보험", "code": "0195"},
    ]

    for company_data in companies:
        InsuranceCompany.objects.get_or_create(
            code=company_data["code"],
            defaults={"name": company_data["name"], "is_active": True},
        )


def remove_insurance_companies(apps, schema_editor):
    """보험사 데이터 삭제"""
    InsuranceCompany = apps.get_model("chatbot", "InsuranceCompany")
    InsuranceCompany.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0003_insurancecompany_alter_chatsession_options_and_more"),
    ]

    operations = [
        migrations.RunPython(create_insurance_companies, remove_insurance_companies),
    ]
