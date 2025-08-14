import markdown
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown_to_html")
def markdown_to_html(text):
    """
    마크다운 텍스트를 HTML로 변환하는 필터
    """
    if not text:
        return ""

    # 기본 마크다운 설정
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.fenced_code",  # 코드 블록
            "markdown.extensions.tables",  # 테이블
            "markdown.extensions.nl2br",  # 줄바꿈
            "markdown.extensions.sane_lists",  # 리스트
        ]
    )

    # 마크다운을 HTML로 변환
    html = md.convert(text)

    # 추가적인 스타일링을 위한 클래스 추가
    html = re.sub(r"<h([1-6])>", r'<h\1 class="markdown-heading">', html)
    html = re.sub(r"<p>", r'<p class="markdown-paragraph">', html)
    html = re.sub(r"<ul>", r'<ul class="markdown-list">', html)
    html = re.sub(r"<ol>", r'<ol class="markdown-list">', html)
    html = re.sub(r"<li>", r'<li class="markdown-list-item">', html)
    html = re.sub(r"<strong>", r'<strong class="markdown-bold">', html)
    html = re.sub(r"<em>", r'<em class="markdown-italic">', html)
    html = re.sub(r"<code>", r'<code class="markdown-code">', html)

    return mark_safe(html)


@register.filter(name="format_chat_message")
def format_chat_message(text):
    """
    챗봇 메시지를 포맷팅하는 필터
    - 마크다운 변환
    - 줄바꿈 처리
    - 특수 문자 처리
    """
    if not text:
        return ""

    # 마크다운 변환
    formatted_text = markdown_to_html(text)

    return formatted_text


@register.filter(name="highlight_keywords")
def highlight_keywords(text, keywords=None):
    """
    키워드를 하이라이트하는 필터
    """
    if not text or not keywords:
        return text

    if isinstance(keywords, str):
        keywords = [keywords]

    highlighted_text = text
    for keyword in keywords:
        if keyword:
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_text = pattern.sub(
                f'<span class="highlight-keyword">{keyword}</span>', highlighted_text
            )

    return mark_safe(highlighted_text)
