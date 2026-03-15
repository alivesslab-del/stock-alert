#!/usr/bin/env python3
"""
Telegram 자동 리포트 스크립트
  python telegram_report.py morning  → 08:00 KST Morning Macro Report
  python telegram_report.py preus    → 15:00 KST Pre-US Market Report
"""

import os, sys, requests, pytz
from datetime import datetime
from xml.etree import ElementTree as ET
import yfinance as yf

# ── 설정 ────────────────────────────────────────────────────
TG_TOKEN = os.environ.get('TG_TOKEN', '')
TG_CHAT  = os.environ.get('TG_CHAT',  '')
KST      = pytz.timezone('Asia/Seoul')

# ── 포트폴리오 (stock.html의 DEFAULT_PORTFOLIO와 동일하게 유지) ──
PORTFOLIO = [
    {'symbol': 'GOOGL',      'name': '알파벳A',            'shares': 4.625619, 'currency': 'USD', 'avg': 261.76,  'sector': 'Communication Services'},
    {'symbol': 'MO',         'name': '알트리아',            'shares': 2.450174, 'currency': 'USD', 'avg': 58.55,   'sector': 'Consumer Staples'},
    {'symbol': 'TSLA',       'name': '테슬라',              'shares': 1.473050, 'currency': 'USD', 'avg': 307.43,  'sector': 'Consumer Discretionary'},
    {'symbol': 'S',          'name': '센티넬원',             'shares': 1.0,      'currency': 'USD', 'avg': 14.65,   'sector': 'Information Technology'},
    {'symbol': 'NVDA',       'name': '엔비디아',             'shares': 6.367037, 'currency': 'USD', 'avg': 175.72,  'sector': 'Information Technology'},
    {'symbol': 'MCD',        'name': '맥도날드',             'shares': 0.191813, 'currency': 'USD', 'avg': 315.94,  'sector': 'Consumer Discretionary'},
    {'symbol': 'SCHD',       'name': '슈왑 미국배당 ETF',   'shares': 4.151897, 'currency': 'USD', 'avg': 29.36,   'sector': 'ETF — Dividend'},
    {'symbol': 'BRK-B',      'name': '버크셔 해서웨이B',    'shares': 5.254275, 'currency': 'USD', 'avg': 439.50,  'sector': 'Financials'},
    {'symbol': 'O',          'name': '리얼티인컴',           'shares': 6.711308, 'currency': 'USD', 'avg': 56.69,   'sector': 'Real Estate'},
    {'symbol': 'LLY',        'name': '일라이릴리',           'shares': 0.261988, 'currency': 'USD', 'avg': 855.32,  'sector': 'Health Care'},
    {'symbol': 'AMD',        'name': 'AMD',                  'shares': 0.054680, 'currency': 'USD', 'avg': 134.02,  'sector': 'Information Technology'},
    {'symbol': 'PLTR',       'name': '팔란티어',             'shares': 0.082555, 'currency': 'USD', 'avg': 167.38,  'sector': 'Information Technology'},
    {'symbol': 'AVGO',       'name': '브로드컴',             'shares': 3.035270, 'currency': 'USD', 'avg': 305.64,  'sector': 'Information Technology'},
    {'symbol': 'PAVE',       'name': '글로벌X 인프라 ETF',  'shares': 0.785363, 'currency': 'USD', 'avg': 47.55,   'sector': 'ETF — Infrastructure'},
    {'symbol': 'LRCX',       'name': '램리서치',             'shares': 0.066028, 'currency': 'USD', 'avg': 204.14,  'sector': 'Information Technology'},
    {'symbol': 'AMZN',       'name': '아마존',               'shares': 2.098517, 'currency': 'USD', 'avg': 200.54,  'sector': 'Consumer Discretionary'},
    {'symbol': 'VOO',        'name': '뱅가드 S&P500 ETF',   'shares': 3.021700, 'currency': 'USD', 'avg': 627.43,  'sector': 'ETF — Broad Market'},
    {'symbol': '005380.KS',  'name': '현대차2우B',           'shares': 1.0,      'currency': 'KRW', 'avg': 318000,  'sector': 'Consumer Discretionary'},
    {'symbol': '005930.KS',  'name': '삼성전자',             'shares': 3.0,      'currency': 'KRW', 'avg': 175500,  'sector': 'Information Technology'},
    {'symbol': '360750.KS',  'name': 'TIGER S&P500',         'shares': 440.0,    'currency': 'KRW', 'avg': 17145,   'sector': 'ETF — Broad Market'},
    {'symbol': '000660.KS',  'name': 'SK하이닉스',           'shares': 4.0,      'currency': 'KRW', 'avg': 488579,  'sector': 'Information Technology'},
]

