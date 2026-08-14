import pandas as pd

from pathlib import Path


# 현재 프로젝트 폴더 위치
BASE_DIR = Path(__file__).resolve().parent  # 절대 경로로 변환하여 파일명 제외, 파일 존재하는 상위 폴더만 가져옴.
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# 데이터셋들
FILES = {
    2023: DATA_DIR / '2023y_IVS_DATA.xlsx',
    2024: DATA_DIR / '2024y_IVS_DATA.xlsx',
    2025: DATA_DIR / '2025y_IVS_DATA.xlsx'
}

# 사용자에게 입력받을 조건인 성별, 연령대, 인원수, 테마
INPUT_COLUMNS = ['D_SEX', 'D_AGE', 'RQ7_1', 'Q3_1a1']
RAW_REGION_COLUMNS = [f'Q9_2a{i:02d}' for i in range(1, 18)] # 원본 엑셀에서 방문 지역을 나타내는 17개 열 자동 생성
REGION_COLUMNS = [f'REGION_{i:02d}' for i in range(1, 18)] 
USE_COLUMNS = ['pnid'] + INPUT_COLUMNS + RAW_REGION_COLUMNS

DESTINATIONS = [
    '서울특별시', '경기도', '인천광역시', '강원도', '대전광역시', '충청북도', '충청남도',
    '세종특별자치시', '경상북도', '경상남도', '대구광역시', '울산광역시', '부산광역시',
    '광주광역시', '전라북도', '전라남도', '제주특별자치도'
]

# 연도별 데이터 전처리
processed_data = []
quality_results = []

for year, file_path in FILES.items():
    if not file_path.exists():
        raise FileNotFoundError(f'원본 파일을 찾을 수 없습니다: {file_path}')

    print(year, '데이터 처리 시작')

    # 대용량 XLSX에서 모델에 필요한 열만 읽어 메모리 사용량을 줄임 (열은 위에서 정의한 거)
    df = pd.read_excel(file_path, usecols=USE_COLUMNS)
    original_rows = len(df)

    # 2023년에는 4번 휴양·휴식 항목이 없으므로 4~16번을 한 칸 이동
    if year == 2023:
        condition = df['Q3_1a1'].between(4, 16)
        df.loc[condition, 'Q3_1a1'] += 1

    # 결측치와 허용 범위를 벗어난 필수 입력 코드를 각각 확인
    missing_input = df[INPUT_COLUMNS].isna().any(axis=1) # 사용자 조건 열 중 하나라도 결측치가 있나 없나 확인
    valid_input = (                                      # 코드북에 있는 데이터와 동일한지(코드북 참고)
        df['D_SEX'].isin([1, 2])
        & df['D_AGE'].isin(range(1, 7))
        & df['RQ7_1'].isin(range(1, 4))
        & df['Q3_1a1'].isin(range(1, 18))
    )

    # 결측치, 중복, 비정상 코드 검사
    missing_input_count = int(missing_input.sum())
    invalid_code_count = int((~missing_input & ~valid_input).sum())
    missing_pnid_count = int(df['pnid'].isna().sum())
    duplicate_count = int(df.duplicated(subset='pnid').sum())

    # 중복된 행은 첫번째 응답만 적재 / ID 미존재, 필수 입력 코드가 비정상인 행은 학습에서 제외
    df = df[df['pnid'].notna() & valid_input].copy()
    df = df.drop_duplicates(subset='pnid', keep='first')

    # 각 지역 열은 방문 1, 미방문 0인 모델 정답값으로 변환한다.
    invalid_region_cells = 0

    for number, raw_column in enumerate(RAW_REGION_COLUMNS, start=1):
        values = df[raw_column]
        invalid_region_cells += int(
            (values.notna() & ~values.isin([0, number])).sum()  #비정상 지역 값 검
        )
        df[f'REGION_{number:02d}'] = (values == number).astype(int)

    # 방문 지역이 하나도 없는 응답자는 추천 모델의 정답이 없으므로 제외한다.
    no_region = df[REGION_COLUMNS].sum(axis=1).eq(0)
    no_region_count = int(no_region.sum())
    df = df[~no_region].copy()

    df['year'] = year
    df = df[['year', 'pnid'] + INPUT_COLUMNS + REGION_COLUMNS]
    df = df.reset_index(drop=True)

    # 연도별 제거 행, 결측치, 중복 ID, 비정상 코드 검사 결과를 저장하기 위한 라인
    quality_results.append({
        'year': year,
        'original_rows': original_rows,
        'final_rows': len(df),
        'removed_rows': original_rows - len(df),
        'missing_pnid': missing_pnid_count,
        'duplicate_pnid': duplicate_count,
        'missing_required_input': missing_input_count,
        'invalid_required_code': invalid_code_count,
        'invalid_region_cells': invalid_region_cells,
        'no_region_rows': no_region_count
    })

    processed_data.append(df)
    print(year, '데이터 처리 완료:', len(df), '행')


# 3개년 데이터 통합과 분포 검사

df_total = pd.concat(processed_data, ignore_index=True)

# 전처리 후에도 필수 열에 결측치가 남아 있으면 저장하지 않고 오류를 알린다.
if df_total[INPUT_COLUMNS + REGION_COLUMNS].isna().any().any():
    raise ValueError('전처리 결과에 처리되지 않은 결측치가 있습니다.')

region_summary = pd.DataFrame({
    'destination': DESTINATIONS,
    'visit_count': df_total[REGION_COLUMNS].sum().to_numpy()
})

# 다중 방문 조사이므로 지역별 방문률의 합계는 100%를 넘을 수 있다.
region_summary['visit_rate'] = (
    region_summary['visit_count'] / len(df_total)
)
region_summary['visit_rate_percent'] = (
    region_summary['visit_rate'] * 100
).round(2)

yearly_region_rate = (
    df_total.groupby('year')[REGION_COLUMNS]
    .mean()
    .rename(columns=dict(zip(REGION_COLUMNS, DESTINATIONS)))
)

# 확인 필요 시 주석 해제
# print('\n전체 데이터 크기:', df_total.shape)
# print('통합 중복 응답자 수:', df_total.duplicated(['year', 'pnid']).sum())
# print('\n연도별 지역 방문 비율(%):')
# print((yearly_region_rate * 100).round(2))


# 전처리 데이터와 검사 보고서(발표용) 저장

# 모델 학습용 2023~2025년 통합 데이터
df_total.to_csv(
    DATA_DIR / 'region_recommend_data.csv',
    index=False,
    encoding='utf-8-sig'
)

# 연도별 제거 행, 결측치, 중복 ID, 비정상 코드 검사 결과
pd.DataFrame(quality_results).to_csv(
    REPORT_DIR / 'data_quality_summary.csv',
    index=False,
    encoding='utf-8-sig'
)

# 3개년 전체 지역별 방문자 수와 방문률
region_summary.to_csv(
    REPORT_DIR / 'region_visit_summary.csv',
    index=False,
    encoding='utf-8-sig'
)

# 연도별 지역 방문률 비교 자료
yearly_region_rate.to_csv(
    REPORT_DIR / 'yearly_region_visit_rate.csv',
    encoding='utf-8-sig'
)

print('\n전처리 데이터와 검사 보고서 저장 완료')
