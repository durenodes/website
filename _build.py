#!/usr/bin/env python3
"""
durenodes.com 정적 페이지 생성기.

_style.css 와 아래 CONTENT 를 단일 원본으로 삼아 index.html(EN) 과 ko/index.html(KO) 을
생성합니다. 배포에는 빌드가 필요 없습니다 — 결과물을 커밋하면 Cloudflare Pages 가 그대로 서빙합니다.

    python3 _build.py

수정할 때: 문구는 CONTENT, 스타일은 _style.css. HTML 을 직접 고치지 마세요. 덮어써집니다.
"""
import os, re, json, pathlib, sys, datetime, urllib.request, concurrent.futures as _cf

HERE = pathlib.Path(__file__).parent
SITE = "https://durenodes.com"

# ── 실측 데이터 ────────────────────────────────────────────────────────────────
# 아래 값은 **빌드 시점에 온체인에서 다시 읽어 덮어씁니다** (fetch_onchain 참고).
# 여기 적힌 것은 조회가 실패했을 때 쓰는 마지막 확인값입니다.
#
# 직접 고치지 마세요. 값을 갱신하려면 `python3 _build.py` 를 실행하면 됩니다.
# 자동 갱신: .github/workflows/refresh.yml 이 매일 실행합니다.
DATA = dict(
    as_of="2026-08-12",
    slashing="0",
    services_live="0", services_total="10",
    contact="contact@durenodes.com",
    security="security@durenodes.com",
    github="https://github.com/durenodes",
    x="https://x.com/durenodes",
    telegram="https://t.me/durenodes",
    monitor="https://github.com/durenodes/monitor",
)

# ── 온체인 조회 ────────────────────────────────────────────────────────────────
# 페이지가 "온체인에서 그대로 확인할 수 있는 값만 적는다"고 말하므로,
# 실제로 그렇게 되도록 빌드 때마다 다시 읽습니다.
#
# 실패해도 빌드는 계속됩니다. 다만 그 경우 위 DATA 의 옛 값이 그대로 나가므로
# 종료 코드 1 을 돌려주고, 워크플로가 이를 감지해 커밋하지 않습니다.
# 낡은 값을 새 값인 척 배포하는 것보다 배포를 건너뛰는 편이 낫습니다.

# 체인 하나의 정의가 네트워크 카드·상태표·통계·위임 카드를 **모두** 만듭니다.
# 예전에는 네 곳을 따로 고쳐야 했고, 그래서 코스모스 허브 메인넷이 어디에도
# 들어가지 않은 채로 배포돼 있었습니다. 추가할 곳이 하나면 빠뜨릴 수 없습니다.
#
#   cap  — 합의에 참여하는 상한. 셀레스티아 100, 코스모스 허브 180 (본딩은 200).
#          순위가 이 값에 가까우면 밀려날 위험이 있다는 뜻이라 그대로 보여줍니다.
CHAINS = [
    dict(key="tia", cid="celestia", label="Celestia", tick="TIA", denom="TIA",
         kind="mainnet", window=10000, since="2026-07-31", cap=100, rank=True,
         api=["https://celestia-rest.publicnode.com", "https://celestia-api.polkachu.com"],
         valoper="celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq",
         valcons="celestiavalcons10ph5dmuk55rp3lr7x3am2esmdxyclusdqvn5tn",
         keplr="https://wallet.keplr.app/chains/celestia?modal=validator&chain=celestia"
               "&validator_address=celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq",
         explorers=[("Mintscan", "https://www.mintscan.io/celestia/validators/"
                                 "celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq"),
                    ("Celenium", "https://celenium.io/validator/"
                                 "celestiavaloper188d40wvjvlgl27pt3l433pq8vrj4g624qmmgvq")]),
    dict(key="hub", cid="cosmoshub-4", label="Cosmos Hub", tick="ATOM", denom="ATOM",
         kind="mainnet", window=10000, since="2026-08-11", cap=180, rank=True,
         api=["https://cosmos-api.polkachu.com", "https://cosmos-rest.publicnode.com"],
         valoper="cosmosvaloper18g6vu6qn3qdm2wttwpcyr8638usjw5s38f3wdm",
         valcons="cosmosvalcons1p790seryrdhytu2yv68h0an52lcy0jhwdmc6xe",
         keplr="https://wallet.keplr.app/chains/cosmos-hub?modal=validator&chain=cosmoshub-4"
               "&validator_address=cosmosvaloper18g6vu6qn3qdm2wttwpcyr8638usjw5s38f3wdm",
         explorers=[("Mintscan", "https://www.mintscan.io/cosmos/validators/"
                                 "cosmosvaloper18g6vu6qn3qdm2wttwpcyr8638usjw5s38f3wdm")]),
    dict(key="mocha", cid="mocha-4", label="Celestia Mocha", tick="MCH", denom="TIA",
         kind="testnet", window=10000, since="2026-07-31", cap=None, rank=False,
         api=["https://celestia-testnet-api.polkachu.com", "https://api-mocha.pops.one"],
         valoper="celestiavaloper1f9894lzpzav48h2cf07500nlf5dandzxg337eq",
         valcons="celestiavalcons1eclzq8qmrqrq9ttgur2490ymka2k4duwuvucx7"),
    dict(key="prov", cid="provider", label="Cosmos Hub Provider", tick="PROV", denom="ATOM",
         kind="testnet", window=10000, since="2026-08-05", cap=None, rank=False,
         api=["https://rest.provider-sentry-01.hub-testnet.polypore.xyz",
              "https://rest.provider-sentry-02.hub-testnet.polypore.xyz"],
         valoper="cosmosvaloper169my69d97z05nd4kq3ztqs0kl6mn5xfn8m8mq6",
         valcons="cosmosvalcons1xzr5nr4pwhvupwx32z3s8s77znrtqrq4z2jsaq"),
]

# 장애 기록. **지우지 않습니다.** 새 항목은 위에 붙입니다.
# 원인을 모르면 모른다고 적습니다 — 빈 칸이나 그럴듯한 추정으로 채우지 마세요.
INCIDENTS = [
    dict(id="2026-08-12-hub", date="2026-08-12", time="02:00 KST",
         chain="cosmoshub-4", dur="9h 29m", kind="outage", cause="arch", jailed=False, slashed=False),
]