MACRO_SENSITIVITY = {
    'Information Technology':  {'rates': -0.8, 'inflation': -0.4, 'oil': -0.1, 'dollar': -0.3},
    'Financials':              {'rates':  0.9, 'inflation':  0.3, 'oil':  0.1, 'dollar':  0.4},
    'Health Care':             {'rates': -0.2, 'inflation':  0.1, 'oil': -0.1, 'dollar': -0.2},
    'Consumer Discretionary':  {'rates': -0.6, 'inflation': -0.7, 'oil': -0.5, 'dollar':  0.1},
    'Consumer Staples':        {'rates': -0.2, 'inflation':  0.4, 'oil': -0.2, 'dollar':  0.0},
    'Energy':                  {'rates': -0.2, 'inflation':  0.6, 'oil':  1.0, 'dollar': -0.5},
    'Real Estate':             {'rates': -1.0, 'inflation': -0.2, 'oil':  0.0, 'dollar':  0.2},
    'Industrials':             {'rates': -0.3, 'inflation':  0.3, 'oil': -0.3, 'dollar': -0.3},
    'Materials':               {'rates': -0.2, 'inflation':  0.7, 'oil':  0.3, 'dollar': -0.4},
    'Utilities':               {'rates': -0.9, 'inflation':  0.2, 'oil': -0.2, 'dollar':  0.1},
    'Communication Services':  {'rates': -0.5, 'inflation': -0.2, 'oil': -0.1, 'dollar': -0.2},
}

MACRO_TOPICS = {
    'rates':     {'q': 'Federal Reserve interest rate monetary policy 2025', 'qkr': '연준 금리 통화정책 2025'},
    'inflation': {'q': 'inflation CPI consumer price index 2025',            'qkr': '인플레이션 물가 CPI 2025'},
    'oil':       {'q': 'oil price WTI crude energy outlook 2025',            'qkr': '유가 원유 에너지 2025'},
    'dollar':    {'q': 'US dollar DXY index forex strength 2025',            'qkr': '달러 환율 강달러 2025'},
}

MACRO_KEYWORDS = {
    'rates':     {'up': ['hike','raise','hawkish','tighten','higher rate','금리 인상','긴축'],
                  'down': ['cut','lower','dovish','pause','pivot','금리 인하','완화']},
    'inflation': {'up': ['hot','surge','above expect','물가 상승','cpi 상승','급등'],
                  'down': ['cool','ease','disinflation','below expect','물가 하락','인플레 둔화']},
    'oil':       {'up': ['surge','rally','supply cut','유가 상승','원유 급등','감산'],
                  'down': ['fall','drop','oversupply','유가 하락','원유 급락']},
    'dollar':    {'up': ['strong','surge','gains','strengthen','달러 강세','강달러'],
                  'down': ['weak','fall','decline','soften','달러 약세','약달러']},
}

SECTOR_KR = {
    'Information Technology': 'IT·반도체', 'Communication Services': '커뮤니케이션',
    'Consumer Discretionary': '경기소비재', 'Consumer Staples': '필수소비재',
    'Financials': '금융', 'Health Care': '헬스케어', 'Energy': '에너지',
    'Real Estate': '리츠', 'Industrials': '산업재', 'Materials': '원자재',
    'Utilities': '유틸리티', 'ETF — Broad Market': 'ETF(시장전체)',
    'ETF — Dividend': 'ETF(배당)', 'ETF — Infrastructure': 'ETF(인프라)',
}

