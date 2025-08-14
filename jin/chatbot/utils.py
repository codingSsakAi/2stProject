import os
import re
from typing import List, Tuple, Optional
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import easyocr
import io
import tempfile

# PyMuPDF import (선택적)
try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("PyMuPDF가 설치되지 않았습니다. 이미지 추출 기능이 제한됩니다.")


class PDFProcessor:
    """PDF 처리 클래스 - 병합, 텍스트 추출, OCR 처리"""

    def __init__(self):
        # 한글 OCR 모델을 명시적으로 지정하고 GPU 사용
        self.reader = easyocr.Reader(
            ["ko", "en"],
            gpu=False,  # GPU 사용 시 True로 변경
            model_storage_directory="./easyocr_models",
            download_enabled=True,
        )

    def merge_pdfs(self, pdf_files: List[str], output_path: str) -> bool:
        """
        여러 PDF 파일을 하나로 병합

        Args:
            pdf_files: 병합할 PDF 파일 경로 리스트
            output_path: 출력 PDF 파일 경로

        Returns:
            bool: 성공 여부
        """
        try:
            writer = PdfWriter()

            for pdf_file in pdf_files:
                if os.path.exists(pdf_file):
                    reader = PdfReader(pdf_file)
                    for page in reader.pages:
                        writer.add_page(page)

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            return True
        except Exception as e:
            print(f"PDF 병합 오류: {e}")
            return False

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        PDF에서 텍스트 추출 (텍스트 기반 PDF)

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            str: 추출된 텍스트
        """
        try:
            text = ""

            # PyMuPDF를 우선 사용 (더 나은 한글 지원)
            if PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(pdf_path)
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        page_text = page.get_text()
                        if page_text:
                            text += f"\n--- 페이지 {page_num + 1} ---\n"
                            text += page_text
                            text += "\n"
                    doc.close()

                    # 한글이 포함되어 있는지 확인
                    if any(
                        "\u3131" <= char <= "\u318e" or "\uac00" <= char <= "\ud7a3"
                        for char in text
                    ):
                        return text.strip()
                    else:
                        print(
                            "PyMuPDF로 추출한 텍스트에 한글이 없습니다. PyPDF2로 재시도합니다."
                        )

                except Exception as e:
                    print(f"PyMuPDF 텍스트 추출 실패: {e}")

            # PyPDF2로 재시도
            reader = PdfReader(pdf_path)

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- 페이지 {page_num + 1} ---\n"
                    text += page_text
                    text += "\n"

            return text.strip()
        except Exception as e:
            print(f"텍스트 추출 오류: {e}")
            return ""

    def extract_images_from_pdf(self, pdf_path: str) -> List[Image.Image]:
        """
        PDF에서 이미지 추출

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            List[Image.Image]: 추출된 이미지 리스트
        """
        if not PYMUPDF_AVAILABLE:
            print("PyMuPDF가 설치되지 않아 이미지 추출을 건너뜁니다.")
            return []

        try:
            images = []
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    # PIL Image로 변환
                    image = Image.open(io.BytesIO(image_bytes))
                    images.append(image)

            doc.close()
            return images
        except Exception as e:
            print(f"이미지 추출 오류: {e}")
            return []

    def ocr_image(self, image: Image.Image) -> str:
        """
        이미지에서 텍스트 추출 (OCR)

        Args:
            image: PIL Image 객체

        Returns:
            str: OCR로 추출된 텍스트
        """
        try:
            # 이미지를 RGB로 변환
            if image.mode != "RGB":
                image = image.convert("RGB")

            # 이미지 전처리 (한글 인식 개선)
            # 이미지 크기 조정 (너무 작으면 확대)
            width, height = image.size
            if width < 800 or height < 600:
                scale_factor = max(800 / width, 600 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # OCR 실행 (한글 우선)
            results = self.reader.readtext(
                image,
                detail=1,
                paragraph=True,  # 문단 단위로 그룹화
                contrast_ths=0.1,  # 대비 임계값 낮춤
                adjust_contrast=0.5,  # 대비 조정
                text_threshold=0.6,  # 텍스트 임계값
                link_threshold=0.4,  # 링크 임계값
                low_text=0.3,  # 낮은 텍스트 임계값
                canvas_size=2560,  # 캔버스 크기
                mag_ratio=1.5,  # 확대 비율
            )

            # 결과 텍스트 추출
            text = ""
            for bbox, text_result, confidence in results:
                if confidence > 0.3:  # 신뢰도 30% 이상으로 낮춤 (한글 인식 개선)
                    text += text_result + " "

            return text.strip()
        except Exception as e:
            print(f"OCR 처리 오류: {e}")
            return ""

    def process_pdf_with_ocr(self, pdf_path: str) -> str:
        """
        PDF를 OCR로 처리하여 텍스트 추출

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            str: 추출된 텍스트
        """
        try:
            # 먼저 텍스트 기반으로 추출 시도
            text = self.extract_text_from_pdf(pdf_path)

            # 한글이 포함되어 있는지 확인
            has_korean = any(
                "\u3131" <= char <= "\u318e" or "\uac00" <= char <= "\ud7a3"
                for char in text
            )

            # 깨진 한글 문자가 있는지 확인 (일반적인 깨진 한글 패턴)
            has_broken_korean = any(char in "៳ᱲᲦᚪᲥᱤᲱᢌᶊὑ" for char in text)

            # 텍스트가 충분하지 않거나 한글이 없거나 깨진 한글이 있으면 OCR 사용
            if len(text.strip()) < 100 or not has_korean or has_broken_korean:
                print(
                    "텍스트 추출 결과가 부족하거나 한글이 없거나 깨진 한글이 있습니다. OCR을 사용합니다."
                )
                images = self.extract_images_from_pdf(pdf_path)
                ocr_text = ""

                for i, image in enumerate(images):
                    page_text = self.ocr_image(image)
                    if page_text:
                        ocr_text += f"\n--- 페이지 {i + 1} ---\n"
                        ocr_text += page_text
                        ocr_text += "\n"

                if ocr_text:
                    text = ocr_text
                    print(f"OCR로 {len(ocr_text)}자 텍스트를 추출했습니다.")
                else:
                    print("OCR로도 텍스트를 추출할 수 없습니다.")

            return text.strip()
        except Exception as e:
            print(f"PDF OCR 처리 오류: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """
        추출된 텍스트 정리

        Args:
            text: 원본 텍스트

        Returns:
            str: 정리된 텍스트
        """
        if not text:
            return ""

        # UTF-8 인코딩 확인 및 수정
        try:
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
        except:
            pass

        # 불필요한 공백 제거
        text = re.sub(r"\s+", " ", text)

        # 페이지 구분자 정리
        text = re.sub(r"--- 페이지 \d+ ---", "\n\n", text)

        # 특수 문자 정리 (한글 보존)
        text = re.sub(r'[^\w\s가-힣.,!?;:()\-()\[\]{}""' "\n\r]", "", text)

        # 깨진 한글 문자 제거 (더 포괄적으로)
        text = re.sub(
            r'[^\uAC00-\uD7A3\u3131-\u318E\u1100-\u11FF\uA960-\uA97F\uD7B0-\uD7FF\w\s.,!?;:()\-()\[\]{}""'
            "\n\r]",
            "",
            text,
        )

        # 추가적인 깨진 문자 패턴 제거
        broken_patterns = [
            r"[៳ᱲᲦᚪᲥᱤᲱᢌᶊὑ]+",  # 특정 깨진 한글 패턴
            r"[ᇋᖰᥥᶱᮍ]+",  # 추가 깨진 문자들
            r"[ᲦᚪᲥ]+",  # 더 많은 깨진 패턴
        ]

        for pattern in broken_patterns:
            text = re.sub(pattern, "", text)

        # 연속된 줄바꿈 정리
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 앞뒤 공백 제거
        text = text.strip()

        return text

    def split_text_into_chunks(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[str]:
        """
        텍스트를 청크로 분할 (RAG용)

        Args:
            text: 분할할 텍스트
            chunk_size: 청크 크기 (문자 수)
            overlap: 청크 간 겹치는 부분 (문자 수)

        Returns:
            List[str]: 분할된 텍스트 청크 리스트
        """
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # 문장 단위로 자르기
            if end < len(text):
                # 마침표, 느낌표, 물음표로 끝나는 지점 찾기
                for i in range(end, max(start, end - 100), -1):
                    if text[i] in ".!?":
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap
            if start >= len(text):
                break

        return chunks


def create_sample_pdf() -> str:
    """
    테스트용 샘플 PDF 생성

    Returns:
        str: 생성된 PDF 파일 경로
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        # 임시 파일 생성
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf_path = temp_file.name
        temp_file.close()

        # PDF 생성
        c = canvas.Canvas(pdf_path, pagesize=letter)

        # 샘플 보험 약관 내용
        content = """
        자동차보험 약관
        
        제1조 (보험의 목적)
        이 보험은 피보험자가 보험기간 중에 자동차를 운전하거나 승차하는 중에 발생한 사고로 인하여 
        제3자에게 입힌 손해를 보상하는 것을 목적으로 합니다.
        
        제2조 (보험금의 지급)
        보험사는 보험계약에 따라 보험금을 지급할 의무가 있습니다.
        
        제3조 (면책사유)
        다음의 경우에는 보험금을 지급하지 않습니다:
        1. 고의로 발생한 사고
        2. 음주운전으로 인한 사고
        3. 무면허 운전으로 인한 사고
        
        제4조 (보험료)
        보험료는 보험계약자가 보험기간 중에 분할하여 납입할 수 있습니다.
        """

        y = 750
        for line in content.split("\n"):
            if line.strip():
                c.drawString(50, y, line.strip())
                y -= 20

        c.save()
        return pdf_path

    except ImportError:
        print("reportlab이 설치되지 않았습니다. 테스트 PDF를 생성할 수 없습니다.")
        return ""
    except Exception as e:
        print(f"샘플 PDF 생성 오류: {e}")
        return ""
