#!/usr/bin/env python3
"""
durenodes.com 정적 페이지 생성기.

_style.css 와 아래 CONTENT 를 단일 원본으로 삼아 index.html(EN) 과 ko/index.html(KO) 을
생성합니다. 배포에는 빌드가 필요 없습니다 — 결과물을 커밋하면 Cloudflare Pages 가 그대로 서빙합니다.

    python3 _build.py

수정할 때: 문구는 CONTENT, 스타일은 _style.css. HTML 을 직접 고치지 마세요. 덮어써집니다.
"""
import os, re, json, pathlib

HERE = pathlib.Path(__file__).parent
SITE = "https://durenodes.com"

# ── 실측 데이터 ────────────────────────────────────────────────────────────────
# 온체인에서 확인한 값만 씁니다. 갱신 시 출처를 함께 확인하세요.
DATA = dict(
    as_of="2026-08-07",
    networks="3",
    uptime="99.82",
    slashing="0",
    services_live="0", services_total="10",
    tia_stake="195.00", tia_comm="20.00", tia_missed="18 / 10,000", tia_since="2026-07-31",
    mocha_stake="2.95", mocha_comm="20.00", mocha_since="2026-07-31",
    atom_stake="1.00", atom_comm="5.00", atom_missed="0", atom_since="2026-08-05",
    valoper="celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq",
    contact="contact@durenodes.com",
    security="security@durenodes.com",
    github="https://github.com/durenodes",
    x="https://x.com/durenodes",
    telegram="https://t.me/durenodes",
    mintscan="https://www.mintscan.io/celestia/validators/celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq",
    celenium="https://celenium.io/validator/celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq",
    keplr="https://wallet.keplr.app/chains/celestia?modal=validator&chain=celestia&validator_address=celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq",
)

SERVICES = [
    ("Public RPC",       "rpc",      "2026 Q4"),
    ("Snapshot",         "snapshot", "2026 Q4"),
    ("Install Guide",    "guide",    "2026 Q4"),
    ("Public API",       "api",      "2026 Q4"),
    ("Public gRPC",      "grpc",     "2026 Q4"),
    ("State-Sync",       "statesync","2027 Q1"),
    ("Seed Node",        "seed",     "2027 Q1"),
    ("Addrbook",         "addrbook", "2027 Q1"),
    ("Archive Snapshot", "archive",  None),
    ("IBC Relayer",      "relayer",  None),
]

