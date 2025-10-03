import os
import google.generativeai as genai
from github import Github

def is_image_file(filename):
    """
    파일 이름이 이미지 확장자를 포함하는지 확인합니다.
    """
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.ico')
    return filename.lower().endswith(image_extensions)

def send_prompt():
    """
    Gemini API를 사용하여 PR에 대한 코드 리뷰를 생성하고,
    그 결과를 GitHub PR에 댓글로 게시하는 함수입니다.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token or not gemini_api_key:
        print("Error: GEMINI_API_KEY 또는 GITHUB_TOKEN 환경 변수가 설정되지 않았습니다.")
        raise Exception("환경 변수(GEMINI_API_KEY, GITHUB_TOKEN)가 설정되지 않았습니다.")

    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(model_name="gemini-2.5-pro")
    g = Github(github_token)

    # GitHub Actions 컨텍스트에서 PR 정보 가져오기
    repository_name = os.getenv('GITHUB_REPOSITORY')
    pr_number = os.getenv('PR_NUMBER')

    if not pr_number:
        print("Error: PR_NUMBER 환경 변수가 설정되지 않았습니다. PR 이벤트에서만 실행 가능합니다.")
        return

    repo = g.get_repo(repository_name)
    pull_request = repo.get_pull(int(pr_number))

    # PR 정보 추출
    pr_title = pull_request.title
    pr_body = pull_request.body

    # 변경된 파일 목록과 diff 내용 전처리
    changed_files = []
    diff_output = ""
    for file in pull_request.get_files():
        if is_image_file(file.filename):
            print(f"Skipping image file: {file.filename}")
            continue

        changed_files.append(file.filename)
        diff_output += f"--- file: {file.filename}\n{file.patch}\n\n"

    # 이미지 파일만 있는 경우
    if not diff_output:
        print("PR에 분석할 코드가 없습니다. 이미지 파일만 변경되었습니다.")
        pull_request.create_issue_comment(f"## 🤖 Gemini 코드 리뷰 결과\n\n이 PR은 코드 변경 없이 이미지 파일만 포함하고 있어, 분석을 건너뜁니다.")
        return

    # Gemini에 전달할 프롬프트 구성
    prompt = f"""
    너는 시니어 개발자다. 제출된 Pull Request(PR)에 대해 건설적이고 상세한 코드 리뷰를 제공해주세요.
    리뷰는 반드시 '우선순위 레벨(P1~P5)'로 분류해 주세요.
    
    [우선순위 정의]
    - P1: 꼭 반영해주세요 (Request changes) — 기능 오동작, 보안 취약점, 데이터 손실 위험, 계약 위반, 테스트 실패 가능성이 높은 핵심 문제
    - P2: 적극적으로 고려해주세요 (Request changes) — 유지보수/확장성/성능 저하 가능성이 큰 구조적 개선 필요
    - P3: 웬만하면 반영해 주세요 (Comment) — 가독성/일관성/경계 조건/에러 처리 보완 등 중간 수준 개선
    - P4: 반영해도 좋고 넘어가도 좋습니다 (Approve) — 선택 사항. 팀 컨벤션/취향 차이 영역
    - P5: 그냥 사소한 의견입니다 (Approve) — 미세 스타일, 주석 표현, 네이밍 제안 등
    
    [리뷰 페르소나]
    - 공격적이거나 비판적 어조는 피하고, 팀의 성장과 코드 품질 향상을 돕는 긍정적이고 구체적인 피드백을 주세요.
    - 문제 지적 시에는 “왜 문제인지(근거) → 영향 → 구체적 해결책/코드 스니펫” 순서로 작성해 주세요.
    
    [PR 정보]
    PR 제목: {pr_title}
    PR 본문: {pr_body}
    변경된 파일 목록: {changed_files}
    ---

    [실제 코드 변경(diff)]
    {diff_output}
    ---

    [출력 형식]
    아래 섹션과 형식을 반드시 지켜서 출력하세요.
    
    ## 1) PR 의도 요약
    - 이 PR의 목표/맥락/핵심 변경 사항을 3~5줄로 간결히 요약해라.
    
    ## 2) 전반적 평가 (품질/가독성/테스트/아키텍처)
    - 컨벤션(PEP8/Clean Code) 준수 여부
    - 네이밍/모듈 경계/의존성 방향
    - 테스트 전략(단위/통합) 적절성 한 줄 평가
    
    ## 3) 우선순위별 피드백 목록
    - 아래 형식을 반복하여, 파일·라인 기준으로 구체적으로 작성해라.
    - 최소한 P1/P2는 근거와 수정 제안을 포함해야 하며, 가능하면 코드 패치 예시를 함께 제시해야한다.
    
    ### [P레벨] 제목 한 줄 요약
    - 파일/위치: <path>:<line or range>
    - 근거(왜 문제인지/왜 개선인지):
    - 영향(버그/보안/성능/유지보수 등):
    - 제안(구체적 조치, 대안, 참고 링크는 선택):
    """

    try:
        response = model.generate_content(prompt)
        gemini_analysis = response.text

        # 생성된 분석 결과를 PR에 댓글로 작성
        comment_body = f"## 🤖 Gemini 코드 리뷰 결과\n\n{gemini_analysis}"
        pull_request.create_issue_comment(comment_body)
        print("Gemini 코드 리뷰가 PR에 성공적으로 게시되었습니다.")

    except Exception as e:
        comment_body = f"Gemini 코드 리뷰 중 오류가 발생했습니다: {e}"
        pull_request.create_issue_comment(comment_body)
        print(comment_body)


if __name__ == "__main__":
    send_prompt()