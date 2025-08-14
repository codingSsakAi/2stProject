// 메인 JavaScript 파일
document.addEventListener('DOMContentLoaded', function () {
  // 페이지 로드 시 페이드인 애니메이션
  const fadeElements = document.querySelectorAll('.fade-in');
  fadeElements.forEach((element) => {
    element.style.opacity = '0';
    element.style.transform = 'translateY(20px)';

    setTimeout(() => {
      element.style.transition = 'all 0.6s ease-out';
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
    }, 100);
  });

  // 폼 유효성 검사 강화
  const allForms = document.querySelectorAll('form');
  allForms.forEach((form) => {
    form.addEventListener('submit', function (e) {
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });

  // 부트스트랩 툴팁 초기화
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // 부트스트랩 팝오버 초기화
  const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });

  // 스크롤 시 네비게이션 바 스타일 변경
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', function () {
      if (window.scrollY > 50) {
        navbar.classList.add('navbar-scrolled');
      } else {
        navbar.classList.remove('navbar-scrolled');
      }
    });
  }

  // 모바일 메뉴 닫기 (링크 클릭 시)
  const navLinks = document.querySelectorAll('.navbar-nav a');
  const navbarCollapse = document.querySelector('.navbar-collapse');

  navLinks.forEach((link) => {
    link.addEventListener('click', () => {
      if (navbarCollapse.classList.contains('show')) {
        navbarCollapse.classList.remove('show');
      }
    });
  });

  // 폼 필드 자동 저장 (localStorage)
  const formFields = document.querySelectorAll('input, select, textarea');
  formFields.forEach((field) => {
    const fieldName = field.name;
    if (fieldName) {
      // 저장된 값 복원
      const savedValue = localStorage.getItem(`form_${fieldName}`);
      if (savedValue && field.type !== 'password') {
        field.value = savedValue;
      }

      // 값 변경 시 저장
      field.addEventListener('change', function () {
        if (field.type !== 'password') {
          localStorage.setItem(`form_${fieldName}`, field.value);
        }
      });
    }
  });

  // 알림 메시지 자동 숨김
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // 로딩 스피너 표시/숨김 함수
  window.showLoading = function () {
    const spinner = document.createElement('div');
    spinner.id = 'loading-spinner';
    spinner.className = 'position-fixed top-50 start-50 translate-middle';
    spinner.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">로딩중...</span>
            </div>
        `;
    document.body.appendChild(spinner);
  };

  window.hideLoading = function () {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
      spinner.remove();
    }
  };

  // 페이지 새로고침 시 폼 데이터 경고 (폼 제출 시에는 제외) - 비활성화됨
  /*
  window.addEventListener('beforeunload', function (e) {
    const allForms = document.querySelectorAll('form');
    let hasData = false;
    let isSubmitting = false;

    // 폼 제출 중인지 확인
    allForms.forEach((form) => {
      if (form.dataset.submitting === 'true') {
        isSubmitting = true;
        return;
      }
    });

    // 폼 제출 중이면 경고 표시하지 않음
    if (isSubmitting) {
      return;
    }

    allForms.forEach((form) => {
      const formData = new FormData(form);
      for (let pair of formData.entries()) {
        if (pair[1] && pair[1].trim() !== '') {
          hasData = true;
          break;
        }
      }
    });

    if (hasData) {
      e.preventDefault();
      e.returnValue = '입력한 데이터가 있습니다. 페이지를 떠나시겠습니까?';
      return '입력한 데이터가 있습니다. 페이지를 떠나시겠습니까?';
    }
  });
  */

  // 폼 제출 시 플래그 설정
  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', function () {
      this.dataset.submitting = 'true';
    });
  });

  // 콘솔 로그 스타일링
  
});