CONTENT = {
"en": dict(
    lang="en", other="ko", other_label="한국어", other_href="/ko/",
    title="DURE — Celestia & Cosmos Hub Validator | Minimum Commission, Published Costs",
    desc="DURE (doo-reh) runs Celestia and Cosmos Hub validators at each chain's minimum commission, publishes fee income alongside infrastructure cost, and never deletes an incident record.",
    og_desc="Shared work, settled fairly. Each chain's minimum commission, costs published, incidents never deleted.",
    kicker="SHARED WORK, SETTLED FAIRLY · 함께 짓고, 낸 만큼 나눈다",
    h1="One chain at a time, run properly",
    lede=('We started a Celestia mainnet validator on 31 July 2026. That is not long. '
          'So what we can show you is not a track record but <b>how we keep one</b> — '
          'uptime and outages written down as they happen, and public services announced '
          'with the order and dates before they open. Everything we open is '
          '<a href="#services">free to use</a>.'),
    nav=dict(networks="NETWORKS", services="SERVICES", status="STATUS", log="LOG", delegate="DELEGATE"),
    stat_networks="NETWORKS", stat_uptime="UPTIME · LAST 10K BLOCKS",
    stat_slashing="SLASHING · JAIL", stat_services="PUBLIC SERVICES · LIVE",
    cta_delegate="DELEGATE", cta_services="Service schedule", cta_status="STATUS",
    sec_networks="Networks we run today",
    net_mainnet="MAINNET", net_testnet="TESTNET",
    net_stake="stake", net_uptime="uptime", net_validator="validator", net_running="running",
    net_next="Next network", net_planned="PLANNED",
    net_next_desc="We add one only after the network we already hold is stable",
    sec_services="The order and dates, published before they open · all free",
    svc=dict(rpc=("Public RPC","Open RPC with no request limits"),
             snapshot=("Snapshot","Pruned snapshot refreshed every 6 hours"),
             guide=("Install Guide","Node setup scripts and documentation"),
             api=("Public API","REST endpoint"),
             grpc=("Public gRPC","gRPC endpoint"),
             statesync=("State-Sync","RPC and trust hash for fast sync"),
             seed=("Seed Node","Peer discovery"),
             addrbook=("Addrbook","Current peer address book"),
             archive=("Archive Snapshot","Archival node snapshot"),
             relayer=("IBC Relayer","Cross-chain packet relay")),
    svc_planned="PLANNED", svc_tbd="DATE TBD",
    sec_status="Only values you can verify on-chain · as of {as_of}",
    th=dict(network="NETWORK", status="STATUS", stake="STAKE", commission="COMMISSION", missed="MISSED", since="SINCE"),
    note=('<b>We charge each chain\'s minimum commission.</b> Celestia enforces a 20% floor at '
          'the network level; Cosmos Hub enforces 5%. We sit on both floors. The numbers differ '
          'because the rules differ, not the policy — and every value above can be verified on-chain.'
          '<br><br><b>Fee income and infrastructure cost are not published yet.</b> We have not been '
          'running long enough for a settlement period worth showing. As soon as the first one closes '
          'we will put income and cost side by side, and leave the breakdown in the repository. '
          'Not inventing numbers is the operating principle of this page.'),
    foot_meta=["MIN = the lowest commission the chain allows",
               "MISSED = within the last 10,000-block window",
               "no jail history · no slashing"],
    sec_log="We write down outages and what we did about them. We do not delete them.",
    log_empty="NO INCIDENTS ON RECORD",
    log_empty_p=("Since we started on 31 July 2026 there has been no jail and no slashing. "
                 "That is not a boast — it means the time has been short. Outages happen eventually, "
                 "and when they do the cause and the fix go here. We do not delete them."),
    sec_delegate="Delegation · what you put in comes back in proportion",
    val_label="CELESTIA VALOPER",
    val_min="· NETWORK MINIMUM",
    val_since="SINCE",
    btn_keplr="Delegate with Keplr",
    story=('<b>DURE (두레, doo-reh)</b> was a village labour commons in Joseon-era Korea. '
           'No one owned it. A ledger recorded how many days each household put in, and at the '
           'settlement each was paid back in proportion. A village had kept by custom the structure '
           'that blockchains now try to write in code — so we took the name as it is.'),
    copy="© 2026 DURE · Shared work, settled fairly",
    links=dict(github="GITHUB", x="X", telegram="TELEGRAM", contact="CONTACT", security="SECURITY"),
),
"ko": dict(
    lang="ko", other="en", other_label="English", other_href="/",
    title="DURE 두레 — 셀레스티아·코스모스 허브 밸리데이터 | 최소 수수료, 비용 공개",
    desc="DURE(두레)는 셀레스티아와 코스모스 허브 밸리데이터를 각 체인이 허용하는 최소 수수료로 운영하고, 수수료 수입과 인프라 비용을 함께 공개하며, 장애 기록을 지우지 않습니다.",
    og_desc="함께 짓고, 낸 만큼 나눈다 · 각 체인이 허용하는 최소 수수료로 운영하고, 수입과 비용을 함께 공개합니다.",
    kicker="함께 짓고, 낸 만큼 나눈다 · SHARED WORK, SETTLED FAIRLY",
    h1="체인 하나부터 제대로 운영합니다",
    lede=('2026년 7월 31일 셀레스티아 메인넷 밸리데이터를 시작했습니다. 아직 짧습니다. '
          '그래서 지금 보여드릴 수 있는 건 성과가 아니라 <b>기록하는 방식</b>입니다. '
          '가동률도 장애도 있는 그대로 적고, 퍼블릭 서비스는 여는 순서와 시점을 미리 공개합니다. '
          '열린 서비스는 <a href="#services">모두 무료</a>로 씁니다.'),
    nav=dict(networks="NETWORKS", services="SERVICES", status="STATUS", log="LOG", delegate="DELEGATE"),
    stat_networks="NETWORKS", stat_uptime="UPTIME · 최근 10K 블록",
    stat_slashing="SLASHING · JAIL", stat_services="PUBLIC SERVICES · 제공 중",
    cta_delegate="DELEGATE", cta_services="서비스 공개 일정", cta_status="STATUS",
    sec_networks="지금 운영하는 네트워크",
    net_mainnet="메인넷", net_testnet="테스트넷",
    net_stake="위임", net_uptime="가동률", net_validator="밸리데이터", net_running="운영 중",
    net_next="다음 네트워크", net_planned="예정",
    net_next_desc="지금 맡은 네트워크가 안정된 뒤에 늘립니다",
    sec_services="여는 순서와 시점을 그대로 공개합니다 · 모두 무료",
    svc=dict(rpc=("Public RPC","요청 제한 없는 공개 RPC"),
             snapshot=("Snapshot","6시간마다 갱신하는 프룬 스냅샷"),
             guide=("설치 가이드","노드 구축 스크립트와 설명서"),
             api=("Public API","REST 엔드포인트"),
             grpc=("Public gRPC","gRPC 엔드포인트"),
             statesync=("State-Sync","빠른 동기화를 위한 RPC와 트러스트 해시"),
             seed=("Seed Node","피어 디스커버리"),
             addrbook=("Addrbook","최신 피어 주소록"),
             archive=("Archive Snapshot","아카이벌 노드 스냅샷"),
             relayer=("IBC Relayer","체인 간 패킷 중계")),
    svc_planned="예정", svc_tbd="시점 미정",
    sec_status="온체인에서 그대로 확인할 수 있는 값만 적습니다 · {as_of} 기준",
    th=dict(network="NETWORK", status="STATUS", stake="STAKE", commission="COMMISSION", missed="MISSED", since="SINCE"),
    note=('<b>수수료는 각 체인이 허용하는 최소값으로 받습니다.</b> 셀레스티아는 네트워크가 20%를 '
          '최소로 강제하고, 코스모스 허브는 5%입니다. 두 곳 모두 그 하한에 맞춰 두었습니다. '
          '체인마다 숫자가 다른 건 정책이 달라서가 아니라 규칙이 다르기 때문이고, 위 표의 값은 '
          '온체인에서 그대로 확인할 수 있습니다.'
          '<br><br><b>수수료 수입과 인프라 비용은 아직 공개하지 않습니다.</b> 운영을 시작한 지 '
          '얼마 되지 않아 공개할 만한 정산 주기가 쌓이지 않았습니다. 첫 정산이 끝나는 대로 수입과 '
          '비용을 나란히 올리고, 명세는 저장소에 그대로 둡니다. 없는 숫자를 지어내지 않는 것이 '
          '이 페이지의 원칙입니다.'),
    foot_meta=["MIN = 해당 체인이 허용하는 최소 수수료",
               "MISSED = 최근 10,000블록 윈도우 기준",
               "jail 이력 없음 · 슬래싱 없음"],
    sec_log="장애와 조치 내역을 그대로 남깁니다. 지우지 않습니다.",
    log_empty="기록된 장애 없음",
    log_empty_p=("운영을 시작한 2026년 7월 31일 이후 jail되거나 슬래싱된 이력이 없습니다. "
                 "다만 이건 자랑이 아니라 아직 시간이 짧다는 뜻입니다. 장애는 결국 생기고, "
                 "생기면 원인과 조치를 여기에 그대로 적습니다. 지우지 않습니다."),
    sec_delegate="위임 안내 · 기여한 만큼 그대로 돌아갑니다",
    val_label="CELESTIA VALOPER",
    val_min="· 네트워크 최소",
    val_since="SINCE",
    btn_keplr="Keplr로 위임",
    story=('<b>DURE(두레)</b>는 조선 시대 마을 단위의 공동 노동 조직입니다. 주인이 따로 없었고, '
           '누가 며칠을 냈는지 장부에 적었고, 낸 만큼 돌려받았습니다. 블록체인이 코드로 만들려는 '
           '구조를 마을이 이미 관습으로 지켜온 셈이라, 그 이름을 그대로 가져왔습니다.'),
    copy="© 2026 DURE · 함께 짓고, 낸 만큼 나눈다",
    links=dict(github="GITHUB", x="X", telegram="TELEGRAM", contact="CONTACT", security="SECURITY"),
),
}