POSTMORTEMS = [dict(
    slug="2026-08-12-cosmos-hub",
    date="2026-08-12",
    en=dict(
        title="254 gas — a Cosmos Hub outage postmortem | DURE",
        h1="254 gas",
        desc="Our Cosmos Hub validator stopped signing for nine and a half hours because we built "
             "the binary ourselves for the wrong architecture. What happened, what we got wrong, "
             "and what we changed.",
        kicker="POSTMORTEM · 12 AUGUST 2026",
        lede="Our Cosmos Hub validator stopped signing at 02:00 KST and did not sign again until "
             "11:29. It was never jailed and never slashed, but it came within 37% of the line. "
             "The cause was a single number: 254 gas.",
        meta=[("CHAIN", "cosmoshub-4"), ("DURATION", "9h 29m"),
              ("IMPACT", "no jail · no slashing"), ("PEAK MISSED", "5,989 / 9,500")],
        sections=[
            ("What broke", [
                "<p>We ran the node from an image we built ourselves, and that build came out "
                "<code>linux/arm64</code>. The official Cosmos Hub release is published for "
                "<code>linux/amd64</code> only, and that is what every other validator on the "
                "network runs.</p>",
                "<p>For three hours this made no difference. Then block 32,454,059 arrived carrying "
                "a transaction that our build metered differently:</p>",
                "<pre>panic recovered in runTx\n  err=\"out of gas in location: WritePerByte;\n"
                "       gasWanted: 259076, gasUsed: 259330: out of gas\"</pre>",
                "<p>Two hundred and fifty-four gas over the limit. On every other node the "
                "transaction fit and succeeded. On ours it ran out and failed, and a failed "
                "transaction changes no state. From that block onward our application state was "
                "a different thing from the chain's.</p>",
                "<pre>CONSENSUS FAILURE!!! wrong Block.Header.AppHash\n"
                "  Expected D018907A...   ← what our node computed\n"
                "  got      56826755...   ← what the network agreed on</pre>",
                "<p>Consensus asks for byte-identical results. Running \"the same version\" is not "
                "the same thing as running the same binary.</p>",
            ]),
            ("Why it took six hours to notice, and three more to diagnose", [
                "<p>Once the state diverged, our node treated every correct block it received as "
                "invalid — and disconnected the peer that sent it.</p>",
                "<pre>Stopping peer for error\n  err=\"reactor validation error: wrong Block.Header.AppHash\"</pre>",
                "<p>Ninety-nine percent of the log was peers connecting and dropping. The symptom "
                "read as <em>the network is rejecting us</em>. We were rejecting the network.</p>",
                "<p>The node also reported <code>catching_up: false</code> the whole time. The "
                "block-sync reactor had already exited, so as far as it knew there was nothing to "
                "catch up on. It was four thousand blocks behind and frozen.</p>",
                "<p>One command would have shown the panic immediately:</p>",
                "<pre>docker logs --tail 400 &lt;container&gt; 2>&amp;1 | grep -v 'module=p2p' | tail -40</pre>",
                "<p>That is now the first thing we run on any node incident.</p>",
            ]),
            ("Two things we got wrong on the way", [
                "<p><b>We blamed memory.</b> The host showed 31 of 32 GB used and heavy swapping, so "
                "we capped the container limits. Three healthy containers restarted for nothing. "
                "Measured properly, the containers were using 15.6 of 20 GiB and the Cosmos node "
                "3.1 of 8. The host figure was page cache from blockchain disk I/O — something we "
                "had already written down elsewhere and did not think to reread.</p>",
                "<p><b>Then we blamed peers.</b> We replaced a working peer list with twenty "
                "addresses harvested from public RPC nodes. Many were sentries that drop unknown "
                "connections on sight, and because persistent peers are retried forever, they "
                "occupied the dial slots and starved normal peer discovery. The original list was "
                "never the problem.</p>",
                "<p>Both detours came from reading symptoms instead of reading the log.</p>",
            ]),
            ("What actually fixed it", [
                "<p>State sync stalled three times — once mid-transfer, twice on light-client "
                "verification. A 43 GB snapshot download was prepared and never needed.</p>",
                "<p>What worked was copying the data directory from another machine already running "
                "the official amd64 image, after stopping it so the database was consistent. "
                "Copying a running node's database gives you a torn snapshot and reproduces exactly "
                "the mismatch you are trying to escape.</p>",
                "<p>The first copy still failed. We swapped the data but left the arm64 binary in "
                "place, and it replayed 233 blocks and diverged again at the same transaction. "
                "<b>The binary has to change first, then the data.</b></p>",
                "<p>Swapping to the official image needed two overrides — its entrypoint is "
                "<code>[\"gaiad\", \"start\"]</code> where ours was <code>[\"gaiad\"]</code>, and it "
                "runs as a non-root user against a root-owned data directory. After that, "
                "<code>uname -m</code> reporting <code>x86_64</code> was the check that mattered.</p>",
            ]),
            ("What changed", [
                "<p><b>Mainnet nodes run official release images. No self-built binaries.</b> Where "
                "the host architecture differs from the release, we run the official build under "
                "emulation — slower, and worth it. A slow node signs late; a wrong node cannot sign "
                "at all. Our Celestia nodes were never affected because they had used the official "
                "image from the start.</p>",
                "<p><b>Our monitoring alerted 65 minutes in, then went quiet for six hours.</b> "
                "Every rule fired as written — the rules were wrong. Alerting once per condition "
                "keeps people from muting notifications, but it meant the loudest moment of the "
                "incident was the quietest. Missed blocks went from 689 to 5,989 during that "
                "silence.</p>",
                "<p>So a halted node is now distinguished from one merely missing blocks: compare "
                "the rise in missed blocks against how far the chain moved. A ratio at or above 0.9 "
                "means we are signing nothing, and it lands in a single poll rather than waiting "
                "for a counter to look alarming. That alert repeats every poll for as long as the "
                "halt lasts, and a ladder at 25/50/75% of the jail threshold fires alongside it. "
                "Every alert now carries the projected jail time.</p>",
                "<p>The monitor is public: "
                "<a href=\"https://github.com/durenodes/monitor\" rel=\"noopener\" target=\"_blank\">"
                "github.com/durenodes/monitor</a>.</p>",
            ]),
        ],
        back="← Back to durenodes.com",
    ),
    ko=dict(
        title="가스 254 — 코스모스 허브 장애 기록 | DURE",
        h1="가스 254",
        desc="코스모스 허브 밸리데이터가 9시간 반 동안 서명을 멈췄습니다. 바이너리를 직접 빌드하면서 "
             "아키텍처가 어긋난 것이 원인이었습니다. 무슨 일이 있었고, 무엇을 잘못 짚었고, 무엇을 바꿨는지.",
        kicker="장애 기록 · 2026년 8월 12일",
        lede="코스모스 허브 밸리데이터가 02:00 에 서명을 멈췄고 11:29 에 재개했습니다. jail 되지도 "
             "슬래싱되지도 않았지만 임계까지 37% 를 남긴 상태였습니다. 원인은 숫자 하나였습니다 — 가스 254.",
        meta=[("체인", "cosmoshub-4"), ("길이", "9시간 29분"),
              ("영향", "jail 없음 · 슬래싱 없음"), ("최고 미스", "5,989 / 9,500")],
        sections=[
            ("무엇이 깨졌나", [
                "<p>노드를 직접 빌드한 이미지로 돌리고 있었고, 그 빌드가 <code>linux/arm64</code> 로 "
                "나왔습니다. 코스모스 허브 공식 릴리스는 <code>linux/amd64</code> 전용이고, "
                "네트워크의 다른 밸리데이터는 전부 그것으로 돕니다.</p>",
                "<p>세 시간 동안은 아무 차이가 없었습니다. 그러다 32,454,059 번 블록에 우리 빌드에서만 "
                "다르게 계량되는 트랜잭션이 실려 왔습니다.</p>",
                "<pre>panic recovered in runTx\n  err=\"out of gas in location: WritePerByte;\n"
                "       gasWanted: 259076, gasUsed: 259330: out of gas\"</pre>",
                "<p>한도를 254 가스 넘겼습니다. 다른 모든 노드에서는 한도 안에 들어와 성공한 "
                "트랜잭션이 우리 노드에서만 실패했고, <b>실패한 트랜잭션은 상태를 바꾸지 않습니다.</b> "
                "그 블록부터 우리 앱 상태는 체인의 것과 다른 물건이 되었습니다.</p>",
                "<pre>CONSENSUS FAILURE!!! wrong Block.Header.AppHash\n"
                "  Expected D018907A...   ← 우리 노드가 계산한 값\n"
                "  got      56826755...   ← 네트워크가 합의한 값</pre>",
                "<p>합의는 바이트 단위로 같은 결과를 요구합니다. \"같은 버전\"을 돌리는 것과 "
                "같은 바이너리를 돌리는 것은 다릅니다.</p>",
            ]),
            ("왜 여섯 시간을 몰랐고, 세 시간을 더 헤맸나", [
                "<p>상태가 갈라진 뒤로 우리 노드는 받은 정상 블록을 전부 잘못된 블록으로 판단하고, "
                "그것을 보내준 피어를 끊었습니다.</p>",
                "<pre>Stopping peer for error\n  err=\"reactor validation error: wrong Block.Header.AppHash\"</pre>",
                "<p>로그의 99% 가 피어 연결과 해제였습니다. 겉보기 증상은 <em>네트워크가 우리를 "
                "거부한다</em> 였습니다. 실제로는 우리가 네트워크를 거부하고 있었습니다.</p>",
                "<p>노드는 그동안 내내 <code>catching_up: false</code> 를 보고했습니다. "
                "블록 동기화 리액터가 이미 종료된 뒤라 스스로는 따라잡을 게 없다고 믿었습니다. "
                "실제로는 4,000 블록 뒤에서 멈춰 있었습니다.</p>",
                "<p>명령 한 줄이면 panic 이 바로 보였습니다.</p>",
                "<pre>docker logs --tail 400 &lt;컨테이너&gt; 2>&amp;1 | grep -v 'module=p2p' | tail -40</pre>",
                "<p>이제 노드 장애에서 가장 먼저 하는 일입니다.</p>",
            ]),
            ("가는 길에 두 번 잘못 짚었습니다", [
                "<p><b>메모리 탓이라고 봤습니다.</b> 호스트가 32GB 중 31GB 사용에 스왑이 심해 "
                "컨테이너 상한을 걸었고, 멀쩡한 컨테이너 셋이 이유 없이 재시작됐습니다. 제대로 재보니 "
                "컨테이너 합계는 20 GiB 중 15.6, 코스모스 노드는 8 중 3.1 이었습니다. 호스트 수치는 "
                "블록체인 디스크 I/O 의 페이지 캐시였고, <b>이미 우리 문서에 적어둔 내용</b>인데 "
                "다시 읽어볼 생각을 못 했습니다.</p>",
                "<p><b>다음엔 피어 탓이라고 봤습니다.</b> 멀쩡히 돌던 피어 목록을 공개 RPC 에서 긁은 "
                "주소 20개로 바꿨습니다. 상당수가 모르는 연결을 즉시 끊는 센트리였고, "
                "persistent peer 는 무한 재시도라 다이얼 슬롯을 점유해 정상적인 피어 탐색까지 "
                "막았습니다. 원래 목록은 처음부터 문제가 아니었습니다.</p>",
                "<p>두 번의 우회 모두 로그가 아니라 증상을 읽어서 생긴 일입니다.</p>",
            ]),
            ("무엇이 실제로 고쳤나", [
                "<p>state-sync 는 세 번 실패했습니다 — 한 번은 전송 도중, 두 번은 라이트 클라이언트 "
                "검증에서. 43GB 스냅샷 다운로드는 준비만 하고 쓰지 않았습니다.</p>",
                "<p>통한 것은 이미 공식 amd64 이미지로 돌고 있던 다른 머신에서 데이터 디렉토리를 "
                "복사해 오는 것이었습니다. <b>복사 전에 그 노드를 반드시 멈춰야 합니다.</b> "
                "돌아가는 노드의 DB 를 복사하면 쓰기 도중 상태가 잘려 들어와, 지금 벗어나려는 바로 그 "
                "불일치가 재현됩니다.</p>",
                "<p>첫 복사는 그래도 실패했습니다. 데이터만 갈고 arm64 바이너리를 그대로 뒀더니 "
                "233 블록을 다시 실행하다 같은 트랜잭션에서 또 갈라졌습니다. "
                "<b>바이너리를 먼저 바꾸고, 그다음에 데이터입니다.</b></p>",
                "<p>공식 이미지로 바꾸는 데 두 가지 오버라이드가 필요했습니다 — entrypoint 가 "
                "<code>[\"gaiad\", \"start\"]</code> 인데 우리는 <code>[\"gaiad\"]</code> 였고, "
                "실행 유저가 non-root 인데 데이터는 root 소유였습니다. 그다음엔 "
                "<code>uname -m</code> 이 <code>x86_64</code> 를 뱉는지가 유일하게 중요한 확인이었습니다.</p>",
            ]),
            ("무엇을 바꿨나", [
                "<p><b>메인넷 노드는 공식 릴리스 이미지만 씁니다. 자체 빌드 금지.</b> 호스트 아키텍처가 "
                "릴리스와 다르면 공식 빌드를 에뮬레이션으로 돌립니다. 느려지지만 그럴 값어치가 "
                "있습니다 — 느린 노드는 늦게 서명하고, 틀린 노드는 아예 못 합니다. 셀레스티아 노드가 "
                "무사했던 이유도 처음부터 공식 이미지였기 때문입니다.</p>",
                "<p><b>모니터는 65분 만에 알렸고, 그 뒤 여섯 시간을 침묵했습니다.</b> 모든 규칙이 "
                "쓰인 대로 작동했습니다 — 규칙이 틀렸습니다. 조건마다 한 번만 알리는 설계는 사람이 "
                "알림을 꺼버리는 걸 막지만, 그 결과 장애가 가장 시끄러워야 할 구간이 가장 조용했습니다. "
                "그 침묵 동안 놓친 블록은 689 에서 5,989 로 올랐습니다.</p>",
                "<p>그래서 이제 <b>멈춘 노드</b>와 <b>가끔 놓치는 노드</b>를 구분합니다. 놓친 블록 "
                "증가분을 체인이 나아간 블록 수와 대조해서, 그 비율이 0.9 이상이면 서명이 사실상 0 "
                "입니다. 카운터가 위협적으로 보일 때까지 기다리지 않고 <b>한 번의 폴링으로</b> "
                "판정됩니다. 이 알림은 정지가 이어지는 동안 매 폴링마다 반복되고, jail 임계의 "
                "25/50/75% 사다리가 함께 울립니다. 모든 알림에 예상 jail 시각이 붙습니다.</p>",
                "<p>감시기는 공개돼 있습니다: "
                "<a href=\"https://github.com/durenodes/monitor\" rel=\"noopener\" target=\"_blank\">"
                "github.com/durenodes/monitor</a>.</p>",
            ]),
        ],
        back="← durenodes.com 으로",
    ),
)]