# ── 유틸 ────────────────────────────────────────────────────
def fmt_ret(n):
    return f"+{n:.1f}%" if n >= 0 else f"{n:.1f}%"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(url, json={'chat_id': TG_CHAT, 'text': text, 'parse_mode': 'HTML'}, timeout=15)
    r.raise_for_status()
    return r.json()

# ── 가격 조회 ────────────────────────────────────────────────
def fetch_prices():
    symbols = [s['symbol'] for s in PORTFOLIO] + ['069500.KS', '229200.KS', 'USDKRW=X']
    try:
        data = yf.download(list(set(symbols)), period='5d', auto_adjust=True, progress=False)
        closes = data['Close']
        result = {}
        for sym in symbols:
            try:
                col = closes[sym] if sym in closes.columns else None
                if col is None:
                    continue
                vals = col.dropna()
                if len(vals) >= 2:
                    prev, curr = float(vals.iloc[-2]), float(vals.iloc[-1])
                    result[sym] = {'price': curr, 'changePct': (curr - prev) / prev * 100 if prev else 0}
                elif len(vals) == 1:
                    result[sym] = {'price': float(vals.iloc[-1]), 'changePct': 0}
            except Exception:
                pass
        return result
    except Exception as e:
        print(f"가격 조회 실패: {e}")
        return {}

# ── 매크로 RSS 분석 ──────────────────────────────────────────
def fetch_rss_titles(query, lang='en'):
    hl  = 'ko' if lang == 'ko' else 'en-US'
    gl  = 'KR' if lang == 'ko' else 'US'
    ced = 'KR:ko' if lang == 'ko' else 'US:en-US'
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl={hl}&gl={gl}&ceid={ced}"
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        root = ET.fromstring(r.content)
        return [item.findtext('title') or '' for item in root.findall('.//item')[:8]]
    except Exception:
        return []

def analyze_macro():
    regime = {}
    all_titles = {}
    for key, t in MACRO_TOPICS.items():
        titles = fetch_rss_titles(t['qkr'], 'ko') + fetch_rss_titles(t['q'], 'en')
        kw = MACRO_KEYWORDS[key]
        up = sum(1 for title in titles for w in kw['up']   if w.lower() in title.lower())
        dn = sum(1 for title in titles for w in kw['down'] if w.lower() in title.lower())
        regime[key]     = 0 if (up + dn) == 0 else (up - dn) / (up + dn)
        all_titles[key] = titles
    return regime, all_titles

# ── 공통 계산 ────────────────────────────────────────────────
def macro_fmt(key, r):
    dir_   = '↑' if r > 0.2 else ('↓' if r < -0.2 else '→')
    labels = {'rates': '금리', 'inflation': '인플레이션', 'oil': '유가', 'dollar': '달러'}
    status = {
        'rates':     '인상 기조' if r > 0.2 else ('인하 기조' if r < -0.2 else '중립'),
        'inflation': '상승 압력' if r > 0.2 else ('둔화 중'   if r < -0.2 else '안정적'),
        'oil':       '가격 상승' if r > 0.2 else ('가격 하락' if r < -0.2 else '보합'),
        'dollar':    '강세'      if r > 0.2 else ('약세'      if r < -0.2 else '보합'),
    }[key]
    return f"{dir_} {labels[key]}: {status}"

def calc_portfolio(prices, usd_krw=1450):
    cost_basis, current_val, sector_val = 0, 0, {}
    for s in PORTFOLIO:
        p         = prices.get(s['symbol'], {}).get('price', s['avg'])
        fx        = usd_krw if s['currency'] == 'USD' else 1
        cost_basis  += s['avg'] * s['shares'] * fx
        current_val += p        * s['shares'] * fx
        sector_val[s['sector']] = sector_val.get(s['sector'], 0) + p * s['shares'] * fx
    port_ret   = (current_val - cost_basis) / cost_basis * 100 if cost_basis else 0
    total      = sum(sector_val.values()) or 1
    sector_pct = sorted(
        [{'name': k, 'pct': round(v / total * 100)} for k, v in sector_val.items()],
        key=lambda x: -x['pct']
    )[:3]
    return port_ret, sector_pct

