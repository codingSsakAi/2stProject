from django import forms

class AccidentForm(forms.Form):
    accident_date = forms.DateTimeField(
        label="사고 일시",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    location = forms.CharField(label="사고 장소")

    # A 차량
    a_name = forms.CharField(label="A차량 성명")
    a_phone = forms.CharField(label="A차량 전화번호")
    a_id = forms.CharField(label="A차량 주민번호")
    a_address = forms.CharField(label="A차량 주소")
    a_passengers = forms.CharField(label="A차량 탑승인원")
    a_damage = forms.CharField(label="A차량 파손 및 특이사항", widget=forms.Textarea)

    # B 차량
    b_name = forms.CharField(label="B차량 성명")
    b_phone = forms.CharField(label="B차량 전화번호")
    b_id = forms.CharField(label="B차량 주민번호")
    b_address = forms.CharField(label="B차량 주소")
    b_passengers = forms.CharField(label="B차량 탑승인원")
    b_damage = forms.CharField(label="B차량 파손 및 특이사항", widget=forms.Textarea)

    # 사고 내용
    description = forms.CharField(label="사고 개요", widget=forms.Textarea)

    # 체크 항목
    weather = forms.ChoiceField(
        choices=[('맑음','맑음'), ('흐림','흐림'), ('비','비'), ('눈','눈'), ('안개','안개')],
        label="사고 당시 날씨"
    )
    time_period = forms.ChoiceField(
        choices=[('오전','오전'), ('오후','오후')],
        label="사고 시점"
    )
