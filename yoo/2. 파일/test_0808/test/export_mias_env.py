
import subprocess

# 출력 파일 이름
output_file = "mias_environment_packages.txt"

# conda list 명령 실행
result = subprocess.run(["conda", "list"], capture_output=True, text=True, shell=True)

# 결과를 파일에 저장
with open(output_file, "w", encoding="utf-8") as f:
    f.write(result.stdout)

print(f"패키지 목록이 '{output_file}' 파일로 저장되었습니다.")