# 가이드는 포스트모템과 같은 셸을 씁니다. 별도 저장소·서브도메인을 만들지 않는 이유는
# 쪼개면 방치되기 때문입니다. 기준: 공식 문서에 없고, 우리가 밸리데이터라서 말할 수 있는 것.
GUIDES = [dict(
    slug="cosmostation-shutdown",
    date="2026-08-16",
    en=dict(
        title="Cosmostation is shutting down. What happens to your stake? | DURE",
        h1="Your stake stays where it is",
        desc="Cosmostation ends its wallet service on 1 September 2026. Watch out for fake "
             "migration sites, and do not unbond — your delegation is unaffected and "
             "unbonding costs you 21 days of rewards.",
        kicker="GUIDE · 16 AUGUST 2026",
        lede="Cosmostation announced on 14 August that its wallet service ends on 1 September. "
             "Watch out for fake migration sites, and do not unbond — your delegation carries "
             "over untouched, and unbonding throws away 21 days of rewards.",
        meta=[("ANNOUNCED", "14 Aug 2026"), ("SERVICE ENDS", "1 Sep 2026"),
              ("PLATFORMS", "iOS · Android · Chrome"), ("YOUR FUNDS", "on-chain · unaffected")],
        sections=[
            ("The stake is on the chain", [
                "<p>Your balance, delegations, unbonding entries and unclaimed rewards are "
                "recorded on-chain against your address. Closing the app does not change any of "
                "them.</p>",
                "<p>The one thing with a deadline is your recovery phrase. When the app stops "
                "working, the screen that shows it goes with it.</p>",
                "<pre>Phrase already written down   → nothing urgent, import it whenever\n"
                "Phrase only inside the app    → export it before 1 September</pre>",
            ]),
            ("Do not unbond", [
                "<p>Unbonding on Cosmos Hub takes 21 days. You earn nothing during that time, "
                "you cannot vote, and you cannot cancel it once started.</p>",
                "<p>Switching wallets does not require unbonding. Put the same recovery phrase "
                "into another wallet and you get the same address, with the same delegation "
                "already on it.</p>",
            ]),
            ("If the balance shows zero", [
                "<p>Some people will import their phrase, see an empty account, and assume the "
                "funds are gone. Usually it is the derivation path.</p>",
                "<p>Cosmostation lets you pick the coin type, and reads <code>hd_path</code> per "
                "chain instead of assuming one. Ethereum-style chains use "
                "<code>m/44'/60'/0'/0/x</code>; the Cosmos default is "
                "<code>m/44'/118'/0'/0/x</code>. An account made with a non-default setting lands "
                "on a different address in a wallet that assumes the default.</p>",
                "<p>The tokens are still at the address you staked from. Check the address before "
                "anything else:</p>",
                "<pre>1. Find the address you staked from — explorer or transaction history\n"
                "2. Look it up on an explorer; the delegation will be there\n"
                "3. Different address in the new wallet means a different path</pre>",
                "<p>Ledger accounts work differently. The key never left the device, so there is "
                "no phrase to export. Connect the same Ledger to another wallet.</p>",
            ]),
            ("Fake migration sites", [
                "<p>A published shutdown date is good conditions for phishing. Expect pages "
                "offering a \"Cosmostation migration tool\" that ask for your recovery phrase.</p>",
                "<p>A recovery phrase goes into a wallet application you installed yourself. "
                "There is no migration step that requires typing it into a website.</p>",
            ]),
            ("Do not move to Leap", [
                "<p>Some coverage lists Leap as an alternative. Leap shut down on 28 May 2026. "
                "Check that the wallet you are moving to is still operating.</p>",
            ]),
        ],
        back="← durenodes.com",
    ),
    ko=dict(
        title="코스모스테이션 종료 — 스테이킹은 어떻게 되나 | DURE",
        h1="스테이킹은 그대로 남습니다",
        desc="코스모스테이션이 2026년 9월 1일 지갑 서비스를 종료합니다. 사칭 사이트를 "
             "조심하시고, 위임은 그대로 유지되니 언스테이킹으로 보상을 낭비하지 마세요.",
        kicker="가이드 · 2026년 8월 16일",
        lede="코스모스테이션이 8월 14일에 9월 1일 지갑 서비스 종료를 알렸습니다. "
             "사칭 사이트를 조심하시고, 위임은 그대로 유지되니 언스테이킹으로 보상을 "
             "낭비하지 마세요.",
        meta=[("공지", "2026-08-14"), ("종료", "2026-09-01"),
              ("대상", "iOS · Android · Chrome"), ("자산", "체인에 있음 · 영향 없음")],
        sections=[
            ("스테이킹은 체인에 있습니다", [
                "<p>잔고, 위임, 언본딩, 미수령 보상은 전부 체인에 주소별로 기록돼 있습니다. "
                "앱이 닫혀도 바뀌지 않습니다.</p>",
                "<p>기한이 있는 건 니모닉 하나입니다. 앱이 멈추면 니모닉을 보여주는 화면도 "
                "같이 없어집니다.</p>",
                "<pre>니모닉을 적어두셨다면   급하지 않습니다. 아무 때나 다른 지갑에 넣으면 됩니다\n"
                "앱 안에만 있다면        9월 1일 전에 내보내세요</pre>",
            ]),
            ("언스테이킹하지 마세요", [
                "<p>코스모스 허브 언본딩은 21일입니다. 그동안 보상이 없고, 투표할 수 없고, "
                "시작하면 취소할 수 없습니다.</p>",
                "<p>지갑을 바꾸는 데 언본딩이 필요하지 않습니다. 같은 니모닉을 다른 지갑에 "
                "넣으면 같은 주소가 나오고, 위임은 그 주소에 이미 붙어 있습니다.</p>",
            ]),
            ("잔고가 0으로 보인다면", [
                "<p>니모닉을 새 지갑에 넣었는데 계정이 비어 보이는 경우가 있습니다. 대개 "
                "파생 경로 문제입니다.</p>",
                "<p>코스모스테이션은 코인 타입을 사용자가 고를 수 있고, 경로를 하나로 정해두지 "
                "않고 체인마다 <code>hd_path</code> 를 읽습니다. 이더리움 계열은 "
                "<code>m/44'/60'/0'/0/x</code>, 코스모스 기본값은 <code>m/44'/118'/0'/0/x</code> "
                "입니다. 기본값이 아닌 설정으로 만든 계정은 기본값을 쓰는 지갑에서 다른 주소로 "
                "나옵니다.</p>",
                "<p>토큰은 원래 스테이킹하던 주소에 있습니다. 먼저 주소부터 확인하세요.</p>",
                "<pre>1. 스테이킹하던 주소를 찾습니다 — 익스플로러나 거래 내역\n"
                "2. 익스플로러에서 조회하면 위임이 보입니다\n"
                "3. 새 지갑 주소가 다르면 파생 경로가 다른 것입니다</pre>",
                "<p>렛저 계정은 경우가 다릅니다. 키가 기기 밖으로 나온 적이 없어 내보낼 니모닉이 "
                "없습니다. 같은 렛저를 다른 지갑에 연결하면 됩니다.</p>",
            ]),
            ("사칭 사이트", [
                "<p>종료 날짜가 공개돼 있어 피싱하기 좋은 조건입니다. \"코스모스테이션 "
                "마이그레이션\" 같은 이름으로 니모닉을 입력받는 페이지를 조심하세요.</p>",
                "<p>니모닉은 직접 설치한 지갑 앱에만 입력합니다. 웹페이지에 니모닉을 넣어야 하는 "
                "이전 절차는 없습니다.</p>",
            ]),
            ("Leap 으로 옮기지 마세요", [
                "<p>대안으로 Leap 을 적어둔 기사가 있습니다. Leap 은 2026년 5월 28일에 "
                "종료했습니다. 옮길 지갑이 아직 운영 중인지 확인하세요.</p>",
            ]),
        ],
        back="← durenodes.com 으로",
    ),
)]


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "durenodes-site-build"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _first(apis, path):
    """엔드포인트를 순서대로 시도합니다. 하나가 죽어도 빌드가 멈추지 않게."""
    last = None
    for base in apis:
        try:
            return _get(base + path)
        except Exception as e:      # noqa: BLE001 — 어떤 실패든 다음 엔드포인트로
            last = e
    raise RuntimeError(f"모든 엔드포인트 실패: {path} ({last})")


