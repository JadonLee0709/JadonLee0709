# stock_project.py
# update_251110_fixed_MAs + math_analysis_derivatives + trend/peaks/backtest

import time
import re
from typing import Optional, List
from urllib.parse import quote
import webbrowser
import requests
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import concurrent.futures
import multiprocessing
import numpy as np

# GUI
import tkinter as tk
from tkinter import simpledialog, messagebox

# -----------------------------
# 공통 설정
# -----------------------------
BASE_URL = "https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://finance.naver.com/",
}

SEARCH_HEADERS = {
    **HEADERS,
    "Referer": "https://search.naver.com/",
}

# 고정 이동평균 창 길이 (요청사항)
FIXED_WINDOWS = (5, 20, 60, 120)


def _set_korean_font():
    try:
        plt.rc("font", family="AppleGothic")  # macOS
    except Exception:
        try:
            plt.rc("font", family="Malgun Gothic")  # Windows
        except Exception:
            plt.rc("font", family="NanumGothic")  # Linux
    plt.rcParams["axes.unicode_minus"] = False


_set_korean_font()

# -----------------------------
# 브라우저 열기
# -----------------------------
def open_finance_search(query: str):
    webbrowser.open_new_tab("https://www.naver.com")


# 붙여넣은 텍스트에서 6자리 코드 추출
CODE_RE = re.compile(r"\b(\d{6})\b")


def pick_code_from_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = CODE_RE.search(text)
    return m.group(1) if m else None


# -----------------------------
# 로컬 폴백 사전
# -----------------------------
FALLBACK_MAP = {
    "삼성전자": "005930",
    "삼성전자우": "005935",
    "네이버": "035420",
    "NAVER": "035420",
    "카카오": "035720",
    "SK하이닉스": "000660",
    "현대차": "005380",
    "기아": "000270",
}