MARK = '''<svg width="19" height="26" viewBox="52 32 133 184" aria-hidden="true" style="display:block">
          <rect x="55" y="36" width="22" height="22" fill="#2BB673"></rect>
          <rect x="58" y="58" width="16" height="154" fill="#E7E3D6"></rect>
          <path d="M74,68 L182,68 L158,108 L182,148 L74,148 Z" fill="#E7E3D6"></path>
          <g fill="#0D0F0C"><rect x="92" y="84" width="18" height="48"></rect><rect x="128" y="84" width="18" height="48"></rect></g>
        </svg>'''


def jsonld(c):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "DURE",
        "alternateName": ["DURE Nodes", "두레"],
        "url": SITE + "/",
        "logo": SITE + "/icon-256.png",
        "description": c["desc"],
        "sameAs": [DATA["github"], DATA["x"], DATA["telegram"]],
        "contactPoint": [
            {"@type": "ContactPoint", "contactType": "customer support", "email": DATA["contact"]},
            {"@type": "ContactPoint", "contactType": "security", "email": DATA["security"]},
        ],
    }, ensure_ascii=False, indent=2)


def build(key):
    c = CONTENT[key]
    css = (HERE / "_style.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S).strip()
    d = DATA
    canonical = SITE + ("/ko/" if key == "ko" else "/")
    depth = "../" if key == "ko" else ""

    svc_cards = "\n".join(
        f'''          <div class="svc">
            <span class="svc-n">{c["svc"][sid][0]}</span>
            <span class="svc-d">{c["svc"][sid][1]}</span>
            <span class="svc-s">{(when + " " + c["svc_planned"]) if when else c["svc_tbd"]}</span>
          </div>'''
        for _, sid, when in SERVICES)

    links = "\n".join([
        f'        <a href="{d["github"]}" rel="me noopener" target="_blank">{c["links"]["github"]}</a>',
        f'        <a href="{d["x"]}" rel="me noopener" target="_blank">{c["links"]["x"]}</a>',
        f'        <a href="{d["telegram"]}" rel="me noopener" target="_blank">{c["links"]["telegram"]}</a>',
        f'        <a href="mailto:{d["contact"]}">{c["links"]["contact"]}</a>',
        f'        <a href="mailto:{d["security"]}">{c["links"]["security"]}</a>',
    ])

    html = f'''<!DOCTYPE html>
<html lang="{c["lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{c["title"]}</title>
<meta name="description" content="{c["desc"]}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{SITE}/">
<link rel="alternate" hreflang="ko" href="{SITE}/ko/">
<link rel="alternate" hreflang="x-default" href="{SITE}/">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/icon-256.png">
<meta name="theme-color" content="#0D0F0C">
<meta property="og:type" content="website">
<meta property="og:site_name" content="DURE">
<meta property="og:locale" content="{"ko_KR" if key == "ko" else "en_US"}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{c["title"]}">
<meta property="og:description" content="{c["og_desc"]}">
<meta property="og:image" content="{SITE}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@durenodes">
<meta name="twitter:title" content="{c["title"]}">
<meta name="twitter:description" content="{c["og_desc"]}">
<meta name="twitter:image" content="{SITE}/og.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@300;400;500;600&display=swap" rel="stylesheet">
<script type="application/ld+json">
{jsonld(c)}
</script>
<style>
{css}
</style>
</head>
<body>

<header class="hdr">
  <div class="wrap hdr-in">
    <a class="brand" href="#top" aria-label="DURE">
      {MARK}
      <b>DURE</b>
    </a>
    <nav class="nav" aria-label="Sections">
      <a href="#networks">{c["nav"]["networks"]}</a>
      <a href="#services">{c["nav"]["services"]}</a>
      <a href="#status">{c["nav"]["status"]}</a>
      <a href="#log">{c["nav"]["log"]}</a>
      <a href="#delegate" class="nav-key">{c["nav"]["delegate"]}</a>
    </nav>
    <a class="lang" href="{c["other_href"]}" hreflang="{c["other"]}" rel="alternate">{c["other_label"]}</a>
  </div>
</header>

<main id="top">

  <div class="hero">
    <div class="wrap">
      <div class="kicker">{c["kicker"]}</div>
      <h1>{c["h1"]}</h1>
      <p class="lede">{c["lede"]}</p>

      <div class="stats">
        <div class="stat"><div class="stat-n">{d["networks"]}</div><div class="stat-l">{c["stat_networks"]}</div></div>
        <div class="stat"><div class="stat-n">{d["uptime"]}<small>%</small></div><div class="stat-l">{c["stat_uptime"]}</div></div>
        <div class="stat"><div class="stat-n">{d["slashing"]}</div><div class="stat-l">{c["stat_slashing"]}</div></div>
        <div class="stat"><div class="stat-n">{d["services_live"]}<small> / {d["services_total"]}</small></div><div class="stat-l">{c["stat_services"]}</div></div>
      </div>

      <div class="cta">
        <a href="#delegate" class="btn btn-solid"><span>{c["cta_delegate"]}</span><span class="dot"></span></a>
        <a href="#services" class="btn">{c["cta_services"]}</a>
        <a href="#status" class="btn">{c["cta_status"]}</a>
      </div>
    </div>
  </div>

  <section id="networks">
    <div class="wrap">
      <div class="sec-head"><h2>NETWORKS</h2><span class="sec-sub">{c["sec_networks"]}</span></div>
      <div class="grid-2">
        <div class="net live">
          <div class="net-top"><span class="tick">TIA</span><span class="net-name">Celestia</span>
            <span class="tag on"><span class="blink"></span>ACTIVE</span></div>
          <div class="net-meta"><span>{c["net_mainnet"]}</span><span>{c["net_stake"]} <b>{d["tia_stake"]} TIA</b></span><span>{c["net_uptime"]} <b>{d["uptime"]}%</b></span></div>
        </div>
        <div class="net test">
          <div class="net-top"><span class="tick">MCH</span><span class="net-name">Celestia Mocha</span>
            <span class="tag warn">{c["net_testnet"]}</span></div>
          <div class="net-meta"><span>MOCHA-4</span><span>{c["net_validator"]} <b>{c["net_running"]}</b></span></div>
        </div>
        <div class="net test">
          <div class="net-top"><span class="tick">ATOM</span><span class="net-name">Cosmos Hub</span>
            <span class="tag warn">{c["net_testnet"]}</span></div>
          <div class="net-meta"><span>PROVIDER</span><span>{c["net_validator"]} <b>{c["net_running"]}</b></span></div>
        </div>
        <div class="net next">
          <div class="net-top"><span class="tick">—</span><span class="net-name" style="color:var(--muted)">{c["net_next"]}</span>
            <span class="tag">{c["net_planned"]}</span></div>
          <div class="net-meta">{c["net_next_desc"]}</div>
        </div>
      </div>
    </div>
  </section>

  <div class="wrap"><div class="rule"></div></div>

  <section id="services">
    <div class="wrap">
      <div class="sec-head"><h2>PUBLIC SERVICES</h2><span class="sec-sub">{c["sec_services"]}</span></div>
      <div class="grid-svc">
{svc_cards}
      </div>
    </div>
  </section>

  <div class="wrap"><div class="rule"></div></div>

  <section id="status">
    <div class="wrap">
      <div class="sec-head"><h2>STATUS</h2><span class="sec-sub">{c["sec_status"].format(as_of=d["as_of"])}</span></div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>{c["th"]["network"]}</th><th>{c["th"]["status"]}</th>
            <th class="num">{c["th"]["stake"]}</th><th class="num">{c["th"]["commission"]}</th>
            <th class="num">{c["th"]["missed"]}</th><th class="num">{c["th"]["since"]}</th>
          </tr></thead>
          <tbody>
            <tr><td>celestia-mainnet</td><td class="ok">BONDED</td><td class="num">{d["tia_stake"]} TIA</td>
                <td class="num">{d["tia_comm"]}%<span class="min-badge">MIN</span></td><td class="num">{d["tia_missed"]}</td><td class="num">{d["tia_since"]}</td></tr>
            <tr><td>mocha-4</td><td class="ok">BONDED</td><td class="num">{d["mocha_stake"]} TIA</td>
                <td class="num">{d["mocha_comm"]}%<span class="min-badge">MIN</span></td><td class="num">—</td><td class="num">{d["mocha_since"]}</td></tr>
            <tr><td>cosmoshub-provider</td><td class="ok">BONDED</td><td class="num">{d["atom_stake"]} ATOM</td>
                <td class="num">{d["atom_comm"]}%<span class="min-badge">MIN</span></td><td class="num">{d["atom_missed"]}</td><td class="num">{d["atom_since"]}</td></tr>
          </tbody>
        </table>
      </div>
      <div class="note">{c["note"]}</div>
      <div class="foot-meta">{"".join(f"<span>{m}</span>" for m in c["foot_meta"])}</div>
    </div>
  </section>

  <div class="wrap"><div class="rule"></div></div>

  <section id="log">
    <div class="wrap">
      <div class="sec-head"><h2>INCIDENT LOG</h2><span class="sec-sub">{c["sec_log"]}</span></div>
      <div class="empty">
        <div class="empty-t">{c["log_empty"]}</div>
        <p>{c["log_empty_p"]}</p>
      </div>
    </div>
  </section>

  <div class="wrap"><div class="rule"></div></div>

  <section id="delegate">
    <div class="wrap">
      <div class="sec-head"><h2>DELEGATE</h2><span class="sec-sub">{c["sec_delegate"]}</span></div>
      <div class="val-card">
        <b class="val-label">{c["val_label"]}</b>
        <div class="val-addr">{d["valoper"]}</div>
        <div class="val-meta">
          <span>COMMISSION {d["tia_comm"]}% <b>{c["val_min"]}</b></span>
          <span>MAX 25.00%</span><span>MAX CHANGE 1.00%</span><span>{c["val_since"]} {d["tia_since"]}</span>
        </div>
      </div>
      <div class="cta">
        <a href="{d["keplr"]}" target="_blank" rel="noopener" class="btn btn-solid"><span>{c["btn_keplr"]}</span><span class="dot"></span></a>
        <a href="{d["mintscan"]}" target="_blank" rel="noopener" class="btn">Mintscan</a>
        <a href="{d["celenium"]}" target="_blank" rel="noopener" class="btn">Celenium</a>
      </div>
    </div>
  </section>

</main>

<footer>
  <div class="wrap foot">
    <div class="foot-story">
      {c["story"]}
      <div class="copy">{c["copy"]}</div>
    </div>
    <div class="foot-links">
{links}
    </div>
  </div>
</footer>

</body>
</html>
'''
    return html


def main():
    (HERE / "index.html").write_text(build("en"), encoding="utf-8")
    (HERE / "ko").mkdir(exist_ok=True)
    (HERE / "ko" / "index.html").write_text(build("ko"), encoding="utf-8")

    (HERE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    (HERE / "sitemap.xml").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>{SITE}/</loc>
    <lastmod>{DATA["as_of"]}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE}/"/>
    <xhtml:link rel="alternate" hreflang="ko" href="{SITE}/ko/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/"/>
  </url>
  <url>
    <loc>{SITE}/ko/</loc>
    <lastmod>{DATA["as_of"]}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE}/"/>
    <xhtml:link rel="alternate" hreflang="ko" href="{SITE}/ko/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/"/>
  </url>
</urlset>
''', encoding="utf-8")

    for f in ("index.html", "ko/index.html", "robots.txt", "sitemap.xml"):
        print(f"  {f:<20} {os.path.getsize(HERE / f):>7,} bytes")


if __name__ == "__main__":
    main()