def calc_macro_impact(regime):
    impacts = []
    for s in PORTFOLIO:
        sens   = MACRO_SENSITIVITY.get(s['sector'], {k: 0 for k in regime})
        impact = sum(sens.get(k, 0) * v for k, v in regime.items()) / max(len(regime), 1)
        impacts.append({'sym': s['symbol'].replace('.KS', ''), 'name': s['name'], 'impact': impact})
    impacts.sort(key=lambda x: -x['impact'])
    return (
        [x['sym'] for x in impacts if x['impact'] >  0.05][:3],
        [x['sym'] for x in impacts if x['impact'] < -0.05][:3],
    )

# ── 전략 생성 ────────────────────────────────────────────────
def morning_strategy(regime, sector_pct):
    lines, r = [], regime
    top = sector_pct[0] if sector_pct else None

    if r.get('rates', 0) < -0.3:
        lines.append('금리 인하 기조 — AI 반도체·성장주 모멘텀 유리')
    elif r.get('rates', 0) > 0.3:
        lines.append('금리 인상 기조 — 배당주·가치주 중심 대응')
    else:
        lines.append('AI 반도체 모멘텀 유지')

    if top and top['pct'] > 40:
        lines.append(f"{SECTOR_KR.get(top['name'], top['name'])} 집중도 {top['pct']}% — 분산 검토")

    if r.get('oil', 0) > 0.3:
        lines.append('에너지 섹터 모니터링 — 유가 상승 지속')
    elif r.get('oil', 0) < -0.3:
        lines.append('유가 하락 — 소비재·운송 비용 감소 수혜')
    else:
        lines.append('에너지 섹터 중립 유지')

    return '\n'.join(lines[:3])

def us_strategy(regime):
    lines, r = [], regime

    if r.get('rates', 0) > 0.3:
        lines.append('금리 민감 섹터 주의 — 성장주·리츠 방어적 접근')
    elif r.get('rates', 0) < -0.3:
        lines.append('금리 인하 기조 — 성장주·리츠 유리')

    it_mood = r.get('rates', 0)
    if it_mood <= 0:
        lines.append('AI 반도체 모멘텀 유지 — 기술주 집중 관찰')

    if r.get('dollar', 0) > 0.3:
        lines.append('강달러 — 다국적 기업 환차손 주의')
    elif r.get('oil', 0) > 0.3:
        lines.append('에너지 섹터 관찰 — 유가 상승')

    if not lines:
        lines.append('매크로 리스크 낮음 — 전반적 중립 대응')

    return '\n'.join(lines[:3])

# ── 08:00 Morning Report ─────────────────────────────────────
def morning_report():
    print("📊 Morning Report 생성 중...")
    today  = datetime.now(KST).strftime('%-m월 %-d일 (%a)')
    prices = fetch_prices()
    regime, macro_titles = analyze_macro()

    usd_krw             = prices.get('USDKRW=X', {}).get('price', 1450)
    port_ret, sec_pct   = calc_portfolio(prices, usd_krw)
    benefits, risks     = calc_macro_impact(regime)

    # 지수
    voo     = prices.get('VOO',      {})
    kospi   = prices.get('069500.KS',{})
    sp_ret  = fmt_ret(voo.get('changePct', 0))   if voo   else '—'
    ks_ret  = fmt_ret(kospi.get('changePct', 0)) if kospi else '—'

    # 상위 종목 (총수익률 기준 TOP 3)
    stock_rets = sorted([
        {'sym': s['symbol'].replace('.KS',''), 'name': s['name'],
         'ret': (prices.get(s['symbol'],{}).get('price', s['avg']) - s['avg']) / s['avg'] * 100}
        for s in PORTFOLIO if s['symbol'] in prices
    ], key=lambda x: -x['ret'])[:3]

    # 헤드라인
    headlines = []
    for titles in macro_titles.values():
        headlines += [t for t in titles if t][:2]
    headlines = headlines[:3]

    msg = '\n'.join(filter(None, [
        f"📊 <b>Morning Macro Report</b> | {today}",
        "",
        "📈 <b>Performance</b>",
        f"포트  {fmt_ret(port_ret)}",
        f"S&P500  {sp_ret}",
        f"KOSPI  {ks_ret}",
        "",
        "📌 <b>오늘 전략</b>",
        morning_strategy(regime, sec_pct),
        "",
        "📈 <b>매크로</b>",
        *[macro_fmt(k, regime.get(k, 0)) for k in ['rates','inflation','oil','dollar']],
        "",
        "📊 <b>섹터 집중도</b>",
        *[f"{SECTOR_KR.get(x['name'], x['name'])}  {x['pct']}%" for x in sec_pct],
        "",
        "📊 <b>포트 영향</b>",
        f"수혜: {' · '.join(benefits)}" if benefits else "수혜: —",
        f"위험: {' · '.join(risks)}"    if risks    else "위험: —",
        "",
        "🥇 <b>상위 종목</b>",
        *[f"{x['sym']}  {fmt_ret(x['ret'])}" for x in stock_rets],
        "",
        "📰 <b>핵심 뉴스</b>",
        *([f"• {h}" for h in headlines] if headlines else ["• 뉴스 없음"]),
        "",
        "<i>🤖 stock.html 자동 리포트</i>",
    ]))

    result = send_telegram(msg)
    print(f"✅ 전송 완료: {result.get('ok')}")