def _one(c):
    v = _first(c["api"], f"/cosmos/staking/v1beta1/validators/{c['valoper']}")["validator"]
    si = _first(c["api"], f"/cosmos/slashing/v1beta1/signing_infos/{c['valcons']}")["val_signing_info"]
    rates = v["commission"]["commission_rates"]

    rank = None
    if c["rank"]:
        # 본딩된 밸리데이터를 스테이크 순으로 정렬해 우리 자리를 찾습니다.
        # 코스모스 허브는 본딩 200 곳 중 상위 180 곳만 합의에 참여하므로,
        # 분모는 본딩 수가 아니라 cap 입니다.
        vs = _first(c["api"], "/cosmos/staking/v1beta1/validators"
                              "?pagination.limit=500&status=BOND_STATUS_BONDED")["validators"]
        vs.sort(key=lambda x: int(x["tokens"]), reverse=True)
        for i, x in enumerate(vs, 1):
            if x["operator_address"] == c["valoper"]:
                rank = i
                break

    return c["key"], dict(
        stake=f"{int(v['tokens']) / 1e6:,.2f}",
        comm=f"{float(rates['rate']) * 100:.2f}",
        max_comm=f"{float(rates['max_rate']) * 100:.2f}",
        max_change=f"{float(rates['max_change_rate']) * 100:.2f}",
        missed=int(si["missed_blocks_counter"]),
        window=c["window"],
        rank=rank,
        status=v["status"].replace("BOND_STATUS_", ""),
        bonded=(v["status"] == "BOND_STATUS_BONDED"),
        jailed=bool(v.get("jailed", False)),
    )


LIVE: dict[str, dict] = {}


