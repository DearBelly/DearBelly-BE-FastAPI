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
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
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
    당신은 현재 시니어 개발자 역할을 맡고 있으며, 제출된 Pull Request(PR)에 대해 동료 개발자에게 건설적이고 상세한 코드 리뷰를 제공해야 합니다.

    - 요구사항:
    1.  분석 대상: 아래에 제공된 PR 제목, 본문, 그리고 변경된 파일 목록을 바탕으로 PR의 의도와 변경 내용을 종합적으로 이해하십시오.
    2.  페르소나: 공격적이거나 비판적인 어조가 아닌, 팀의 성장과 코드 품질 향상을 돕는 긍정적이고 건설적인 피드백을 제공하십시오.
    3.  피드백 형식: 다음 5가지 핵심 항목에 대해 구체적인 피드백을 작성해 주세요. 각 항목별로 제목을 달아 명확하게 구분해 주세요.

    - PR 정보:
    PR 제목: {pr_title}
    PR 본문: {pr_body}
    변경된 파일 목록: {changed_files}
    ---

    - 실제 코드 변경(diff):
    {diff_output}
    ---

    - 코드 리뷰 내용:

    ### 1. 주요 변경 사항 요약 및 의도 파악
    제공된 정보를 바탕으로 이 PR의 핵심적인 변경 내용이 무엇이며, 어떤 문제를 해결하거나 어떤 기능을 구현하려 하는지 개발자의 의도를 존중하며 간결하게 요약해 주세요.

    ### 2. 코드 품질 및 가독성
    * 코드 스타일: PEP 8, Clean Code 원칙 등 팀의 컨벤션을 준수했는지 검토해 주세요.
    * 변수/함수명: 변수, 함수, 클래스 이름이 명확하고 의도를 잘 드러내는지 평가해 주세요.
    * 주석/문서화: 복잡한 로직이나 비즈니스 규칙에 대한 설명이 충분히 포함되어 있는지 확인해 주세요.
    * 중복 코드: 유사하거나 반복되는 로직이 있는지 파악하고, 재사용 가능한 함수나 클래스로 분리할 것을 제안해 주세요.

    ### 3. 잠재적 버그 및 엣지 케이스
    * 논리적 오류: 코드가 예상치 못한 상황(예: 입력 값 없음, null 값, 0으로 나누기)에서 오류를 일으킬 수 있는지 검토해 주세요.
    * 경쟁 상태 (Race Condition): 멀티쓰레드/비동기 환경에서 발생할 수 있는 잠재적인 문제를 지적해 주세요.
    * 에러 핸들링: 예외 처리가 적절하게 구현되었는지, 사용자에게 의미 있는 에러 메시지를 제공하는지 확인해 주세요.

    ### 4. 성능 및 효율성
    * 시간 복잡도: 현재 구현된 알고리즘이 대규모 데이터에 대해 비효율적이지 않은지 검토해 주세요.
    * 자원 사용: 메모리 누수나 불필요한 I/O, 과도한 DB 쿼리 등이 발생할 가능성은 없는지 확인해 주세요.
    * 최적화 제안: 더 효율적인 자료 구조나 알고리즘을 사용하여 성능을 개선할 수 있는 부분을 구체적으로 제안해 주세요.

    ### 5. 보안 및 아키텍처
    * 보안 취약점: SQL Injection, XSS, 불충분한 입력 값 검증 등과 같은 잠재적인 보안 위험이 있는지 검토해 주세요.
    * 아키텍처 적합성: 이 PR의 변경 사항이 기존 시스템 아키텍처의 설계 원칙과 잘 부합하는지 평가해 주세요.
    * 확장성: 향후 기능 확장 시 이 코드가 유연하게 대처할 수 있도록 설계되었는지 의견을 제시해 주세요.
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