# ── 15:00 Pre-US Report ──────────────────────────────────────
def preus_report():
    print("📊 Pre-US Report 생성 중...")
    today  = datetime.now(KST).strftime('%-m월 %-d일 (%a)')
    prices = fetch_prices()
    regime, macro_titles = analyze_macro()

    # 한국 지수
    kospi  = prices.get('069500.KS', {})
    kosdaq = prices.get('229200.KS', {})
    ks_ret  = fmt_ret(kospi.get('changePct', 0))  if kospi  else '—'
    kq_ret  = fmt_ret(kosdaq.get('changePct', 0)) if kosdaq else '—'

    # 포트폴리오 변화 (등락 절댓값 TOP 5)
    port_changes = sorted([
        {'name': s['name'], 'pct': prices[s['symbol']]['changePct']}
        for s in PORTFOLIO if s['symbol'] in prices
    ], key=lambda x: abs(x['pct']), reverse=True)[:5]

    # 미국장 관찰 종목 (USD 종목 중 등락 절댓값 TOP 3)
    us_watch = sorted([
        {'sym': s['symbol'], 'pct': prices[s['symbol']]['changePct']}
        for s in PORTFOLIO if s['currency'] == 'USD' and s['symbol'] in prices
    ], key=lambda x: abs(x['pct']), reverse=True)[:3]

    # 미국 뉴스 (영문 기사 우선)
    us_news = []
    for titles in macro_titles.values():
        us_news += [t for t in titles if t and all(ord(c) < 0x3000 for c in t)][:2]
    us_news = us_news[:3]

    msg = '\n'.join(filter(None, [
        f"📊 <b>Pre-US Market Report</b> | {today}",
        "",
        "📈 <b>한국 시장 결과</b>",
        f"KOSPI  {ks_ret}",
        f"KOSDAQ  {kq_ret}",
        "",
        "📊 <b>포트폴리오 변화</b>",
        *([f"{x['name']}  {fmt_ret(x['pct'])}" for x in port_changes]
          if port_changes else ["데이터 없음 (가격 조회 실패)"]),
        "",
        "📌 <b>미국장 전략</b>",
        us_strategy(regime),
        "",
        "👀 <b>미국장 관찰 종목</b>",
        *([x['sym'] for x in us_watch] if us_watch else ["—"]),
        "",
        "📰 <b>주요 뉴스</b>",
        *([f"• {h}" for h in us_news] if us_news else ["• 뉴스 없음"]),
        "",
        "<i>🤖 stock.html 자동 리포트</i>",
    ]))

    result = send_telegram(msg)
    print(f"✅ 전송 완료: {result.get('ok')}")

