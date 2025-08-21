import base64

with open('static/images/damage_outline.png', 'rb') as img_file:
    base64_string = base64.b64encode(img_file.read()).decode('utf-8')
    print(f"data:image/png;base64,{base64_string}")