import asyncio
import httpx
from bs4 import BeautifulSoup


async def test_live_check(user_id: str):
    """라이브 확인 테스트"""
    url = f"https://twitcasting.tv/{user_id}"

    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # HTML 전체 저장
        with open("page_full.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        print("=" * 80)
        print(f"페이지 확인: {url}")
        print("=" * 80)

        # 1. 기존 방식: tw-player-live-badge
        live_badge = soup.find("span", class_="tw-player-live-badge")
        print(f"\n1. tw-player-live-badge 찾기: {live_badge}")

        # 2. LIVE 텍스트가 포함된 모든 요소
        print("\n2. 'LIVE' 텍스트를 포함한 요소들:")
        for elem in soup.find_all(string=lambda text: text and "LIVE" in text.upper()):
            print(f"   - {elem.parent.name}: {elem.parent.get('class', [])} = '{elem.strip()}'")

        # 3. data-is-onlive 또는 유사한 속성
        print("\n3. data-* 속성들:")
        for elem in soup.find_all(attrs=lambda x: x and any('live' in str(k).lower() or 'onlive' in str(k).lower() for k in x.keys())):
            print(f"   - {elem.name}: {elem.attrs}")

        # 4. meta 태그 확인
        print("\n4. Meta 태그들:")
        for meta in soup.find_all("meta"):
            prop = meta.get("property", "")
            name = meta.get("name", "")
            content = meta.get("content", "")
            if any(x in prop.lower() or x in name.lower() for x in ["video", "type", "live", "stream"]):
                print(f"   - {prop or name}: {content}")

        # 5. script 태그에서 JSON 데이터 찾기
        print("\n5. Script 태그에서 'onlive' 또는 'is_live' 찾기:")
        for script in soup.find_all("script"):
            if script.string and ("onlive" in script.string.lower() or "is_live" in script.string.lower()):
                # 첫 200자만 출력
                snippet = script.string[:200].replace("\n", " ")
                print(f"   - 발견: {snippet}...")

        # 6. 특정 클래스 패턴 찾기
        print("\n6. 'live' 관련 클래스를 가진 요소들:")
        for elem in soup.find_all(class_=lambda x: x and any('live' in c.lower() for c in x)):
            print(f"   - {elem.name}.{'.'.join(elem.get('class', []))}")


if __name__ == "__main__":
    # 현재 라이브 중인 채널로 테스트
    asyncio.run(test_live_check("_ll44n"))