# -----------------------------
# 네이버 검색에서 종목코드 추출
# -----------------------------
def get_code_from_naver_search(query: str) -> Optional[str]:
    url = "https://search.naver.com/search.naver?query={}".format(quote(query))
    try:
        r = requests.get(url, headers=SEARCH_HEADERS, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print("[WARN] naver search request fail: {}".format(e))
        return None

    html = r.text
    m = re.findall(r"/item/(?:main|coinfo|sise_day)\.naver\?[^\"'>]*\bcode=(\d{6})", html)
    if m:
        return m[0]

    m = re.findall(r'"(?:code|stockCd)"\s*:\s*"(\d{6})"', html)
    if m:
        return m[0]

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")
    m = re.search(r"\b(\d{6})\b(?=[^\n]{0,40}\b(?:KOSPI|KOSDAQ|KRX)\b)", text, re.I)
    if m:
        return m[0]

    m = CODE_RE.findall(text)
    if m:
        seen = []
        for c in m:
            if c not in seen:
                seen.append(c)
        return seen[0] if seen else None
    return None


# -----------------------------
# 페이지 단위 크롤링 함수 (멀티프로세싱용)
# -----------------------------
def _fetch_page(code: str, page: int) -> pd.DataFrame:
    url = BASE_URL.format(code=code, page=page)
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        tables = pd.read_html(res.text, match="날짜")
        if not tables:
            return pd.DataFrame()
        df = tables[0]
    except Exception:
        return pd.DataFrame()

    df = df.dropna(how="any")
    if "날짜" not in df.columns or df.empty:
        return pd.DataFrame()
    df = df[df["날짜"].astype(str).str.contains(r"\d{4}\.\d{2}\.\d{2}", na=False)]
    if df.empty:
        return pd.DataFrame()

    df = df.rename(
        columns={
            "날짜": "Date",
            "종가": "Close",
            "전일비": "Change",
            "시가": "Open",
            "고가": "High",
            "저가": "Low",
            "거래량": "Volume",
        }
    )

    for col in ["Close", "Open", "High", "Low", "Volume"]:
        s = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("-", "0", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(s, errors="coerce").fillna(0).astype("int64")

    df["Date"] = pd.to_datetime(df["Date"], format="%Y.%m.%d", errors="coerce")
    df = df.dropna(subset=["Date"])
    return df[["Date", "Close", "Open", "High", "Low", "Volume"]]


# -----------------------------
# 멀티프로세싱 데이터 수집
# -----------------------------
def Daily_prices_naver(code: str, pages: int = 10, workers: int = None) -> pd.DataFrame:
    if workers is None:
        workers = multiprocessing.cpu_count()

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_fetch_page, code, p) for p in range(1, pages + 1)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    frames = [df for df in results if not df.empty]
    if not frames:
        return pd.DataFrame(columns=["Date", "Close", "Open", "High", "Low", "Volume"])

    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return out


# -----------------------------
# 이동평균선 계산 (고정: 5, 20, 60, 120)
# -----------------------------
def _add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for w in FIXED_WINDOWS:
        col = f"MA{w}"
        out[col] = out["Close"].rolling(window=w, min_periods=w).mean()
    return out


def stock_calculator(code: str, pages: int = 20, workers: int = None) -> pd.DataFrame:
    prices = Daily_prices_naver(code=code, pages=pages, workers=workers)
    prices = _add_moving_averages(prices)
    return prices


# -----------------------------
# 그래프 (고정: 5, 20, 60, 120)
# -----------------------------
def graph_operator(df: pd.DataFrame):
    """
    - 종가 + 5/20/60/120일선
    - (수정) 극대/극소 점 제거함
    - (유지) 극대/극소로 만든 추세선은 남겨둠
    """
    # 극대/극소 정보 추가
    work = detect_local_extrema(df, window=2).reset_index(drop=True)

    dates = work["Date"]
    x_all = np.arange(len(work))

    plt.figure(figsize=(12, 6))
    plt.title("이동평균선(5, 20, 60, 120) + 극대/극소 채널 추세선")
    plt.xlabel("날짜")
    plt.ylabel("주가")
    plt.grid(True)

    # 종가
    plt.plot(dates, work["Close"], label="종가", color="black")

    # 이동평균선들
    for w in FIXED_WINDOWS:
        col = f"MA{w}"
        if col in work.columns:
            plt.plot(dates, work[col], label=f"{w}일선", linestyle="--")

    # 극대/극소만 가져오되 점은 찍지 않음
    peaks = work[work["is_peak"]]
    troughs = work[work["is_trough"]]

    # ---------- 극대들로 상단 추세선(직선) ----------
    if len(peaks) >= 2:
        px = peaks.index.to_numpy()
        py = peaks["Close"].to_numpy()

        a_peak, b_peak = np.polyfit(px, py, 1)
        peak_trend = a_peak * x_all + b_peak

        plt.plot(dates, peak_trend, color="red", linestyle="-", alpha=0.7, label="극대 추세선 (상단 채널)")

    # ---------- 극소들로 하단 추세선(직선) ----------
    if len(troughs) >= 2:
        tx = troughs.index.to_numpy()
        ty = troughs["Close"].to_numpy()

        a_trough, b_trough = np.polyfit(tx, ty, 1)
        trough_trend = a_trough * x_all + b_trough

        plt.plot(dates, trough_trend, color="blue", linestyle="-", alpha=0.7, label="극소 추세선 (하단 채널)")

    plt.legend()
    plt.tight_layout()
    plt.show()


# -----------------------------
# 알람 기능 (고정: 5 vs 120 교차)
# -----------------------------
def alarm_operator(df: pd.DataFrame) -> str:
    cs, cl = "MA5", "MA120"

    if cs not in df.columns or cl not in df.columns:
        return "⚖️ 필요한 이동평균 컬럼(MA5/MA120)이 없습니다."

    tmp = df.dropna(subset=[cs, cl])
    if len(tmp) < 2:
        return "⚖️ 데이터가 부족합니다."

    last = tmp.iloc[-1]
    prev = tmp.iloc[-2]

    if (last[cs] > last[cl]) and (prev[cs] <= prev[cl]):
        return "📈 골든크로스(5↗120)."
    elif (last[cs] < last[cl]) and (prev[cs] >= prev[cl]):
        return "📉 데드크로스(5↘120)."
    else:
        return "⚖️ 특별한 신호 없음"


# -----------------------------
# 수학적 분석 (미분 기반 특징 + 패턴 통계)
# -----------------------------
def _add_derivative_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Close와 MA(5,20,60,120)에 대해 1차/2차 차분(=미분 근사)을 계산해서
    d1_*, d2_* 컬럼을 추가한다.
    """
    out = df.copy()

    # 가격 자체의 변화량(1차, 2차)
    out["d1_Close"] = out["Close"].diff()       # 1차 미분 근사
    out["d2_Close"] = out["d1_Close"].diff()    # 2차 미분 근사

    for w in FIXED_WINDOWS:
        col = f"MA{w}"
        if col in out.columns:
            v_col = f"d1_{col}"  # 1차 미분(기울기)
            a_col = f"d2_{col}"  # 2차 미분(기울기 변화, 곡률)
            out[v_col] = out[col].diff()
            out[a_col] = out[v_col].diff()

    return out


def math_analysis_report(df: pd.DataFrame, horizon: int = 5) -> str:
    """
    - 미분 기반 특징을 추가하고
    - '상승 추세(20/60 우상향) + 단기 조정(5일선 하락 & 가격이 5/20 아래)' 패턴에서
      h일 뒤 수익률 통계를 계산해 리포트 문자열을 반환한다.
    """
    if df.empty or len(df) < 150:
        return "데이터가 부족하여 수학적 분석을 수행할 수 없습니다. (최소 150개 이상 필요)"

    work = _add_derivative_features(df.copy())

    # 향후 horizon일 수익률
    future_col = f"future_ret_{horizon}"
    work[future_col] = work["Close"].shift(-horizon) / work["Close"] - 1.0

    # 레짐 조건: 60일선, 20일선이 모두 우상향 & 20일선이 60일선 위
    cond_regime = (
        (work.get("d1_MA60", 0) > 0)
        & (work.get("d1_MA20", 0) > 0)
        & (work.get("MA20", 0) > work.get("MA60", 0))
    )

    # 단기 조정: 5일선 기울기 < 0, 가격이 5/20일선 아래
    cond_pullback = (
        (work.get("d1_MA5", 0) < 0)
        & (work["Close"] < work.get("MA5", work["Close"] * 0 + float("inf")))
        & (work["Close"] < work.get("MA20", work["Close"] * 0 + float("inf")))
    )

    pattern = cond_regime & cond_pullback
    pattern_df = work.loc[pattern].dropna(subset=[future_col])

    total = len(pattern_df)

    # 현재 상태
    current = work.iloc[-1]
    now_regime = bool(cond_regime.iloc[-1])
    now_pullback = bool(cond_pullback.iloc[-1])

    lines: List[str] = []
    lines.append(f"[수학적 분석 요약 - 향후 {horizon}거래일 기준]")

    # 1) 현재 기울기 상태
    lines.append("1) 현재 이동평균선 기울기 상태:")
    for w in FIXED_WINDOWS:
        v_col = f"d1_MA{w}"
        if v_col in work.columns and pd.notna(current.get(v_col)):
            val = float(current[v_col])
            if val > 0:
                direction = "상승(우상향)"
            elif val < 0:
                direction = "하락(우하향)"
            else:
                direction = "거의 보합"
            lines.append(f"   - {w:3}일선: {direction} (최근 기울기: {val:.2f})")

    # 2) 현재 패턴 분류
    lines.append("\n2) 현재 패턴 판단:")
    if now_regime and now_pullback:
        lines.append("   - 상태: '상승 추세 속 단기 조정' 패턴에 해당합니다.")
    elif now_regime and not now_pullback:
        lines.append("   - 상태: 상승 추세는 유지 중이지만, 단기 조정 구간은 아닙니다.")
    elif (not now_regime) and now_pullback:
        lines.append("   - 상태: 단기 조정처럼 보이지만, 장기 추세(20/60 기준)가 명확한 상승은 아닙니다.")
    else:
        lines.append("   - 상태: 상승 추세도, 전형적인 단기 조정 패턴도 아닙니다.")

    # 3) 과거 통계
    lines.append("\n3) 과거 데이터에서 같은 패턴의 성과:")

    if total < 5:
        lines.append(f"   - 동일 패턴 발생 횟수: {total}회 (5회 미만 → 통계적 신뢰도 낮음)")
        return "\n".join(lines)

    avg_ret = float(pattern_df[future_col].mean())
    win_rate = float((pattern_df[future_col] > 0).mean())
    max_ret = float(pattern_df[future_col].max())
    min_ret = float(pattern_df[future_col].min())

    lines.append(f"   - 동일 패턴 발생 횟수: {total}회")
    lines.append(f"   - 평균 {horizon}일 수익률: {avg_ret * 100:.2f}%")
    lines.append(f"   - 상승한 비율(승률): {win_rate * 100:.1f}%")
    lines.append(f"   - 최고 {horizon}일 수익률: {max_ret * 100:.2f}%")
    lines.append(f"   - 최저 {horizon}일 수익률: {min_ret * 100:.2f}%")

    lines.append(
        "\n※ 위 통계는 과거 패턴 분석 결과일 뿐, "
        "미래 수익을 보장하지 않습니다. (거래비용/슬리피지 미반영)"
    )

    return "\n".join(lines)

# -----------------------------
# 극대/극소(국소 고점/저점) 탐지
# -----------------------------
def detect_local_extrema(df: pd.DataFrame, window: int = 1) -> pd.DataFrame:
    """
    단순한 방법으로 국소 극대/극소를 찾는다.
    window=1이면 i-1, i, i+1 세 점 비교해서
    - i가 양쪽보다 크면 is_peak=True (local maximum)
    - i가 양쪽보다 작으면 is_trough=True (local minimum)
    """
    work = df.copy().reset_index(drop=True)
    n = len(work)
    is_peak = [False] * n
    is_trough = [False] * n

    for i in range(window, n - window):
        center = work.at[i, "Close"]
        left = work.at[i - window, "Close"]
        right = work.at[i + window, "Close"]

        # 극대 (local maximum)
        if center > left and center >= right:
            is_peak[i] = True
        # 극소 (local minimum)
        if center < left and center <= right:
            is_trough[i] = True

    work["is_peak"] = is_peak
    work["is_trough"] = is_trough
    return work

# -----------------------------
# 추세 레이블링 (상승장/하락장/전환 구간)
# -----------------------------
def add_trend_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    MA60, MA120과 그 기울기를 이용해서
    각 날짜별로 'bull', 'bear', 'transition' 레이블을 붙인다.
    """
    work = _add_moving_averages(df.copy())
    work = _add_derivative_features(work)

    labels = []
    for _, row in work.iterrows():
        d1_ma60 = row.get("d1_MA60", 0)
        d1_ma120 = row.get("d1_MA120", 0)
        ma60 = row.get("MA60", np.nan)
        ma120 = row.get("MA120", np.nan)

        label = "transition"
        if pd.notna(ma60) and pd.notna(ma120):
            # 장기 상승장: 둘 다 우상향 + MA60 > MA120
            if (d1_ma60 > 0) and (d1_ma120 > 0) and (ma60 > ma120):
                label = "bull"
            # 장기 하락장: 둘 다 우하향 + MA60 < MA120
            elif (d1_ma60 < 0) and (d1_ma120 < 0) and (ma60 < ma120):
                label = "bear"
        labels.append(label)

    work["trend_label"] = labels
    return work


# -----------------------------
# 극대/극소(국소 고점/저점) 탐지
# -----------------------------
def detect_local_extrema(df: pd.DataFrame, window: int = 1) -> pd.DataFrame:
    """
    단순한 방법으로 국소 극대/극소를 찾는다.
    window=1이면 i-1, i, i+1 세 점 비교해서
    - i가 양쪽보다 크면 is_peak=True
    - i가 양쪽보다 작으면 is_trough=True
    """
    work = df.copy().reset_index(drop=True)
    n = len(work)
    is_peak = [False] * n
    is_trough = [False] * n

    for i in range(window, n - window):
        center = work.at[i, "Close"]
        left = work.at[i - window, "Close"]
        right = work.at[i + window, "Close"]

        if center > left and center >= right:
            is_peak[i] = True
        if center < left and center <= right:
            is_trough[i] = True

    work["is_peak"] = is_peak
    work["is_trough"] = is_trough
    return work


# -----------------------------
# 단순 MA20·MA60 추세+조정 전략 백테스트
# -----------------------------
def _max_drawdown(equity: pd.Series) -> float:
    """
    최대 낙폭(MDD) 계산: (최고점 대비 최저점 하락률)
    """
    cum_max = equity.cummax()
    dd = (equity - cum_max) / cum_max
    return float(dd.min())  # 음수 값


def backtest_ma20_60_strategy(
    df: pd.DataFrame,
    fee_rate: float = 0.0005,   # 왕복 수수료·세금 대충 0.05% 가정
    initial_cash: float = 10_000_000.0
) -> dict:
    """
    MA20·MA60 + 20일선 기울기 기반 단순 전략 백테스트.
    - 진입: Close > MA20, MA20 > MA60, d1_MA20 > 0
    - 청산: Close < MA20 or MA20 < MA60
    - 항상 전액 매수 / 전액 현금
    """
    # 이동평균/미분 컬럼이 없으면 추가
    work = df.copy()
    if "MA20" not in work.columns or "MA60" not in work.columns:
        work = _add_moving_averages(work)
    work = _add_derivative_features(work)

    # 필수 컬럼 체크
    for col in ["Close", "MA20", "MA60", "d1_MA20"]:
        if col not in work.columns:
            raise ValueError(f"필수 컬럼이 없습니다: {col}")

    work = work.dropna(subset=["Close", "MA20", "MA60", "d1_MA20"]).reset_index(drop=True)

    cash = initial_cash
    shares = 0.0
    equity_list: List[float] = []
    position_flag: List[int] = []
    trades: List[dict] = []

    in_position = False
    entry_price = None
    entry_idx = None

    for i, row in work.iterrows():
        price = float(row["Close"])
        ma20 = float(row["MA20"])
        ma60 = float(row["MA60"])
        d1_ma20 = float(row["d1_MA20"])

        # 보유 중 → 청산 조건 체크
        if in_position:
            if (price < ma20) or (ma20 < ma60):
                # 전량 매도
                sell_price = price * (1 - fee_rate)
                cash = shares * sell_price
                trades.append({
                    "entry_idx": entry_idx,
                    "exit_idx": i,
                    "entry_price": entry_price,
                    "exit_price": sell_price,
                    "ret": sell_price / entry_price - 1.0,
                })
                shares = 0.0
                in_position = False
                entry_price = None
                entry_idx = None
        else:
            # 미보유 → 진입 조건 체크
            if (price > ma20) and (ma20 > ma60) and (d1_ma20 > 0):
                buy_price = price * (1 + fee_rate)
                shares = cash / buy_price
                cash = 0.0
                in_position = True
                entry_price = buy_price
                entry_idx = i

        # 하루 종료 후 평가액 기록
        equity = cash + shares * price
        equity_list.append(equity)
        position_flag.append(1 if in_position else 0)

    work["equity"] = equity_list
    work["position"] = position_flag

    # 일별 수익률
    work["equity_ret"] = work["equity"].pct_change().fillna(0.0)

    total_return = work["equity"].iloc[-1] / initial_cash - 1.0
    mdd = _max_drawdown(work["equity"])
    # 연율화 샤프 (252거래일 가정)
    mean_ret = work["equity_ret"].mean()
    std_ret = work["equity_ret"].std()
    if std_ret > 0:
        sharpe = (mean_ret / std_ret) * np.sqrt(252)
    else:
        sharpe = 0.0

    # 트레이드 통계
    n_trades = len(trades)
    if n_trades > 0:
        rets = np.array([t["ret"] for t in trades])
        win_rate = float((rets > 0).mean())
        avg_trade_ret = float(rets.mean())
    else:
        win_rate = 0.0
        avg_trade_ret = 0.0

    result = {
        "total_return": total_return,
        "MDD": mdd,
        "sharpe": sharpe,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "avg_trade_ret": avg_trade_ret,
        "equity_curve": work[["Date", "equity", "position"]].copy(),
        "trades": trades,
    }
    return result


def print_backtest_report(result: dict, name: str = "MA20·60 전략"):
    """
    backtest_ma20_60_strategy 결과 dict를 예쁘게 출력
    """
    print(f"\n=== 백테스트 결과: {name} ===")
    print(f"총 수익률: {result['total_return'] * 100:.2f}%")
    print(f"최대 낙폭(MDD): {result['MDD'] * 100:.2f}%")
    print(f"샤프 비율(단순): {result['sharpe']:.2f}")
    print(f"트레이드 수: {result['n_trades']}회")
    if result["n_trades"] > 0:
        print(f"승률: {result['win_rate'] * 100:.1f}%")
        print(f"평균 트레이드 수익률: {result['avg_trade_ret'] * 100:.2f}%")
    print("====================================")


# -----------------------------
# 코드 해석
# -----------------------------
def resolve_to_code(user_input: str) -> Optional[str]:
    s = (user_input or "").strip()
    c = pick_code_from_text(s)
    if c:
        return c
    if s in FALLBACK_MAP:
        return FALLBACK_MAP[s]
    return get_code_from_naver_search(s)


# -----------------------------
# GUI
# -----------------------------
def run_app():
    text = simpledialog.askstring(
        "종목 입력",
        "종목코드(6자리) 또는 종목명을 입력하세요\n예) 005930 또는 삼성전자",
    )
    if not text:
        return

    code = resolve_to_code(text)
    if not code:
        open_finance_search(text)
        messagebox.showinfo("코드 입력 안내", "브라우저에서 종목 코드 확인 후 붙여넣으세요.")
        pasted = simpledialog.askstring("코드 붙여넣기", "6자리 코드 또는 종목 URL:")
        code = pick_code_from_text(pasted)

    if not code:
        messagebox.showerror("입력 오류", f"유효한 코드가 없습니다. (입력: {text})")
        return

    pages = simpledialog.askinteger("페이지 수", "몇 페이지 가져올까요?", minvalue=1, maxvalue=100)
    if not pages:
        return

    workers = simpledialog.askinteger(
        "코어 수",
        "사용할 코어 개수 (기본: 최대치)",
        minvalue=1,
        maxvalue=multiprocessing.cpu_count(),
    )

    df = stock_calculator(code, pages, workers=workers)
    if df.empty:
        messagebox.showerror("데이터 없음", f"code={code} 데이터 없음")
        return

    graph_operator(df)
    signal = alarm_operator(df)

    # 수학적 분석 리포트 생성
    report = math_analysis_report(df, horizon=5)

    messagebox.showinfo("알림", f"{signal}\n\n{report}")


def start_gui():
    root = tk.Tk()
    root.title("주식 그래프 앱")
    button = tk.Button(root, text="실행", command=run_app, width=20)
    button.pack(pady=20)
    root.mainloop()


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    mode = input("실행 모드 선택 (1: CLI, 2: GUI) → ").strip()
    if mode == "1":
        text = input("종목코드(6자리) 또는 종목명을 입력하세요: ").strip()
        code = resolve_to_code(text)

        if not code:
            print("❌ 코드 확인 불가")
        else:
            pages = int(input("몇 페이지를 가져올까요? (예: 20): ").strip() or "20")
            workers = input(
                f"몇 개 코어를 사용할까요? (최대={multiprocessing.cpu_count()}): "
            ).strip()
            workers = int(workers) if workers else None

            df = stock_calculator(code, pages, workers=workers)
            if df.empty:
                print(f"❌ 데이터 없음 (code={code})")
            else:
                print(df.tail())
                signal = alarm_operator(df)
                print(signal)

                # 극대/극소(국소 고점/저점) 탐지
                ext_df = detect_local_extrema(df, window=1)
                recent_ext = ext_df.tail(30)  # 최근 30일 정도만 체크

                peaks = recent_ext[recent_ext["is_peak"]]
                troughs = recent_ext[recent_ext["is_trough"]]

                print("\n=== 최근 극대/극소 정보 ===")
                if not peaks.empty:
                    print("최근 국소 고점(peak)들:")
                    for _, row in peaks.tail(5).iterrows():
                        print(f"  - {row['Date'].date()} 종가 {row['Close']}")
                else:
                    print("최근 30일 내 국소 고점 없음")

                if not troughs.empty:
                    print("최근 국소 저점(trough)들:")
                    for _, row in troughs.tail(5).iterrows():
                        print(f"  - {row['Date'].date()} 종가 {row['Close']}")
                else:
                    print("최근 30일 내 국소 저점 없음")

                # 수학적 분석 리포트 출력 (기본 5거래일 기준)
                report = math_analysis_report(df, horizon=5)
                print("\n=== 수학적 분석(미분 기반) ===")
                print(report)

                # 추세 레이블 확인
                trend_df = add_trend_labels(df)
                print("\n최근 추세 레이블:", trend_df["trend_label"].iloc[-1])

                # MA20·60 전략 백테스트
                try:
                    bt_result = backtest_ma20_60_strategy(df)
                    print_backtest_report(bt_result, name=f"{code} MA20·60 전략")
                except Exception as e:
                    print("[WARN] 백테스트 중 오류:", e)

                graph_operator(df)
    else:
        start_gui()