# ── 🚨 Macro Alert ───────────────────────────────────────────
def macro_alert():
    """
    조건 기반 즉시 알림.
    하루 중복 방지: GitHub Actions cache 없이 날짜+조건 키를 파일로 저장.
    """
    import json, pathlib

    STATE_FILE = pathlib.Path('/tmp/macro_alert_state.json')
    today_str  = datetime.now(KST).strftime('%Y-%m-%d')

    # 상태 로드 (당일 이미 발송된 알림 키 목록)
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    else:
        state = {}

    sent_today = set(state.get(today_str, []))

    # ── 가격 조회 ──
    alert_syms = ['NVDA', '^VIX', '^TNX']   # TNX = 미국 10년 국채 수익률 ×10
    try:
        raw = yf.download(alert_syms, period='5d', auto_adjust=True, progress=False)
        closes = raw['Close']
    except Exception as e:
        print(f"Alert 가격 조회 실패: {e}")
        return

    def get_change(sym):
        try:
            col  = closes[sym].dropna()
            if len(col) < 2:
                return None
            prev, curr = float(col.iloc[-2]), float(col.iloc[-1])
            return (curr - prev) / prev * 100 if prev else None
        except Exception:
            return None

    alerts = []

    # ── 조건 1: NVDA ±5% ──
    nvda_chg = get_change('NVDA')
    if nvda_chg is not None and abs(nvda_chg) >= 5.0:
        key = f'NVDA_{today_str}'
        if key not in sent_today:
            direction = '급등' if nvda_chg > 0 else '급락'
            impact    = 'AI 반도체 섹터 모멘텀 급등\n반도체 종목 변동성 확대 가능' if nvda_chg > 0 \
                        else 'AI 반도체 섹터 하락 압력\n관련 종목 손절·비중 축소 검토'
            alerts.append({
                'key': key,
                'msg': f"🚨 <b>Macro Alert</b>\n\nNVDA {fmt_ret(nvda_chg)} ({direction})\n\n{impact}",
            })

    # ── 조건 2: US10Y +0.10%p 이상 ──
    # ^TNX 는 수익률×10 → 실제 변화량 = changePct/10 ×10 = changePct (basis points 개념)
    # yfinance ^TNX 종가 단위: 퍼센트 × 10 → 실제 %p 변화 = (curr - prev) / 10
    try:
        tnx_col  = closes['^TNX'].dropna()
        if len(tnx_col) >= 2:
            tnx_prev, tnx_curr = float(tnx_col.iloc[-2]), float(tnx_col.iloc[-1])
            tnx_chg_pp = (tnx_curr - tnx_prev) / 10   # %p 변화
            if tnx_chg_pp >= 0.10:
                key = f'US10Y_{today_str}'
                if key not in sent_today:
                    alerts.append({
                        'key': key,
                        'msg': f"🚨 <b>Macro Alert</b>\n\nUS10Y +{tnx_chg_pp:.2f}%p\n\n금리 상승 압력\n성장주 및 리츠 섹터 주의",
                    })
    except Exception:
        pass

    # ── 조건 3: VIX +15% ──
    vix_chg = get_change('^VIX')
    if vix_chg is not None and vix_chg >= 15.0:
        key = f'VIX_{today_str}'
        if key not in sent_today:
            alerts.append({
                'key': key,
                'msg': f"🚨 <b>Macro Alert</b>\n\nVIX {fmt_ret(vix_chg)}\n\n시장 공포 지수 상승\n리스크 자산 변동성 확대 가능",
            })

    # ── 전송 ──
    if not alerts:
        print("✅ 알림 조건 없음")
        return

    newly_sent = []
    for a in alerts:
        try:
            result = send_telegram(a['msg'])
            if result.get('ok'):
                print(f"🚨 Alert 전송: {a['key']}")
                newly_sent.append(a['key'])
        except Exception as e:
            print(f"Alert 전송 실패 ({a['key']}): {e}")

    # ── 상태 저장 ──
    state[today_str] = list(sent_today | set(newly_sent))
    STATE_FILE.write_text(json.dumps(state))


# ── 실행 ─────────────────────────────────────────────────────
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'morning'
    if   mode == 'morning': morning_report()
    elif mode == 'preus':   preus_report()
    elif mode == 'alert':   macro_alert()
    else:
        print(f"알 수 없는 모드: {mode}  (morning / preus / alert)")
        sys.exit(1)