def fetch_onchain():
    """LIVE 를 온체인 현재값으로 채웁니다. 성공하면 True."""
    try:
        with _cf.ThreadPoolExecutor(len(CHAINS)) as ex:
            got = dict(ex.map(_one, CHAINS))
    except Exception as e:          # noqa: BLE001
        print(f"  온체인 조회 실패: {e}", file=sys.stderr)
        return False

    LIVE.update(got)
    DATA["as_of"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    DATA["mainnets"] = str(sum(1 for c in CHAINS if c["kind"] == "mainnet"))
    DATA["testnets"] = str(sum(1 for c in CHAINS if c["kind"] == "testnet"))
    DATA["incidents"] = str(len(INCIDENTS))

    print("  온체인 조회 완료")
    for c in CHAINS:
        r = got[c["key"]]
        pos = f" · {r['rank']}/{c['cap']}" if r["rank"] else ""
        print(f"    {c['cid']:<20} {r['stake']:>14} {c['denom']} · 커미션 {r['comm']}%"
              f" · 미스 {r['missed']:,}/{r['window']:,} · {r['status']}{pos}")
        if not r["bonded"] or r["jailed"]:
            print(f"      경고: BONDED 가 아닙니다 (jailed={r['jailed']})", file=sys.stderr)
        # 합의 셋 하위 5 자리 안으로 들어오면 빌드 로그에 남깁니다.
        # 밀려나면 보상이 끊기는데 missed 로는 잡히지 않습니다.
        if r["rank"] and c["cap"] and r["rank"] > c["cap"] - 5:
            print(f"      경고: 합의 셋 하위 {r['rank']}/{c['cap']} — 밀려날 수 있습니다", file=sys.stderr)

    # 가동률은 **페이지에 싣지 않습니다.** missed_blocks_counter 는 누적이 아니라
    # 최근 10,000블록(약 7.6시간) 롤링 윈도라, 이걸 "가동률"로 내걸면
    # 방문자는 전체 기간 수치로 읽고 값은 하루에도 크게 출렁입니다.
    # 대신 STATUS 표에 "미스 / 윈도" 를 그대로 적어 해석의 여지를 없앴습니다.
    return True


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
    title="DURE — Celestia & Cosmos Hub Validator | Minimum Commission, Verifiable Figures",
    desc="DURE (doo-reh) runs Celestia and Cosmos Hub validators at each chain's minimum commission, publishes only figures you can verify on-chain, and never deletes an incident record.",
    og_desc="Each chain's minimum commission. Only figures you can check on-chain. Incidents never deleted.",
    kicker="CELESTIA · COSMOS HUB · MAINNET VALIDATOR",
    h1="One chain at a time, run properly",
    lede=('We started on Celestia mainnet on 31 July 2026 and joined the Cosmos Hub active set '
          'on 11 August — not long enough to have a record worth showing. What we can do is '
          'publish every number you can check on-chain yourself, write outages down as they '
          'happen, and charge <b>each chain\'s minimum commission</b>. Everything we open is '
          '<a href="#services">free to use</a>.'),
    nav=dict(networks="NETWORKS", services="SERVICES", status="STATUS", log="LOG",
             guides="GUIDES", delegate="DELEGATE"),
    stat_networks="NETWORKS",
    stat_slashing="SLASHING · JAIL", stat_services="PUBLIC SERVICES · LIVE",
    stat_incidents="INCIDENTS ON RECORD",
    cta_delegate="DELEGATE", cta_services="Service schedule", cta_status="STATUS",
    sec_networks="{mainnets} mainnet · {testnets} testnet",
    net_mainnet="MAINNET", net_testnet="TESTNET",
    net_stake="stake", net_comm="commission", net_rank="rank",
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
    th=dict(network="NETWORK", status="STATUS", stake="STAKE", commission="COMMISSION",
            missed="MISSED", rank="RANK", since="SINCE"),
    note=('<b>We charge each chain\'s minimum commission.</b> Celestia enforces a 20% floor at '
          'the network level; Cosmos Hub enforces 5%. We sit on both floors. The numbers differ '
          'because the rules differ, not the policy — and every value above can be verified on-chain.'
          '<br><br><b>RANK is the part we would rather not show.</b> Celestia caps its active set at '
          '100 and the Cosmos Hub at 180 of its 200 bonded. A validator that slips past those cuts '
          'stops earning, and on the Hub it stops signing while still reading as bonded. We are '
          'closer to those edges than we would like, so the number stays on the page.'
          '<br><br><b>We do not put up a number you cannot check.</b> Every figure on this page '
          'resolves to a query against the chain, and the addresses to run it against are below. '
          'If a value here disagrees with the chain, the chain is right.'),
    foot_meta=["MIN = the lowest commission the chain allows",
               "MISSED = within the last 10,000-block window",
               "RANK = position in the active set",
               "testnet tokens have no value"],
    door_go="View \u2192",
    door_log_t="Every incident, with the cause",
    door_log_d="Signing outages, what caused them, and what we changed. "
               "Nothing is removed once posted.",
    door_guides_t="Notes from running the nodes",
    door_guides_d="What the official documentation does not cover.",
    log_page=dict(
        title="Incident log | DURE",
        h1="Incident log",
        desc="Every signing outage on our validators, with cause, duration and what changed. "
             "Entries are never removed.",
        kicker="INCIDENT LOG",
        lede="Every outage that stopped us signing, with what caused it and what we changed. "
             "We do not delete entries.",
        criteria="",
        back="\u2190 durenodes.com",
    ),
    sec_guides="What the official docs do not cover",
    guides=dict(
        title="Guides | DURE",
        h1="Guides",
        desc="Operational notes from running Celestia and Cosmos Hub validators. "
             "Only what the official documentation does not cover.",
        kicker="GUIDES",
        lede="We write these when we hit something the official documentation does not "
             "cover, or when a deadline is about to cost people money.",
        criteria="We do not publish general setup guides. If the official docs already "
                 "say it, we link to them instead.",
        back="\u2190 durenodes.com",
    ),
    sec_log="We write down outages and what we did about them. We do not delete them.",
    log_head=("Monitoring runs every 10 minutes and the code is "
              '<a href="{monitor}" rel="noopener" target="_blank">public</a>. '
              "No jail and no slashing so far — the entries below are the gaps we saw."),
    log_cause="CAUSE",
    log_impact="IMPACT",
    log_none="no jail · no slashing",
    log_causes=dict(
        unknown="Not identified. We did not find a cause we could point at, so we are not writing one down.",
        arch=("We were running a self-built arm64 binary while the rest of the network runs the "
              "official amd64 release. One transaction metered 254 gas differently, ran out of gas "
              "on our node alone, and our application state diverged from the chain."),
    ),
    log_bodies=dict(
        outage="A {dur} outage on {chain}, detected by our own monitoring.",
        gap="A {dur} gap on {chain}, recorded by our own monitoring. We have not confirmed "
            "whether the node was unreachable or simply missed signatures.",
    ),
    log_more="Read the full postmortem →",
    log_criteria=("We record outages where signing stopped. If we could not identify a cause we say "
                  "so, and what goes up here stays up."),
    log_empty="NO INCIDENTS ON RECORD",
    log_empty_p=("There has been no jail and no slashing. That is not a boast — it means the time "
                 "has been short. Outages happen eventually, and when they do the cause and the fix "
                 "go here. We do not delete them."),
    sec_delegate="Delegation",
    val_min="· NETWORK MINIMUM",
    val_since="SINCE",
    btn_keplr="Delegate with Keplr",
    story=('<b>DURE (두레, doo-reh)</b> was a village labour commons in Joseon-era Korea. '
           'No one owned it, a ledger recorded how many days each household worked, and the '
           'harvest was split in the same proportion. That is how stake and rewards work here, '
           'so we took the name as it is.'),
    copy="© 2026 DURE",
    links=dict(github="GITHUB", x="X", telegram="TELEGRAM", contact="CONTACT", security="SECURITY"),
),
"ko": dict(
    lang="ko", other="en", other_label="English", other_href="/?lang=en",
    title="DURE 두레 — 셀레스티아·코스모스 허브 밸리데이터 | 최소 수수료, 검증 가능한 값",
    desc="DURE(두레)는 셀레스티아와 코스모스 허브 밸리데이터를 각 체인이 허용하는 최소 수수료로 운영하고, 온체인에서 확인 가능한 값만 올리며, 장애 기록을 지우지 않습니다.",
    og_desc="각 체인이 허용하는 최소 수수료로 운영하고, 온체인에서 확인 가능한 값만 올립니다.",
    kicker="셀레스티아 · 코스모스 허브 · 메인넷 밸리데이터",
    h1="체인 하나부터 제대로 운영합니다",
    lede=('2026년 7월 31일 셀레스티아 메인넷에서 시작했고, 8월 11일 코스모스 허브 액티브 셋에 '
          '들어갔습니다. 아직 짧아서 내세울 실적이 없습니다. 대신 직접 확인할 수 있는 온체인 값만 '
          '올리고, 장애는 생기는 대로 적습니다. 수수료는 <b>각 체인이 허용하는 최소값</b>으로 '
          '받고, 여는 서비스는 <a href="#services">모두 무료</a>입니다.'),
    nav=dict(networks="NETWORKS", services="SERVICES", status="STATUS", log="LOG",
             guides="GUIDES", delegate="DELEGATE"),
    stat_networks="NETWORKS",
    stat_slashing="SLASHING · JAIL", stat_services="공개 서비스 · 제공 중",
    stat_incidents="기록된 장애",
    cta_delegate="DELEGATE", cta_services="서비스 공개 일정", cta_status="STATUS",
    sec_networks="메인넷 {mainnets} · 테스트넷 {testnets}",
    net_mainnet="메인넷", net_testnet="테스트넷",
    net_stake="위임", net_comm="커미션", net_rank="순위",
    net_next="다음 네트워크", net_planned="예정",
    net_next_desc="지금 맡은 네트워크가 안정된 뒤에 늘립니다",
    sec_services="여는 순서와 시점을 미리 알립니다 · 모두 무료",
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
    th=dict(network="NETWORK", status="STATUS", stake="STAKE", commission="COMMISSION",
            missed="MISSED", rank="RANK", since="SINCE"),
    note=('<b>수수료는 각 체인이 허용하는 최소값으로 받습니다.</b> 셀레스티아는 네트워크가 20%를 '
          '최소로 강제하고, 코스모스 허브는 5%입니다. 두 곳 모두 그 하한에 맞춰 두었습니다. '
          '체인마다 숫자가 다른 건 정책이 달라서가 아니라 규칙이 다르기 때문이고, 위 표의 값은 '
          '온체인에서 그대로 확인할 수 있습니다.'
          '<br><br><b>RANK 는 사실 감추고 싶은 숫자입니다.</b> 셀레스티아는 액티브 셋 상한이 100곳, '
          '코스모스 허브는 본딩 200곳 중 180곳입니다. 이 선 밖으로 밀리면 보상이 끊기고, 허브에서는 '
          '본딩 상태 그대로 블록 서명만 멈춥니다. 지금 우리는 그 경계에 가까운 편이고, '
          '그래서 더더욱 이 숫자를 페이지에 남겨둡니다.'
          '<br><br><b>확인할 수 없는 숫자는 올리지 않습니다.</b> 이 페이지의 모든 값은 체인에 '
          '질의하면 그대로 나오고, 질의할 주소는 아래에 적혀 있습니다. 여기 적힌 값이 체인과 '
          '다르면 체인이 맞습니다.'),
    foot_meta=["MIN = 해당 체인이 허용하는 최소 수수료",
               "MISSED = 최근 10,000블록 윈도우 기준",
               "RANK = 액티브 셋 내 순위",
               "테스트넷 토큰은 가치가 없습니다"],
    door_go="보기 \u2192",
    door_log_t="장애 전부, 원인까지",
    door_log_d="서명이 멈춘 장애와 그 원인, 그리고 바꾼 것. 올린 뒤에는 지우지 않습니다.",
    door_guides_t="노드를 돌리며 남긴 기록",
    door_guides_d="공식 문서에 없는 것들입니다.",
    log_page=dict(
        title="장애 기록 | DURE",
        h1="장애 기록",
        desc="우리 밸리데이터에서 서명이 멈춘 장애 전부입니다. 원인과 시간, 바꾼 것을 함께 "
             "적습니다. 기록은 지우지 않습니다.",
        kicker="장애 기록",
        lede="서명이 멈춘 장애 전부와 그 원인, 그리고 바꾼 것입니다. 기록을 지우지 않습니다.",
        criteria="",
        back="\u2190 durenodes.com 으로",
    ),
    sec_guides="공식 문서에 없는 것",
    guides=dict(
        title="가이드 | DURE",
        h1="가이드",
        desc="셀레스티아·코스모스 허브 밸리데이터를 운영하며 남긴 기록입니다. "
             "공식 문서에 없는 것만 씁니다.",
        kicker="가이드",
        lede="공식 문서에 없는 것을 직접 겪었을 때, 또는 기한이 사람들의 돈을 "
             "가져갈 때 씁니다.",
        criteria="일반 설치 가이드는 쓰지 않습니다. 공식 문서에 이미 있는 것은 "
                 "그쪽을 링크합니다.",
        back="\u2190 durenodes.com 으로",
    ),
    sec_log="장애와 조치 내역을 그대로 남깁니다. 지우지 않습니다.",
    log_head=("10분 간격으로 감시하고 있고, 그 코드는 "
              '<a href="{monitor}" rel="noopener" target="_blank">공개</a>돼 있습니다. '
              "지금까지 jail·슬래싱은 없었고, 아래는 관측된 공백입니다."),
    log_cause="원인",
    log_impact="영향",
    log_none="jail 없음 · 슬래싱 없음",
    log_causes=dict(
        unknown="확인하지 못했습니다. 가리킬 수 있는 원인을 찾지 못해 추정으로 채우지 않습니다.",
        arch=("네트워크의 나머지가 공식 amd64 릴리스로 도는데 우리만 자체 빌드한 arm64 바이너리를 "
              "쓰고 있었습니다. 한 트랜잭션에서 가스가 254 만큼 다르게 계산돼 우리 노드에서만 "
              "실패했고, 앱 상태가 체인과 갈라졌습니다."),
    ),
    log_bodies=dict(
        outage="{chain} 에서 {dur} 동안 멈췄고, 자체 모니터링으로 감지했습니다.",
        gap="{chain} 에서 {dur} 의 공백이 자체 모니터링에 기록되었습니다. "
            "노드가 응답하지 않은 것인지 서명만 누락된 것인지는 확인하지 못했습니다.",
    ),
    log_more="전체 기록 읽기 →",
    log_criteria=("서명이 멈춘 장애를 기록합니다. 원인을 모르면 모른다고 적고, "
                  "여기 올라온 것은 지우지 않습니다."),
    log_empty="기록된 장애 없음",
    log_empty_p=("jail되거나 슬래싱된 이력이 없습니다. 다만 이건 자랑이 아니라 아직 시간이 "
                 "짧다는 뜻입니다. 장애는 결국 생기고, 생기면 원인과 조치를 여기에 그대로 "
                 "적습니다. 지우지 않습니다."),
    sec_delegate="위임 안내",
    val_min="· 네트워크 최소",
    val_since="SINCE",
    btn_keplr="Keplr로 위임",
    story=('<b>DURE(두레)</b>는 조선 시대 마을 단위의 공동 노동 조직입니다. 주인이 따로 없었고, '
           '누가 며칠 일했는지 장부에 적어 그만큼 나눴습니다. 지분만큼 보상이 돌아가는 지금 구조와 '
           '같아서 이름을 그대로 가져왔습니다.'),
    copy="© 2026 DURE",
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


def net_cards(c):
    cards = []
    for ch in CHAINS:
        r = LIVE[ch["key"]]
        main = ch["kind"] == "mainnet"
        tag = ('<span class="tag on"><span class="blink"></span>ACTIVE</span>' if main
               else f'<span class="tag warn">{c["net_testnet"]}</span>')
        meta = [f'<span>{ch["cid"].upper()}</span>',
                f'<span>{c["net_stake"]} <b>{r["stake"]} {ch["denom"]}</b></span>',
                f'<span>{c["net_comm"]} <b>{r["comm"]}%</b></span>']
        if r["rank"]:
            meta.append(f'<span>{c["net_rank"]} <b>{r["rank"]} / {ch["cap"]}</b></span>')
        cards.append(
            f'        <div class="net {"live" if main else "test"}">\n'
            f'          <div class="net-top"><span class="tick">{ch["tick"]}</span>'
            f'<span class="net-name">{ch["label"]}</span>{tag}</div>\n'
            f'          <div class="net-meta">{"".join(meta)}</div>\n'
            f'        </div>')
    cards.append(
        f'        <div class="net next">\n'
        f'          <div class="net-top"><span class="tick">—</span>'
        f'<span class="net-name" style="color:var(--muted)">{c["net_next"]}</span>'
        f'<span class="tag">{c["net_planned"]}</span></div>\n'
        f'          <div class="net-meta">{c["net_next_desc"]}</div>\n'
        f'        </div>')
    return "\n".join(cards)


def table_rows(c):
    rows = []
    for ch in CHAINS:
        r = LIVE[ch["key"]]
        rank = f'{r["rank"]} / {ch["cap"]}' if r["rank"] else "—"
        rows.append(
            f'            <tr><td>{ch["cid"]}</td>'
            f'<td class="{"ok" if r["bonded"] else ""}">{r["status"]}</td>'
            f'<td class="num">{r["stake"]} {ch["denom"]}</td>'
            f'<td class="num">{r["comm"]}%<span class="min-badge">MIN</span></td>'
            f'<td class="num">{r["missed"]:,} / {r["window"]:,}</td>'
            f'<td class="num">{rank}</td>'
            f'<td class="num">{ch["since"]}</td></tr>')
    return "\n".join(rows)


def incidents(c, key):
    """장애 기록. 서명이 멈춘 건은 카드로, 그 아래는 한 줄로. 어느 쪽도 지우지 않습니다."""
    if not INCIDENTS:
        return (f'      <div class="empty">\n'
                f'        <div class="empty-t">{c["log_empty"]}</div>\n'
                f'        <p>{c["log_empty_p"]}</p>\n'
                f'      </div>')
    slugs = {p["slug"].split("-", 3)[-1]: p["slug"] for p in POSTMORTEMS}
    items = [f'      <p class="log-head">{c["log_head"].format(monitor=DATA["monitor"])}</p>']
    for i in INCIDENTS:
        pm = next((p for p in POSTMORTEMS if p["date"] == i["date"]), None)
        more = ""
        if pm:
            href = ("/ko" if key == "ko" else "") + f'/incidents/{pm["slug"]}/'
            more = f'\n        <a class="inc-more" href="{href}">{c["log_more"]}</a>'
        items.append(
            f'      <div class="inc">\n'
            f'        <div class="inc-when">{i["date"]} · {i["time"]}</div>\n'
            f'        <p class="inc-body">{c["log_bodies"][i["kind"]].format(chain=i["chain"], dur=i["dur"])}</p>\n'
            f'        <div class="inc-meta">'
            f'<span><b>{c["log_cause"]}</b> {c["log_causes"][i["cause"]]}</span>'
            f'<span><b>{c["log_impact"]}</b> {c["log_none"]}</span></div>'
            f'{more}\n'
            f'      </div>')
    items.append(f'      <p class="log-note">{c["log_criteria"]}</p>')
    return "\n".join(items)


def nav_html(c, key, landing=False):
    """헤더 네비게이션. 랜딩·목록·상세가 **같은 것**을 씁니다.

    랜딩에서는 앵커만 쓰고(부드러운 스크롤), 다른 페이지에서는 랜딩 경로를 붙여
    어디서든 여섯 항목 모두로 이동됩니다.
    """
    pre = "/ko" if key == "ko" else ""
    a = "" if landing else (pre + "/")
    n = c["nav"]
    return "\n".join(f"      {x}" for x in (
        f'<a href="{a}#networks">{n["networks"]}</a>',
        f'<a href="{a}#services">{n["services"]}</a>',
        f'<a href="{a}#status">{n["status"]}</a>',
        f'<a href="{pre}/incidents/" class="nav-pg">{n["log"]}</a>',
        f'<a href="{pre}/guides/" class="nav-pg">{n["guides"]}</a>',
        f'<a href="{a}#delegate" class="nav-key">{n["delegate"]}</a>',
    ))


def guide_list(key, home_prefixed=True):
    """가이드 목록. 랜딩 섹션과 /guides/ 색인이 **같은 함수**를 씁니다.

    두 곳에 손으로 적으면 반드시 갈라집니다 — `todo.md` 가 그 사고를 이미 기록하고 있습니다.
    """
    pre = "/ko" if key == "ko" else ""
    out = []
    for g in GUIDES:
        p = g[key]
        out.append(
            f'      <a class="gd" href="{pre}/guides/{g["slug"]}/">\n'
            f'        <div class="gd-when">{g["date"]}</div>\n'
            f'        <div class="gd-t">{p["h1"]}</div>\n'
            f'        <p class="gd-d">{p["desc"]}</p>\n'
            f'      </a>')
    return "\n".join(out)


def index_page(key, kind):
    """목록 페이지. /guides/ 와 /incidents/ 가 같은 셸을 씁니다.

    랜딩에서 두 섹션을 뺐으므로 여기가 각 기록물의 유일한 입구입니다.
    """
    c = CONTENT[key]
    css = re.sub(r"/\*.*?\*/", "", (HERE / "_style.css").read_text(encoding="utf-8"), flags=re.S).strip()
    canonical = SITE + ("/ko" if key == "ko" else "") + f"/{kind}/"
    alt = (f"/ko/{kind}/" if key == "en" else f"/{kind}/")
    home = "/ko/" if key == "ko" else "/"
    pre = "/ko" if key == "ko" else ""
    g = c["guides"] if kind == "guides" else c["log_page"]
    body = guide_list(key) if kind == "guides" else incidents(c, key)

    return f'''<!DOCTYPE html>
<html lang="{c["lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{g["title"]}</title>
<meta name="description" content="{g["desc"]}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{SITE}/{kind}/">
<link rel="alternate" hreflang="ko" href="{SITE}/ko/{kind}/">
<link rel="alternate" hreflang="x-default" href="{SITE}/{kind}/">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/icon-256.png">
<meta name="theme-color" content="#0D0F0C">
<meta property="og:type" content="website">
<meta property="og:site_name" content="DURE">
<meta property="og:locale" content="{"ko_KR" if key == "ko" else "en_US"}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{g["title"]}">
<meta property="og:description" content="{g["desc"]}">
<meta property="og:image" content="{SITE}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@durenodes">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>

<header class="hdr">
  <div class="wrap hdr-in">
    <a class="brand" href="{home}" aria-label="DURE">
      {MARK}
      <b>DURE</b>
    </a>
    <nav class="nav" aria-label="Sections">
{nav_html(c, key)}
    </nav>
    <a class="lang" href="{alt}" hreflang="{c["other"]}" rel="alternate">{c["other_label"]}</a>
  </div>
</header>

<main id="top">
  <div class="hero">
    <div class="wrap">
      <div class="kicker">{g["kicker"]}</div>
      <h1>{g["h1"]}</h1>
      <p class="lede">{g["lede"]}</p>
    </div>
  </div>

  <section>
    <div class="wrap">
{body}
{f'      <p class="log-note">{g["criteria"]}</p>' if g["criteria"] else ""}
      <p class="pm-back"><a href="{home}">{g["back"]}</a></p>
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
        <a href="{DATA["github"]}" rel="me noopener" target="_blank">{c["links"]["github"]}</a>
        <a href="{DATA["x"]}" rel="me noopener" target="_blank">{c["links"]["x"]}</a>
        <a href="{DATA["telegram"]}" rel="me noopener" target="_blank">{c["links"]["telegram"]}</a>
        <a href="mailto:{DATA["contact"]}">{c["links"]["contact"]}</a>
        <a href="mailto:{DATA["security"]}">{c["links"]["security"]}</a>
    </div>
  </div>
</footer>

</body>
</html>
'''


def delegate_cards(c):
    out = []
    for ch in CHAINS:
        if not ch.get("keplr"):
            continue
        r = LIVE[ch["key"]]
        expl = "".join(
            f'        <a href="{u}" target="_blank" rel="noopener" class="btn">{n}</a>\n'
            for n, u in ch["explorers"])
        out.append(
            f'      <div class="val-card">\n'
            f'        <b class="val-label">{ch["label"].upper()} VALOPER</b>\n'
            f'        <div class="val-addr">{ch["valoper"]}</div>\n'
            f'        <div class="val-meta">\n'
            f'          <span>COMMISSION {r["comm"]}% <b>{c["val_min"]}</b></span>\n'
            f'          <span>MAX {r["max_comm"]}%</span>'
            f'<span>MAX CHANGE {r["max_change"]}%</span>'
            f'<span>{c["val_since"]} {ch["since"]}</span>\n'
            f'        </div>\n'
            f'      </div>\n'
            f'      <div class="cta">\n'
            f'        <a href="{ch["keplr"]}" target="_blank" rel="noopener" class="btn btn-solid">'
            f'<span>{c["btn_keplr"]}</span><span class="dot"></span></a>\n'
            f'{expl}      </div>')
    return "\n".join(out)


def postmortem_html(key, pm, kind="incidents"):
    """장애 기록 상세 페이지. 랜딩과 같은 셸을 쓰되 본문만 다릅니다.

    `kind` 로 /incidents/ 와 /guides/ 를 함께 처리합니다. 셸을 복제하면 한쪽만 고치는
    일이 생깁니다 — 실제로 문구가 갈라진 적이 있습니다.
    """
    c = CONTENT[key]
    p = pm[key]
    css = re.sub(r"/\*.*?\*/", "", (HERE / "_style.css").read_text(encoding="utf-8"), flags=re.S).strip()
    path = f"/{kind}/{pm['slug']}/"
    pre = "/ko" if key == "ko" else ""
    canonical = SITE + ("/ko" if key == "ko" else "") + path
    alt = ("/ko" if key == "en" else "") + path if key == "en" else path
    home = "/ko/" if key == "ko" else "/"

    meta = "".join(f'<div class="pm-m"><b>{k}</b><span>{v}</span></div>' for k, v in p["meta"])
    body = "\n".join(
        f'      <h2>{title}</h2>\n' + "\n".join(f"      {para}" for para in paras)
        for title, paras in p["sections"])

    return f'''<!DOCTYPE html>
<html lang="{c["lang"]}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{p["title"]}</title>
<meta name="description" content="{p["desc"]}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{SITE}/{kind}/{pm["slug"]}/">
<link rel="alternate" hreflang="ko" href="{SITE}/ko/{kind}/{pm["slug"]}/">
<link rel="alternate" hreflang="x-default" href="{SITE}/{kind}/{pm["slug"]}/">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/icon-256.png">
<meta name="theme-color" content="#0D0F0C">
<meta property="og:type" content="article">
<meta property="og:site_name" content="DURE">
<meta property="og:locale" content="{"ko_KR" if key == "ko" else "en_US"}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{p["title"]}">
<meta property="og:description" content="{p["desc"]}">
<meta property="og:image" content="{SITE}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@durenodes">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>

<header class="hdr">
  <div class="wrap hdr-in">
    <a class="brand" href="{home}" aria-label="DURE">
      {MARK}
      <b>DURE</b>
    </a>
    <nav class="nav" aria-label="Sections">
{nav_html(c, key)}
    </nav>
    <a class="lang" href="{alt}" hreflang="{c["other"]}" rel="alternate">{c["other_label"]}</a>
  </div>
</header>

<main id="top">
  <div class="hero">
    <div class="wrap">
      <div class="kicker">{p["kicker"]}</div>
      <h1>{p["h1"]}</h1>
      <p class="lede">{p["lede"]}</p>
      <div class="pm-meta">{meta}</div>
    </div>
  </div>

  <section>
    <div class="wrap post">
{body}
      <p class="pm-back"><a href="{home}">{p["back"]}</a></p>
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
        <a href="{DATA["github"]}" rel="me noopener" target="_blank">{c["links"]["github"]}</a>
        <a href="{DATA["x"]}" rel="me noopener" target="_blank">{c["links"]["x"]}</a>
        <a href="{DATA["telegram"]}" rel="me noopener" target="_blank">{c["links"]["telegram"]}</a>
        <a href="mailto:{DATA["contact"]}">{c["links"]["contact"]}</a>
        <a href="mailto:{DATA["security"]}">{c["links"]["security"]}</a>
    </div>
  </div>
</footer>

</body>
</html>
'''


def guide_html(key, g):
    """가이드 페이지. 포스트모템과 같은 셸이고 경로만 /guides/ 입니다."""
    return postmortem_html(key, g, kind="guides")


def build(key):
    c = CONTENT[key]
    pre = "/ko" if key == "ko" else ""
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
{nav_html(c, key, landing=True)}
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
        <div class="stat"><div class="stat-n">{len(CHAINS)}</div><div class="stat-l">{c["stat_networks"]}</div></div>
        <div class="stat"><div class="stat-n">{d["slashing"]}</div><div class="stat-l">{c["stat_slashing"]}</div></div>
        <div class="stat"><div class="stat-n">{d["services_live"]}<small> / {d["services_total"]}</small></div><div class="stat-l">{c["stat_services"]}</div></div>
        <div class="stat"><div class="stat-n"><a href="{pre}/incidents/">{d["incidents"]}</a></div><div class="stat-l">{c["stat_incidents"]}</div></div>
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
      <div class="sec-head"><h2>NETWORKS</h2><span class="sec-sub">{c["sec_networks"].format(mainnets=d["mainnets"], testnets=d["testnets"])}</span></div>
      <div class="grid-2">
{net_cards(c)}
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
            <th class="num">{c["th"]["missed"]}</th><th class="num">{c["th"]["rank"]}</th>
            <th class="num">{c["th"]["since"]}</th>
          </tr></thead>
          <tbody>
{table_rows(c)}
          </tbody>
        </table>
      </div>
      <div class="note">{c["note"]}</div>
      <div class="foot-meta">{"".join(f"<span>{m}</span>" for m in c["foot_meta"])}</div>
    </div>
  </section>

  <div class="wrap"><div class="rule"></div></div>


  <section id="delegate">
    <div class="wrap">
      <div class="sec-head"><h2>DELEGATE</h2><span class="sec-sub">{c["sec_delegate"]}</span></div>
{delegate_cards(c)}
    </div>
  </section>

  <div class="wrap"><div class="rule"></div></div>

  <section id="records">
    <div class="wrap">
      <div class="doors">
        <a class="door" href="{pre}/incidents/">
          <div class="door-k">{c["nav"]["log"]}</div>
          <div class="door-t">{c["door_log_t"]}</div>
          <p class="door-d">{c["door_log_d"]}</p>
          <span class="door-go">{c["door_go"]}</span>
        </a>
        <a class="door" href="{pre}/guides/">
          <div class="door-k">{c["nav"]["guides"]}</div>
          <div class="door-t">{c["door_guides_t"]}</div>
          <p class="door-d">{c["door_guides_d"]}</p>
          <span class="door-go">{c["door_go"]}</span>
        </a>
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
    # --skip-fetch: 문구·스타일만 고칠 때. 네트워크 없이 기존 DATA 로 생성합니다.
    skip = "--skip-fetch" in sys.argv
    if skip:
        print(
            f"  ⚠ --skip-fetch — 수치가 {DATA['as_of']} 기준으로 고정됩니다.\n"
            "    페이지의 'as of' 표기도 그 날짜로 남으므로 표시 자체는 정직하지만,\n"
            "    이 상태로 커밋하면 낡은 값이 배포됩니다.\n"
            "    커밋 전에 네트워크를 연결하고 `python3 _build.py` 를 다시 실행하세요.",
            file=sys.stderr)

    if not skip and not fetch_onchain():
        # 조회에 실패했으면 **아무것도 쓰지 않고** 끝냅니다.
        # 여기서 생성하면 옛 값이 새로 쓰인 것처럼 파일에 남아,
        # 다음 커밋에 낡은 수치가 그대로 배포됩니다.
        print("  생성을 건너뜁니다. 기존 파일은 그대로 둡니다.", file=sys.stderr)
        return 1

    (HERE / "index.html").write_text(build("en"), encoding="utf-8")
    (HERE / "ko").mkdir(exist_ok=True)
    (HERE / "ko" / "index.html").write_text(build("ko"), encoding="utf-8")

    written = []
    for kind in ("incidents", "guides"):
        for key in ("en", "ko"):
            d = HERE / ("ko" if key == "ko" else ".") / kind
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(index_page(key, kind), encoding="utf-8")
            written.append(str((d / "index.html").relative_to(HERE)))

    for kind, items in (("incidents", POSTMORTEMS), ("guides", GUIDES)):
        for pm in items:
            for key in ("en", "ko"):
                d = HERE / ("ko" if key == "ko" else ".") / kind / pm["slug"]
                d.mkdir(parents=True, exist_ok=True)
                (d / "index.html").write_text(
                    postmortem_html(key, pm, kind=kind), encoding="utf-8")
                written.append(str((d / "index.html").relative_to(HERE)))

    (HERE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    idx_urls = "\n".join(
        f"""  <url>
    <loc>{SITE}{pre}/{kind}/</loc>
    <lastmod>{last}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE}/{kind}/"/>
    <xhtml:link rel="alternate" hreflang="ko" href="{SITE}/ko/{kind}/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/{kind}/"/>
  </url>"""
        for kind, last in (("incidents", POSTMORTEMS[0]["date"]), ("guides", GUIDES[0]["date"]))
        for pre in ("", "/ko"))

    pm_urls = "\n".join(
        f"""  <url>
    <loc>{SITE}{pre}/{kind}/{pm["slug"]}/</loc>
    <lastmod>{pm["date"]}</lastmod>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE}/{kind}/{pm["slug"]}/"/>
    <xhtml:link rel="alternate" hreflang="ko" href="{SITE}/ko/{kind}/{pm["slug"]}/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/{kind}/{pm["slug"]}/"/>
  </url>"""
        for kind, items in (("incidents", POSTMORTEMS), ("guides", GUIDES))
        for pm in items for pre in ("", "/ko"))

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
{idx_urls}
{pm_urls}
</urlset>
''', encoding="utf-8")

    for f in ["index.html", "ko/index.html", "robots.txt", "sitemap.xml"] + written:
        print(f"  {f:<20} {os.path.getsize(HERE / f):>7,} bytes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
